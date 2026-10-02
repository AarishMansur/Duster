"""CLI: python scripts/train_tinker.py

LoRA fine-tunes Qwen/Qwen2.5-7B-Instruct on data/train.jsonl and writes the
resulting model path to .env as TINKER_MODEL_NAME.

Requires: pip install -r requirements-train.txt and TINKER_API_KEY in .env
"""
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BASE_MODEL = "Qwen/Qwen2.5-7B-Instruct"
DATA_PATH = Path("data/train.jsonl")
ENV_PATH = Path(".env")


def load_conversations(path: Path) -> list[list[dict[str, str]]]:
    conversations = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                conversations.append(json.loads(line)["messages"])
    return conversations


def update_env(key: str, value: str) -> None:
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []
    out = []
    found = False
    for line in lines:
        if line.startswith(f"{key}="):
            out.append(f"{key}={value}")
            found = True
        else:
            out.append(line)
    if not found:
        out.append(f"{key}={value}")
    ENV_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")


async def train(rank: int, steps: int, max_length: int, batch_size: int) -> None:
    import tinker
    from tinker_cookbook import TrainOnWhat, conversation_to_datum, get_renderer
    from tinker_cookbook.hyperparam_utils import get_lr
    from tinker_cookbook.model_info import get_recommended_renderer_name

    service_client = tinker.ServiceClient()
    training_client = await service_client.create_lora_training_client_async(
        base_model=BASE_MODEL, rank=rank
    )
    tokenizer = training_client.get_tokenizer()
    renderer = get_renderer(get_recommended_renderer_name(BASE_MODEL), tokenizer)

    conversations = load_conversations(DATA_PATH)
    if not conversations:
        print(f"No conversations found in {DATA_PATH}")
        return
    print(f"Loaded {len(conversations)} training conversations")

    data = [
        conversation_to_datum(
            conv, renderer, max_length=max_length, train_on_what=TrainOnWhat.LAST_ASSISTANT_MESSAGE
        )
        for conv in conversations
    ]

    lr = get_lr(BASE_MODEL)
    print(f"Base: {BASE_MODEL} | LoRA rank: {rank} | lr: {lr} | steps: {steps}")

    for step in range(steps):
        batch = [data[(step * batch_size + i) % len(data)] for i in range(min(batch_size, len(data)))]
        t0 = time.time()
        fwdbwd_future = await training_client.forward_backward_async(batch, "cross_entropy")
        optim_future = await training_client.optim_step_async(
            tinker.AdamParams(learning_rate=lr)
        )
        result = await fwdbwd_future.result_async()
        await optim_future.result_async()
        print(f"Step {step + 1}/{steps}: loss = {result.loss:.4f} ({time.time() - t0:.1f}s)")

    save_result = await training_client.save_weights_for_sampler_async(name="five-good-ones")
    weights_path = getattr(save_result, "weights_path", None) or getattr(save_result, "path", None)
    if weights_path:
        update_env("TINKER_MODEL_NAME", weights_path)
        print(f"\nSaved. Wrote TINKER_MODEL_NAME={weights_path} to .env")
        print("Set CLASSIFIER=tinker in .env (or pick Tinker in Settings) to use it.")
    else:
        print("\nCould not read the weights path from the save result.")
        print("Copy the model path from the Tinker console into .env as TINKER_MODEL_NAME.")


def main() -> None:
    import os

    if not os.environ.get("TINKER_API_KEY"):
        print("TINKER_API_KEY is not set - add it to .env first.")
        return
    if not DATA_PATH.exists():
        print(f"{DATA_PATH} not found - create it with labeled conversations first.")
        print('Format: {"messages": [{"role": "user", "content": "<job text>"},')
        print('                    {"role": "assistant", "content": "{\\"label\\": \\"fit\\"}"}]}')
        return
    asyncio.run(train(rank=32, steps=100, max_length=1024, batch_size=4))


if __name__ == "__main__":
    main()
