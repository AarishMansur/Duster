from .base import Classifier, ModelVerdict
from .heuristic import HeuristicClassifier
from .ollama import OllamaClassifier

# TODO: TinkerFineTunedClassifier — fine-tuned open-weight model (e.g. a LoRA
# adapter on qwen2.5) served through Ollama. Subclass Classifier, implement
# classify() with the same prompt/parse pattern as OllamaClassifier, and add
# it to get_classifier() below. No other code changes needed.


def get_classifier(name: str = "heuristic") -> Classifier:
    if name == "ollama":
        return OllamaClassifier()
    if name == "heuristic":
        return HeuristicClassifier()
    raise ValueError(f"unknown classifier: {name}")


__all__ = ["Classifier", "ModelVerdict", "HeuristicClassifier", "OllamaClassifier", "get_classifier"]
