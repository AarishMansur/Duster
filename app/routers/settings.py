from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from .. import backboard
from ..preferences import (
    extract_excludes_from_memories,
    get_classifier_name,
    get_prefs,
    set_pref,
)

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

CLASSIFIER_OPTIONS = ["heuristic", "ollama", "backboard", "tinker"]


@router.get("/settings")
def settings_page(request: Request):
    prefs = get_prefs()
    imported: list[str] = []
    memories = backboard.list_memories()
    if memories:
        existing = [k.strip() for k in prefs["exclude_keywords"].split(",") if k.strip()]
        imported = [k for k in extract_excludes_from_memories(memories) if k not in existing]
        prefs["exclude_keywords"] = ", ".join(existing + imported)
    return templates.TemplateResponse(
        request,
        "settings.html",
        {
            "prefs": prefs,
            "saved": request.query_params.get("saved") == "1",
            "effective_classifier": get_classifier_name(),
            "imported_excludes": imported,
        },
    )


@router.post("/settings")
def save_settings(
    resume_text: str = Form(""),
    domain_definition: str = Form(""),
    weekly_budget: str = Form("5"),
    exclude_keywords: str = Form(""),
    classifier: str = Form("heuristic"),
):
    if classifier not in CLASSIFIER_OPTIONS:
        classifier = "heuristic"
    set_pref("resume_text", resume_text)
    set_pref("domain_definition", domain_definition)
    set_pref("weekly_budget", str(_parse_budget(weekly_budget)))
    set_pref("exclude_keywords", exclude_keywords)
    set_pref("classifier", classifier)
    return RedirectResponse("/settings?saved=1", status_code=303)


def _parse_budget(raw: str) -> int:
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return 5
