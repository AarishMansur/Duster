from datetime import date, datetime, timezone

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Job(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    source: str  # greenhouse | lever | ashby
    company: str = Field(index=True)
    title: str
    description: str
    location: str | None = None
    url: str = Field(unique=True, index=True)
    posted_at: datetime | None = None
    fetched_at: datetime = Field(default_factory=utcnow)


class Verdict(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="job.id", unique=True, index=True)
    model_name: str
    label: str  # fit | no_fit
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    created_at: datetime = Field(default_factory=utcnow)


class Application(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="job.id", index=True)
    week_start: date
    notes: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class Preference(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    key: str = Field(unique=True, index=True)
    value: str
    updated_at: datetime = Field(default_factory=utcnow)
