# Five Good Ones

A job-fit filter for job hunters who are tired of mass-applying to the wrong roles.

Five Good Ones pulls job postings from public applicant-tracking APIs (Greenhouse, Lever, Ashby), classifies each one against **your** target domain with an open-weight model, and enforces a weekly application budget — so you only ever apply to high-fit roles, at a sustainable pace.

**No closed AI APIs anywhere.** Every LLM call goes through Ollama (local) or Backboard (open-weight models). The app ships with a heuristic keyword classifier so it works with zero model setup.

## Who it's for

A job seeker who wants a tight, curated list — "these 5 roles this week are worth your time" — instead of a firehose of 800 postings.

## How it works

```
 config/companies.txt          public job boards           open-weight models
 (source:company list)    ->   Greenhouse/Lever/Ashby  ->   classify fit vs no-fit
        |                            |                            |
        v                            v                            v
   python -m app.fetch        SQLite (Job table)          Verdict (label, confidence, reason)
        |                            |                            |
        v                            v                            v
   daily cron / manual      Dashboard (htmx tabs)        For You / Skipped / Applied
```

### Architecture

```
                         +---------------------------+
                         |  config/companies.txt     |
                         +-------------+-------------+
                                       |
                                       v
+----------------+   GET/POST   +-------+--------+   normalize   +-----------+
| Greenhouse API |------------>|                |-------------->|           |
+----------------+             |  app/fetcher  |               |  SQLite   |
+----------------+             |  (async httpx)|               |  (SQLModel)|
| Lever API      |------------>|                |               |           |
+----------------+             +-------+--------+               +-----+-----+
+----------------+                     |                              |
| Ashby API      |------------>        |                              v
+----------------+                     v                        +-----------+
                              +----------------+               | Dashboard |
                              | app/classifiers|               |  (htmx)   |
                              |  - heuristic   |               +-----+-----+
                              |  - ollama      |                     |
                              |  - backboard   |                     v
                              |  - tinker     |               +-----------+
                              +-------+--------+               | Settings  |
                                      |                        +-----------+
                              +-------v--------+
                              | Ollama / Backboard / Tinker |
                              +------------------------------+
```

## Setup

### 1. Install

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # then edit .env
```

### 2. (Optional) Pull the local model

The app works out of the box with the heuristic classifier. To use a local LLM:

```bash
ollama pull qwen2.5:7b
```

### 3. Configure companies

Edit `config/companies.txt` — one `source:company` per line:

```
greenhouse:stripe
lever:fly
ashby:mercury
```

### 4. Run

```bash
uvicorn app.main:app --reload
```

Open http://localhost:8000 — set your resume, domain, budget, and exclude keywords on `/settings`, then hit **Classify new jobs** on the dashboard.

### 5. Fetch jobs

```bash
python -m app.fetch        # manual fetch
python -m app.seed         # 10 fake jobs for dev testing
```

## Classifiers

All classifiers implement one interface — `classify(job, prefs) -> Verdict` — and every LLM response is validated with pydantic before use. On any parse failure, the app falls back to the heuristic classifier. It never crashes.

| Classifier | Backend | Needs | Use case |
|---|---|---|---|
| `heuristic` | keyword matching | nothing | zero-setup baseline, fallback |
| `ollama` | qwen2.5:7b via Ollama | local Ollama | private, free, offline |
| `backboard` | open-weight models via Backboard API | `BACKBOARD_API_KEY` | no local GPU |
| `tinker` | LoRA fine-tune via Tinker API | `TINKER_API_KEY`, trained model | best accuracy (see below) |

Switch in Settings or via `CLASSIFIER` in `.env`.

## Fine-tuning with Tinker (optional)

The app records every Hide/Override you make as labeled feedback. Use it to fine-tune a classifier on your own taste:

```bash
pip install -r requirements-train.txt
# 1. Label data into data/train.jsonl (format below)
python scripts/train_tinker.py
# 2. Evaluate against the baselines
python scripts/eval_classifiers.py
```

`data/train.jsonl` format — one conversation per line:

```json
{"messages": [{"role": "user", "content": "Job title: Senior ML Engineer\nJob description:\nBuild and deploy production ML models...\nTarget domain: ML engineer, NOT data analyst"}, {"role": "assistant", "content": "{\"label\": \"fit\"}"}]}
```

`train_tinker.py` LoRA-fine-tunes Qwen2.5-7B-Instruct on this data and writes the resulting model name to `.env` as `TINKER_MODEL_NAME`. `eval_classifiers.py` runs the held-out `data/test.jsonl` through heuristic, ollama (zero-shot), and tinker (fine-tuned), printing accuracy + false-positive rate for each and saving `eval_results.json`.

## Configuration

All config lives in `.env` (see `.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./fivegoodones.db` | SQLModel connection (Postgres-ready) |
| `COMPANIES_FILE` | `config/companies.txt` | boards to fetch |
| `CLASSIFIER` | `heuristic` | default classifier |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | local Ollama |
| `BACKBOARD_API_KEY` | — | Backboard API key |
| `BACKBOARD_BASE_URL` | `https://app.backboard.io/api` | Backboard endpoint |
| `BACKBOARD_MODEL` | `llama-3.1-8b-instruct` | model for Backboard classifier |
| `COMPARE_MODELS` | 3 open models | models for `app.compare_models` |
| `TINKER_API_KEY` | — | Tinker API key |
| `TINKER_MODEL_NAME` | — | saved LoRA weights (`tinker://...`) |

## Scripts

| Command | What it does |
|---|---|
| `python -m app.fetch` | fetch + normalize jobs from all boards |
| `python -m app.seed` | insert 10 fake jobs for dev |
| `python -m app.compare_models` | 20 jobs x 3 models via Backboard -> `compare_results.json` |
| `python scripts/train_tinker.py` | LoRA fine-tune on `data/train.jsonl` |
| `python scripts/eval_classifiers.py` | 3-way classifier eval -> `eval_results.json` |

## Deploy (Render)

`render.yaml` defines two services:

- **web** — `uvicorn app.main:app`
- **cron** — `python -m app.fetch` daily at 09:00

Push to GitHub, import the repo in Render, and the blueprint deploys both. A `Dockerfile` is included if you prefer container deploys.

> Note: Render's free tier has an ephemeral filesystem, so SQLite resets on redeploy. Set `DATABASE_URL` to a Postgres instance when you're ready (SQLModel works unchanged).

## Privacy

Your resume and preferences never leave this server. The only outbound calls are to your own classifier (Ollama on this machine, or Backboard's open-weight models) when judging jobs. Hide/Override feedback is stored locally in the `Preference` table and optionally mirrored to Backboard memory.

## Tech stack

Python 3.11 · FastAPI · SQLModel/SQLite · Jinja2 + htmx · httpx · pydantic-settings · Ollama · Backboard · Tinker
