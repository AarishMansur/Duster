from datetime import datetime, timezone

from sqlmodel import Session, select

from .db import engine
from .models import Preference

DEFAULTS: dict[str, str] = {
    "resume_text": "",
    "domain_definition": "",
    "weekly_budget": "5",
    "exclude_keywords": "",
}


def get_prefs() -> dict[str, str]:
    with Session(engine) as session:
        rows = session.exec(select(Preference)).all()
    prefs = dict(DEFAULTS)
    prefs.update({row.key: row.value for row in rows})
    return prefs


def set_pref(key: str, value: str) -> None:
    with Session(engine) as session:
        pref = session.exec(select(Preference).where(Preference.key == key)).first()
        if pref is None:
            session.add(Preference(key=key, value=value))
        else:
            pref.value = value
            pref.updated_at = datetime.now(timezone.utc)
        session.commit()


def get_budget() -> int:
    try:
        return max(0, int(get_prefs()["weekly_budget"]))
    except ValueError:
        return 5
