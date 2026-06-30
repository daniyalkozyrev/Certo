# Certo

Platform for **evaluating and improving AI agents**. An agent is run over a
benchmark inside an **E2B sandbox**, graded by a **judge ensemble**
(Prometheus-2 + an optional second LLM to cut single-judge subjectivity), and
scored with an aggregate **TrustScore**. Every run is stored as a
reward-labelled trajectory (+1 / −1) for later agent-improvement datasets.

```
Certo/
├── backend/    FastAPI · Postgres+pgvector · Redis+Arq · E2B · judge ensemble
└── frontend/   Next.js 15 dashboard (talks to the backend API)
```

## Run it all locally

### 1. Backend
```bash
cd backend
python -m venv .venv && source .venv/Scripts/activate   # Windows Git Bash
pip install -e ".[dev]"
cp .env.example .env            # MOCK_SANDBOX/MOCK_JUDGE default true → no GPU/E2B needed
docker compose up -d            # postgres + redis  (needs Docker Desktop running)
alembic upgrade head
python -m scripts.seed          # demo agent + benchmark

uvicorn app.main:app --reload                       # terminal A → http://localhost:8000
arq app.workers.settings.WorkerSettings             # terminal B (background worker)
```

### 2. Frontend
```bash
cd frontend
npm install
cp .env.example .env.local      # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev                     # → http://localhost:3000
```

Open http://localhost:3000 → **New evaluation** → pick the seeded agent +
benchmark → watch it run → see the TrustScore, per-task results and the
ensemble judge votes.

## Judge ensemble (second opinion)

The judge layer averages independent graders to reduce subjectivity. The second
judge is a **plug-in slot** — enable it in `backend/.env`:

```
JUDGE_SECONDARY_ENABLED=true
JUDGE_SECONDARY_BASE_URL=https://api.openai.com/v1   # any OpenAI-compatible endpoint
JUDGE_SECONDARY_API_KEY=...
JUDGE_SECONDARY_MODEL=gpt-4o-mini
```

## Going from mock to real services

In `backend/.env`:
- `MOCK_SANDBOX=false` + `E2B_API_KEY=...` — execute code in real E2B.
- `MOCK_JUDGE=false` + `JUDGE_BASE_URL=http://<gpu-host>:8000/v1` — real Prometheus-2 on vLLM.

CORS for the frontend is configured via `CORS_ORIGINS` in `backend/.env`.
See [backend/API.md](backend/API.md) for the full API contract.
