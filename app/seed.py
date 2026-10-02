"""CLI: python -m app.seed"""
from sqlmodel import Session, select

from .db import create_db_and_tables, engine
from .models import Job

FAKE_JOBS = [
    Job(
        source="greenhouse",
        company="nimbus",
        title="Senior ML Engineer",
        description=(
            "Build and deploy production machine learning models for our "
            "recommendation platform. You will own model training pipelines, "
            "fine-tune LLMs, and work with PyTorch and Python."
        ),
        location="Remote",
        url="https://boards-api.example.com/nimbus/jobs/1",
    ),
    Job(
        source="lever",
        company="datawise",
        title="Data Analyst",
        description=(
            "Produce dashboards and ad-hoc reports for the sales team. "
            "Strong SQL and Tableau required. Some light statistics."
        ),
        location="New York, NY",
        url="https://api.example.com/datawise/jobs/2",
    ),
    Job(
        source="ashby",
        company="cortex",
        title="Backend Engineer, Python",
        description=(
            "Design and scale our Python microservices on AWS. You will build "
            "APIs, work on data pipelines, and mentor junior engineers."
        ),
        location="Remote (US)",
        url="https://api.example.com/cortex/jobs/3",
    ),
    Job(
        source="greenhouse",
        company="pixelforge",
        title="Frontend Engineer",
        description=(
            "Build delightful user interfaces with React and TypeScript. "
            "Eye for design and accessibility a plus."
        ),
        location="San Francisco, CA",
        url="https://boards-api.example.com/pixelforge/jobs/4",
    ),
    Job(
        source="lever",
        company="cloudhaven",
        title="DevOps Engineer",
        description=(
            "Manage Kubernetes clusters, CI/CD pipelines, and Terraform "
            "infrastructure. On-call rotation required."
        ),
        location="Austin, TX (on-site)",
        url="https://api.example.com/cloudhaven/jobs/5",
    ),
    Job(
        source="ashby",
        company="quantia",
        title="Quantitative Trader",
        description=(
            "Develop trading strategies for fintech markets. Strong math and "
            "statistics background required. Experience with pricing models."
        ),
        location="New York, NY (on-site)",
        url="https://api.example.com/quantia/jobs/6",
    ),
    Job(
        source="greenhouse",
        company="nimbus",
        title="ML Platform Engineer",
        description=(
            "Build the internal ML platform: feature stores, model serving, "
            "and experiment tracking. Kubernetes, Python, and Go."
        ),
        location="Remote",
        url="https://boards-api.example.com/nimbus/jobs/7",
    ),
    Job(
        source="lever",
        company="datawise",
        title="Machine Learning Engineer",
        description=(
            "Apply ML to forecasting problems. Python, scikit-learn, and "
            "PySpark. You will present findings to stakeholders."
        ),
        location="Remote",
        url="https://api.example.com/datawise/jobs/8",
    ),
    Job(
        source="ashby",
        company="cortex",
        title="Full-stack Engineer",
        description=(
            "Work across our Python backend and React frontend. Generalists "
            "welcome; you will touch everything from APIs to UI."
        ),
        location="Toronto (hybrid)",
        url="https://api.example.com/cortex/jobs/9",
    ),
    Job(
        source="lever",
        company="cloudhaven",
        title="Site Reliability Engineer",
        description=(
            "Keep our cloud infrastructure reliable. On-call required. "
            "Must be on-site in Austin."
        ),
        location="Austin, TX (on-site)",
        url="https://api.example.com/cloudhaven/jobs/10",
    ),
]


def main() -> None:
    create_db_and_tables()
    with Session(engine) as session:
        existing_urls = set(session.exec(select(Job.url)).all())
        added = 0
        for job in FAKE_JOBS:
            if job.url not in existing_urls:
                session.add(job)
                added += 1
        session.commit()
    print(f"Seeded {added} fake jobs.")


if __name__ == "__main__":
    main()
