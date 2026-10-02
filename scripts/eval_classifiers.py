"""CLI: python scripts/eval_classifiers.py

Runs the held-out data/test.jsonl through three classifiers - heuristic,
ollama (base qwen2.5:7b, zero-shot), and tinker (fine-tuned) - and prints
accuracy + false-positive rate for each. Writes eval_results.json.

The test set uses the same format as data/train.jsonl. Labels should be
created against the same domain definition you have in Settings.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.classifiers import get_classifier
from app.classifiers.prompts import parse_job_text
from app.config import settings
from app.db import create_db_and_tables, engine
from app.models import Job
from app.preferences import get_prefs
from sqlmodel import Session, select

TEST_PATH = Path("data/test.jsonl")
CLASSIFIERS = ["heuristic", "ollama", "tinker"]


def load_test_set(path: Path) -> list[tuple[str, str, str]]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            user_content = row["messages"][0]["content"]
            assistant_content = row["messages"][1]["content"]
            title, description, _domain = parse_job_text(user_content)
            gold = json.loads(assistant_content)["label"]
            rows.append((title, description, gold))
    return rows


def evaluate(name: str, jobs: list[tuple[str, str, str]], prefs: dict[str, str]) -> dict:
    classifier = get_classifier(name)
    details = []
    for i, (title, description, gold) in enumerate(jobs):
        job = Job(
            source="eval",
            company="eval",
            id=i + 1,
            title=title,
            description=description,
            location="",
            url="",
        )
        verdict = classifier.classify(job, prefs)
        details.append(
            {
                "title": title,
                "gold": gold,
                "predicted": verdict.label,
                "correct": verdict.label == gold,
            }
        )
    total = len(details)
    correct = sum(1 for d in details if d["correct"])
    fp = sum(1 for d in details if d["gold"] == "no_fit" and d["predicted"] == "fit")
    tn = sum(1 for d in details if d["gold"] == "no_fit" and d["predicted"] == "no_fit")
    return {
        "classifier": name,
        "accuracy": round(correct / total, 4) if total else 0.0,
        "false_positive_rate": round(fp / (fp + tn), 4) if (fp + tn) else 0.0,
        "correct": correct,
        "total": total,
        "details": details,
    }


def main() -> None:
    create_db_and_tables()
    if not TEST_PATH.exists():
        print(f"{TEST_PATH} not found - create it with labeled conversations first.")
        return
    jobs = load_test_set(TEST_PATH)
    if not jobs:
        print(f"{TEST_PATH} is empty.")
        return

    prefs = get_prefs()
    print(f"Evaluating {len(jobs)} held-out jobs")
    print(f"Domain: {prefs.get('domain_definition')!r}\n")

    if not settings.ollama_base_url:
        print("Note: OLLAMA_BASE_URL not set - ollama will fall back to heuristic.")
    if not settings.tinker_model_name:
        print("Note: TINKER_MODEL_NAME not set - tinker will fall back to heuristic.")
    print()

    results = {}
    for name in CLASSIFIERS:
        r = evaluate(name, jobs, prefs)
        results[name] = r
        print(
            f"{name:10} accuracy={r['accuracy']:.2%}  "
            f"false-positive-rate={r['false_positive_rate']:.2%}  "
            f"({r['correct']}/{r['total']})"
        )

    with open("eval_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print("\nWrote eval_results.json")


if __name__ == "__main__":
    main()
