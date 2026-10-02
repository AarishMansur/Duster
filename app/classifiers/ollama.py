import httpx
from pydantic import ValidationError

from ..config import settings
from ..models import Job, Verdict
from .base import Classifier, ModelVerdict
from .heuristic import HeuristicClassifier


def _extract_json(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object in model response")
    return text[start : end + 1]


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
                    "prompt": self._prompt(job, prefs),
                    "format": "json",
                    "stream": False,
                    "options": {"temperature": 0.1},
                },
                timeout=120.0,
            )
            resp.raise_for_status()
            data = ModelVerdict.model_validate_json(_extract_json(resp.json()["response"]))
            return Verdict(
                job_id=job.id,
                model_name=self.name,
                label=data.label,
                confidence=data.confidence,
                reason=data.reason,
            )
        except (httpx.HTTPError, ValueError, ValidationError, KeyError):
            return HeuristicClassifier().classify(job, prefs)

    def _prompt(self, job: Job, prefs: dict[str, str]) -> str:
        return (
            "You are a job-fit classifier for a job seeker.\n\n"
            f"Target domain: {prefs.get('domain_definition') or '(not specified)'}\n"
            f"Hard excludes: {prefs.get('exclude_keywords') or '(none)'}\n\n"
            f"Job title: {job.title}\n"
            f"Job description:\n{job.description[:1500]}\n\n"
            "Decide whether this job fits the target domain. "
            'Respond with strict JSON only, no markdown:\n'
            '{"label": "fit" or "no_fit", "confidence": 0.0-1.0, "reason": "one short sentence"}'
        )
