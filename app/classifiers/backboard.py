import httpx
from pydantic import ValidationError

from ..config import settings
from ..models import Job, Verdict
from .base import Classifier, ModelVerdict
from .heuristic import HeuristicClassifier
from .prompts import build_prompt, extract_json


class BackboardClassifier(Classifier):
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
    ):
        self.base_url = (base_url or settings.backboard_base_url).rstrip("/")
        self.model = model or settings.backboard_model
        self.api_key = api_key or settings.backboard_api_key
        self.name = f"backboard:{self.model}"

    def classify(self, job: Job, prefs: dict[str, str]) -> Verdict:
        try:
            resp = httpx.post(
                f"{self.base_url}/threads/messages",
                headers={"X-API-Key": self.api_key},
                json={
                    "content": build_prompt(job, prefs),
                    "model_name": self.model,
                    "stream": False,
                    "json_output": True,
                    "memory": "off",
                },
                timeout=120.0,
            )
            resp.raise_for_status()
            data = resp.json()
            verdict = ModelVerdict.model_validate_json(extract_json(data["content"]))
            return Verdict(
                job_id=job.id,
                model_name=self.name,
                label=verdict.label,
                confidence=verdict.confidence,
                reason=verdict.reason,
            )
        except (httpx.HTTPError, ValueError, ValidationError, KeyError):
            return HeuristicClassifier().classify(job, prefs)
