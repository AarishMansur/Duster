from .backboard import BackboardClassifier
from .base import Classifier, ModelVerdict
from .heuristic import HeuristicClassifier
from .ollama import OllamaClassifier
from .tinker import TinkerFineTunedClassifier


def get_classifier(name: str = "heuristic") -> Classifier:
    if name == "ollama":
        return OllamaClassifier()
    if name == "backboard":
        return BackboardClassifier()
    if name == "tinker":
        return TinkerFineTunedClassifier()
    if name == "heuristic":
        return HeuristicClassifier()
    raise ValueError(f"unknown classifier: {name}")


__all__ = [
    "Classifier",
    "ModelVerdict",
    "HeuristicClassifier",
    "OllamaClassifier",
    "BackboardClassifier",
    "TinkerFineTunedClassifier",
    "get_classifier",
]
