from ..models import Job


def format_job_text(title: str, description: str, domain_definition: str) -> str:
    return (
        f"Job title: {title}\n"
        f"Job description:\n{description[:1500]}\n"
        f"Target domain: {domain_definition}"
    )


def parse_job_text(text: str) -> tuple[str, str, str]:
    title = description = domain = ""
    section = None
    desc_lines: list[str] = []
    for line in text.split("\n"):
        if line.startswith("Job title: "):
            title = line[len("Job title: "):]
            section = None
        elif line.startswith("Job description:"):
            section = "desc"
        elif line.startswith("Target domain: "):
            domain = line[len("Target domain: "):]
            section = None
        elif section == "desc":
            desc_lines.append(line)
    return title, "\n".join(desc_lines).strip(), domain


def build_prompt(job: Job, prefs: dict[str, str]) -> str:
    return (
        "You are a job-fit classifier for a job seeker.\n\n"
        f"Target domain: {prefs.get('domain_definition') or '(not specified)'}\n"
        f"Hard excludes: {prefs.get('exclude_keywords') or '(none)'}\n\n"
        f"Job title: {job.title}\n"
        f"Job description:\n{job.description[:1500]}\n\n"
        "Decide whether this job fits the target domain. "
        'Respond with strict JSON only, no markdown:\n'
        '{"label": "fit" or "no_fit", "confidence": 0.0-1.0, "reason": "one short sentence"}'
    )


def extract_json(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object in model response")
    return text[start : end + 1]
