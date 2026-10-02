from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from ..classifiers import get_classifier
from ..config import settings
from ..db import engine
from ..models import Job, Verdict
from ..preferences import get_prefs

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/")
def dashboard(request: Request):
    with Session(engine) as session:
        total = len(session.exec(select(Job)).all())
        judged = len(session.exec(select(Verdict)).all())
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"total": total, "unjudged": total - judged, "classifier": settings.classifier},
    )


@router.post("/api/classify")
def classify_unjudged():
    classifier = get_classifier(settings.classifier)
    with Session(engine) as session:
        unjudged = session.exec(
            select(Job).where(Job.id.not_in(select(Verdict.job_id)))
        ).all()
        for job in unjudged:
            session.add(classifier.classify(job, get_prefs()))
        session.commit()
    return {"classified": len(unjudged), "classifier": classifier.name}
