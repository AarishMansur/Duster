import httpx
from pydantic import ValidationError

from ..config import settings
from ..models import Job, Verdict
from .base import Classifier, ModelVerdict
from .heuristic import HeuristicClassifier
from .prompts import build_prompt, extract_json


class OllamaClassifier(Classifier):
    name = "qwen2.5:7b"

    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")

    def classify(self, job: Job, prefs: dict[str, str]) -> Verdict:
        try:
            resp = httpx.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.name,
                    "prompt": build_prompt(job, prefs),
                    "format": "json",
                    "stream": False,
                    "options": {"temperature": 0.1},
                },
                timeout=120.0,
            )
            resp.raise_for_status()
            data = resp.json()
            verdict = ModelVerdict.model_validate_json(extract_json(data["response"]))
            return Verdict(
                job_id=job.id,
                model_name=self.name,
                label=verdict.label,
                confidence=verdict.confidence,
                reason=verdict.reason,
            )
        except (httpx.HTTPError, ValueError, ValidationError, KeyError):
            return HeuristicClassifier().classify(job, prefs)
