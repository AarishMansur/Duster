import json
import os

from ..config import settings
from ..models import Job, Verdict
from .base import Classifier
from .heuristic import HeuristicClassifier
from .prompts import extract_json, format_job_text

_client = None
_tokenizer = None
_renderer = None


def _get_client(model_name: str, api_key: str):
    global _client, _tokenizer, _renderer
    if _client is None:
        import tinker
        from tinker_cookbook.model_info import get_recommended_renderer_name
        from tinker_cookbook.renderers import get_renderer

        os.environ.setdefault("TINKER_API_KEY", api_key)
        service_client = tinker.ServiceClient()
        _client = service_client.create_sampling_client(model_path=model_name)
        _tokenizer = _client.get_tokenizer()
        _renderer = get_renderer(
            get_recommended_renderer_name(_client.get_base_model()), _tokenizer
        )
    return _client, _tokenizer, _renderer


class TinkerFineTunedClassifier(Classifier):
    def __init__(self, model_name: str | None = None, api_key: str | None = None):
        self.model_name = model_name or settings.tinker_model_name
        self.api_key = api_key or settings.tinker_api_key
        self.name = f"tinker:{self.model_name}"

    def classify(self, job: Job, prefs: dict[str, str]) -> Verdict:
        try:
            import tinker

            client, tokenizer, renderer = _get_client(self.model_name, self.api_key)
            job_text = format_job_text(
                job.title, job.description, prefs.get("domain_definition", "")
            )
            prompt = renderer.build_generation_prompt([{"role": "user", "content": job_text}])
            model_input = tinker.ModelInput.from_ints(tokenizer.encode(prompt))
            result = client.sample(
                model_input, 1, tinker.SamplingParams(max_tokens=32, temperature=0.0)
            ).result()
            text = tokenizer.decode(result.sequences[0].tokens)
            label = json.loads(extract_json(text))["label"]
            if label not in ("fit", "no_fit"):
                raise ValueError(f"unexpected label: {label}")
            return Verdict(
                job_id=job.id,
                model_name=self.name,
                label=label,
                confidence=0.85,
                reason="Tinker fine-tuned model",
            )
        except Exception:
            return HeuristicClassifier().classify(job, prefs)
