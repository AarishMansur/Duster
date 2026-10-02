from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from ..preferences import get_prefs, set_pref

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


def _parse_budget(raw: str) -> int:
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return 5


@router.get("/settings")
def settings_page(request: Request):
    return templates.TemplateResponse(
        request,
        "settings.html",
        {"prefs": get_prefs(), "saved": request.query_params.get("saved") == "1"},
    )


@router.post("/settings")
def save_settings(
    resume_text: str = Form(""),
    domain_definition: str = Form(""),
    weekly_budget: str = Form("5"),
    exclude_keywords: str = Form(""),
):
    set_pref("resume_text", resume_text)
    set_pref("domain_definition", domain_definition)
    set_pref("weekly_budget", str(_parse_budget(weekly_budget)))
    set_pref("exclude_keywords", exclude_keywords)
    return RedirectResponse("/settings?saved=1", status_code=303)
