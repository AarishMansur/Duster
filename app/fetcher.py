import asyncio
from datetime import datetime, timezone
from html.parser import HTMLParser

import httpx
from sqlmodel import Session, select

from .config import settings
from .db import engine
from .models import Job

USER_AGENT = "FiveGoodOnes/1.0 (open-source job-fit filter)"


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def get_text(self) -> str:
        return " ".join("".join(self.parts).split())


def html_to_text(raw: str) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(raw)
    return parser.get_text()


def parse_datetime(value) -> datetime | None:
    # Lever returns epoch millis; Greenhouse/Ashby return ISO-8601 strings.
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def load_companies(path: str) -> list[tuple[str, str]]:
    companies: list[tuple[str, str]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            source, _, company = line.partition(":")
            companies.append((source.strip().lower(), company.strip().lower()))
    return companies


async def fetch_greenhouse(client: httpx.AsyncClient, company: str) -> list[Job]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs"
    resp = await client.get(url)
    resp.raise_for_status()
    jobs = []
    for item in resp.json().get("jobs", []):
        jobs.append(
            Job(
                source="greenhouse",
                company=company,
                title=item.get("title", ""),
                description=html_to_text(item.get("content", "")),
                location=(item.get("location") or {}).get("name"),
                url=item["absolute_url"],
                posted_at=parse_datetime(item.get("updated_at")),
            )
        )
    return jobs


async def fetch_lever(client: httpx.AsyncClient, company: str) -> list[Job]:
    url = f"https://api.lever.co/v0/postings/{company}?mode=json"
    resp = await client.get(url)
    resp.raise_for_status()
    jobs = []
    for item in resp.json():
        categories = item.get("categories") or {}
        description = item.get("descriptionPlain") or html_to_text(
            item.get("description", "")
        )
        jobs.append(
            Job(
                source="lever",
                company=company,
                title=item.get("text", ""),
                description=description,
                location=categories.get("location"),
                url=item["hostedUrl"],
                posted_at=parse_datetime(item.get("updatedAt") or item.get("createdAt")),
            )
        )
    return jobs


async def fetch_ashby(client: httpx.AsyncClient, company: str) -> list[Job]:
    url = f"https://api.ashbyhq.com/postingApi/jobBoard/{company}"
    resp = await client.post(url, json={"includeCompensation": True})
    resp.raise_for_status()
    jobs = []
    for item in resp.json().get("jobs", []):
        jobs.append(
            Job(
                source="ashby",
                company=company,
                title=item.get("title", ""),
                description=html_to_text(item.get("description", "")),
                location=item.get("location"),
                url=item["jobUrl"],
                posted_at=parse_datetime(item.get("postedAt")),
            )
        )
    return jobs


async def fetch_all() -> dict[str, int]:
    companies = load_companies(settings.companies_file)

    async with httpx.AsyncClient(
        timeout=30.0, headers={"User-Agent": USER_AGENT}
    ) as client:
        tasks = []
        for source, company in companies:
            if source == "greenhouse":
                tasks.append(fetch_greenhouse(client, company))
            elif source == "lever":
                tasks.append(fetch_lever(client, company))
            elif source == "ashby":
                tasks.append(fetch_ashby(client, company))
        results = await asyncio.gather(*tasks, return_exceptions=True)

    jobs: list[Job] = []
    errors = 0
    for result in results:
        if isinstance(result, Exception):
            errors += 1
            print(f"  ! fetch error: {result}")
        else:
            jobs.extend(result)

    with Session(engine) as session:
        existing_urls = set(session.exec(select(Job.url)).all())
        new_jobs = [j for j in jobs if j.url not in existing_urls]
        for job in new_jobs:
            session.add(job)
        session.commit()

    return {"fetched": len(jobs), "new": len(new_jobs), "errors": errors}


def run_fetcher() -> dict[str, int]:
    return asyncio.run(fetch_all())
