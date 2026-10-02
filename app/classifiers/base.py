from abc import ABC, abstractmethod
from typing import Literal

from pydantic import BaseModel, Field

from ..models import Job, Verdict


class ModelVerdict(BaseModel):
    label: Literal["fit", "no_fit"]
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str


class Classifier(ABC):
    name: str = "abstract"

    @abstractmethod
    def classify(self, job: Job, prefs: dict[str, str]) -> Verdict:
        ...
