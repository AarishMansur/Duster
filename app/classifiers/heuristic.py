from ..models import Job, Verdict
from .base import Classifier


def _keywords(raw: str) -> list[str]:
    return [
        kw.strip().lower()
        for kw in raw.replace("\n", ",").split(",")
        if len(kw.strip()) >= 2
    ]


def _parse_domain(raw: str) -> tuple[list[str], list[str]]:
    positives: list[str] = []
    negatives: list[str] = []
    for segment in raw.split(","):
        phrase = segment.strip().lower().strip(".")
        if not phrase:
            continue
        if phrase.startswith("not "):
            negatives.append(phrase[4:].strip())
        else:
            positives.append(phrase)
    return positives, negatives


class HeuristicClassifier(Classifier):
    name = "heuristic"

    def classify(self, job: Job, prefs: dict[str, str]) -> Verdict:
        text = f"{job.title} {job.description}".lower()

        for kw in _keywords(prefs.get("exclude_keywords", "")):
            if kw in text:
                return self._verdict(job, "no_fit", 0.9, f"Matches exclude keyword '{kw}'")

        positives, negatives = _parse_domain(prefs.get("domain_definition", ""))
        for phrase in negatives:
            if phrase in text:
                return self._verdict(job, "no_fit", 0.8, f"Matches excluded domain '{phrase}'")

        matches = [p for p in positives if p in text]
        if matches:
            confidence = min(0.5 + 0.1 * len(matches), 0.9)
            return self._verdict(job, "fit", confidence, f"Matches domain keywords: {', '.join(matches[:3])}")

        return self._verdict(job, "no_fit", 0.5, "No domain keyword match")

    def _verdict(self, job: Job, label: str, confidence: float, reason: str) -> Verdict:
        return Verdict(
            job_id=job.id,
            model_name=self.name,
            label=label,
            confidence=confidence,
            reason=reason,
        )
