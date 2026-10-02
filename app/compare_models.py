"""CLI: python -m app.compare_models

Runs the same 20 sample jobs through each open model via Backboard and prints
a table of label + latency + cost per model. Writes compare_results.json.
"""
import json
import time

import httpx
from sqlmodel import Session, select

from .classifiers.base import ModelVerdict
from .classifiers.prompts import build_prompt, extract_json
from .config import settings
from .db import create_db_and_tables, engine
from .models import Job
from .preferences import get_prefs

SAMPLE_SIZE = 20


def _headers() -> dict[str, str]:
    return {"X-API-Key": settings.backboard_api_key}


def _model_prices() -> dict[str, tuple[float | None, float | None]]:
    resp = httpx.get(
        f"{settings.backboard_base_url}/models",
        headers=_headers(),
        params={"model_type": "llm", "limit": 500},
        timeout=30.0,
    )
    resp.raise_for_status()
    prices: dict[str, tuple[float | None, float | None]] = {}
    for m in resp.json().get("models", []):
        prices[m["name"]] = (
            m.get("input_cost_per_1m_tokens"),
            m.get("output_cost_per_1m_tokens"),
        )
    return prices


def _classify_one(model: str, job: Job, prefs: dict[str, str]) -> dict:
    start = time.monotonic()
    resp = httpx.post(
        f"{settings.backboard_base_url}/threads/messages",
        headers=_headers(),
        json={
            "content": build_prompt(job, prefs),
            "model_name": model,
            "stream": False,
            "json_output": True,
            "memory": "off",
        },
        timeout=120.0,
    )
    resp.raise_for_status()
    latency_ms = (time.monotonic() - start) * 1000
    data = resp.json()
    verdict = ModelVerdict.model_validate_json(extract_json(data["content"]))
    return {
        "label": verdict.label,
        "confidence": verdict.confidence,
        "latency_ms": round(latency_ms, 1),
        "input_tokens": data.get("input_tokens"),
        "output_tokens": data.get("output_tokens"),
    }


def main() -> None:
    if not settings.backboard_api_key:
        print("BACKBOARD_API_KEY is not set - add it to .env first.")
        return

    create_db_and_tables()
    with Session(engine) as session:
        jobs = session.exec(select(Job).limit(SAMPLE_SIZE)).all()
    if not jobs:
        print("No jobs in the database — run python -m app.seed first.")
        return

    prefs = get_prefs()
    models = [m.strip() for m in settings.compare_models.split(",") if m.strip()]
    prices = _model_prices()

    results: dict[str, dict] = {}
    for model in models:
        rows = []
        for job in jobs:
            try:
                row = _classify_one(model, job, prefs)
            except Exception as e:
                row = {"error": str(e)}
            row["job_id"] = job.id
            rows.append(row)

        ok = [r for r in rows if "error" not in r]
        input_price, output_price = prices.get(model, (None, None))
        total_cost = None
        if input_price is not None and output_price is not None and ok:
            input_tokens = sum(r.get("input_tokens") or 0 for r in ok)
            output_tokens = sum(r.get("output_tokens") or 0 for r in ok)
            total_cost = input_tokens * input_price / 1e6 + output_tokens * output_price / 1e6

        results[model] = {
            "jobs": rows,
            "fit": sum(1 for r in ok if r["label"] == "fit"),
            "no_fit": sum(1 for r in ok if r["label"] == "no_fit"),
            "avg_latency_ms": (
                round(sum(r["latency_ms"] for r in ok) / len(ok), 1) if ok else None
            ),
            "total_cost_usd": round(total_cost, 6) if total_cost is not None else None,
        }
        print(
            f"{model}: fit={results[model]['fit']} no_fit={results[model]['no_fit']} "
            f"avg_latency={results[model]['avg_latency_ms']}ms "
            f"cost=${results[model]['total_cost_usd']}"
        )

    with open("compare_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nWrote compare_results.json ({len(models)} models x {len(jobs)} jobs)")


if __name__ == "__main__":
    main()
