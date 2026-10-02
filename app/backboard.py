import httpx

from .config import settings
from .preferences import get_prefs, set_pref

ASSISTANT_PREF = "backboard_assistant_id"


def _headers() -> dict[str, str]:
    return {"X-API-Key": settings.backboard_api_key}


def get_or_create_assistant() -> str | None:
    existing = get_prefs().get(ASSISTANT_PREF)
    if existing:
        return existing
    try:
        resp = httpx.get(
            f"{settings.backboard_base_url}/assistants",
            headers=_headers(),
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        assistants = data if isinstance(data, list) else data.get("assistants", [])
        if assistants:
            assistant_id = assistants[0]["assistant_id"]
        else:
            resp = httpx.post(
                f"{settings.backboard_base_url}/assistants",
                headers=_headers(),
                json={
                    "name": "Five Good Ones",
                    "system_prompt": "You store job-fit feedback for one job seeker.",
                },
                timeout=30.0,
            )
            resp.raise_for_status()
            assistant_id = resp.json()["assistant_id"]
        set_pref(ASSISTANT_PREF, assistant_id)
        return assistant_id
    except (httpx.HTTPError, KeyError):
        return None


def add_memory(content: str) -> None:
    assistant_id = get_or_create_assistant()
    if not assistant_id:
        return
    try:
        httpx.post(
            f"{settings.backboard_base_url}/assistants/{assistant_id}/memories",
            headers=_headers(),
            json={"content": content},
            timeout=30.0,
        ).raise_for_status()
    except httpx.HTTPError:
        pass


def list_memories() -> list[str]:
    assistant_id = get_or_create_assistant()
    if not assistant_id:
        return []
    try:
        resp = httpx.get(
            f"{settings.backboard_base_url}/assistants/{assistant_id}/memories",
            headers=_headers(),
            params={"page_size": 100},
            timeout=30.0,
        )
        resp.raise_for_status()
        return [m["content"] for m in resp.json().get("memories", [])]
    except (httpx.HTTPError, KeyError):
        return []
