# Certo Backend

Backend for **Certo** — a platform for evaluating and improving AI agents.

It registers agents, runs them on benchmark tasks inside an **E2B** sandbox,
grades the output with an **LLM-as-a-Judge (Prometheus 2)** served on a
self-hosted vLLM endpoint, and aggregates a **TrustScore**. Every run is stored
as a reward-labelled trajectory (+1 / −1) to later build improvement datasets.

## Stack

- Python 3.12 + FastAPI
- PostgreSQL + pgvector, SQLAlchemy 2.0 (async) + Alembic
- Redis + Arq (background evaluation jobs)
- E2B sandbox, OpenAI-compatible client for the judge (vLLM)

## Architecture

```
api/ (HTTP)  →  services/ (use-cases)  →  repositories/ (data)  →  models/ (ORM)
                     │
                     ├─ sandbox/      E2B code execution
                     ├─ judge/        Prometheus-2 grading
                     ├─ agent_runner/ agent-under-test inference
                     └─ scoring/      TrustScore aggregation
workers/  background evaluation runner (Arq)
```

## Quick start (local)

```bash
# 1. Install deps (editable)
python -m venv .venv && source .venv/Scripts/activate   # Windows Git Bash
pip install -e ".[dev]"

# 2. Configure
cp .env.example .env            # MOCK_SANDBOX/MOCK_JUDGE default to true → no external services needed

# 3. Infrastructure
docker compose up -d            # postgres + redis

# 4. Migrate
alembic upgrade head

# 5. Seed demo data
python -m scripts.seed

# 6. Run API + worker (two terminals)
uvicorn app.main:app --reload
arq app.workers.settings.WorkerSettings
```

Open http://localhost:8000/docs for the interactive API.

## End-to-end smoke test

```bash
# create an evaluation (uses the seeded agent + benchmark ids printed by seed)
curl -X POST localhost:8000/api/v1/evaluations \
  -H 'content-type: application/json' \
  -d '{"agent_id":"<AGENT_ID>","benchmark_id":"<BENCHMARK_ID>"}'

# poll until status == completed, then read trust_score
curl localhost:8000/api/v1/evaluations/<EVAL_ID>
```

## Switching from mock to real services

In `.env`:

- `MOCK_SANDBOX=false` + `E2B_API_KEY=...` — execute code in real E2B.
- `MOCK_JUDGE=false` + `JUDGE_BASE_URL=http://<gpu-host>:8000/v1` — use real Prometheus 2 on vLLM.
- Set per-agent `config` (base_url/api_key/model) or the `AGENT_DEFAULT_*` vars for the agent-under-test.
