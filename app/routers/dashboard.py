from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, and_, or_, select

from ..classifiers import get_classifier
from ..config import settings
from ..db import engine
from ..models import Application, Job, Verdict
from ..preferences import add_feedback, get_budget, get_prefs

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


def _week_start() -> date:
    today = datetime.now(timezone.utc).date()
    return today - timedelta(days=today.weekday())


def _recent_clause(cutoff: datetime):
    return or_(
        Job.posted_at >= cutoff,
        and_(Job.posted_at.is_(None), Job.fetched_at >= cutoff),
    )


def _counts(session: Session) -> dict[str, int]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    unjudged = Job.id.not_in(select(Verdict.job_id))
    return {
        "new": len(session.exec(select(Job).where(unjudged, _recent_clause(cutoff))).all()),
        "fit": len(session.exec(select(Verdict).where(Verdict.label == "fit")).all()),
        "skipped": len(session.exec(select(Verdict).where(Verdict.label == "no_fit")).all()),
        "applied_week": len(
            session.exec(select(Application).where(Application.week_start == _week_start())).all()
        ),
    }


@router.get("/")
def dashboard(request: Request):
    with Session(engine) as session:
        counts = _counts(session)
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"counts": counts, "default_tab": "new" if counts["new"] else "fit"},
    )


@router.get("/tab/new")
def tab_new(request: Request):
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    with Session(engine) as session:
        jobs = session.exec(
            select(Job)
            .where(Job.id.not_in(select(Verdict.job_id)), _recent_clause(cutoff))
            .order_by(Job.fetched_at.desc())
        ).all()
    return templates.TemplateResponse(
        request, "partials/new.html",
        {"jobs": jobs, "classifier_name": get_classifier(settings.classifier).name},
    )


@router.get("/tab/fit")
def tab_fit(request: Request):
    with Session(engine) as session:
        rows = session.exec(
            select(Verdict, Job)
            .where(Verdict.job_id == Job.id, Verdict.label == "fit")
            .order_by(Verdict.confidence.desc())
        ).all()
        applied_ids = set(session.exec(select(Application.job_id)).all())
        used = len(
            session.exec(select(Application).where(Application.week_start == _week_start())).all()
        )
    return templates.TemplateResponse(
        request,
        "partials/fit.html",
        {"rows": rows, "applied_ids": applied_ids, "used": used, "budget": get_budget()},
    )


@router.get("/tab/skipped")
def tab_skipped(request: Request):
    with Session(engine) as session:
        rows = session.exec(
            select(Verdict, Job)
            .where(Verdict.job_id == Job.id, Verdict.label == "no_fit")
            .order_by(Verdict.created_at.desc())
        ).all()
    return templates.TemplateResponse(request, "partials/skipped.html", {"rows": rows})


@router.get("/tab/applied")
def tab_applied(request: Request):
    with Session(engine) as session:
        rows = session.exec(
            select(Application, Job)
            .where(Application.job_id == Job.id)
            .order_by(Application.week_start.desc(), Application.created_at.desc())
        ).all()
    weeks: dict[str, list] = {}
    for app, job in rows:
        weeks.setdefault(app.week_start.isoformat(), []).append((app, job))
    return templates.TemplateResponse(request, "partials/applied.html", {"weeks": weeks})


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


@router.post("/apply/{job_id}")
def apply(request: Request, job_id: int):
    week_start = _week_start()
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if job is None:
            raise HTTPException(404, "job not found")
        used = len(
            session.exec(select(Application).where(Application.week_start == week_start)).all()
        )
        budget = get_budget()
        if used >= budget:
            return templates.TemplateResponse(
                request,
                "partials/apply_result.html",
                {"budget_reached": True, "used": used, "budget": budget},
            )
        session.add(Application(job_id=job_id, week_start=week_start))
        session.commit()
        job_url = job.url
    return templates.TemplateResponse(
        request,
        "partials/apply_result.html",
        {"job_url": job_url, "applied": True, "used": used + 1, "budget": budget},
    )


@router.post("/hide/{job_id}")
def hide(job_id: int):
    with Session(engine) as session:
        verdict = session.exec(select(Verdict).where(Verdict.job_id == job_id)).first()
        if verdict is None:
            session.add(
                Verdict(
                    job_id=job_id,
                    model_name="user",
                    label="no_fit",
                    confidence=1.0,
                    reason="Hidden by user",
                )
            )
        else:
            verdict.label = "no_fit"
            verdict.confidence = 1.0
            verdict.reason = "Hidden by user"
            verdict.model_name = "user"
        session.commit()
    add_feedback(job_id, "hide")
    return Response(content="")


@router.post("/override/{job_id}")
def override(job_id: int):
    with Session(engine) as session:
        verdict = session.exec(select(Verdict).where(Verdict.job_id == job_id)).first()
        if verdict is None:
            session.add(
                Verdict(
                    job_id=job_id,
                    model_name="user",
                    label="fit",
                    confidence=1.0,
                    reason="Overridden by user",
                )
            )
        else:
            verdict.label = "fit"
            verdict.confidence = 1.0
            verdict.reason = "Overridden by user"
            verdict.model_name = "user"
        session.commit()
    add_feedback(job_id, "override")
    return Response(content="")
