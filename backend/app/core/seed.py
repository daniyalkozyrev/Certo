"""First-boot seeding so a fresh deploy is immediately usable.

Ensures one working Claude-backed agent and a small answer-match benchmark exist.
Idempotent AND self-healing: the demo agent's config is refreshed on every boot,
so a stale model/key (e.g. from a mis-set env var) gets corrected on redeploy.
"""

from __future__ import annotations

from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionFactory
from app.core.logging import get_logger
from app.models.agent import Agent, AgentType
from app.models.benchmark import Benchmark, GradingType, Task

logger = get_logger(__name__)

_GAIA_PROMPT = (
    "You are a general AI assistant. Answer the question as accurately as you can. "
    "You may reason briefly, then finish with a single line:\n"
    "FINAL ANSWER: [YOUR FINAL ANSWER]\n"
    "YOUR FINAL ANSWER should be a number OR as few words as possible OR a comma "
    "separated list. Give your single best guess if unsure."
)

# Small, verifiable answer-match set (no dataset download needed at boot).
_DEMO_TASKS = [
    ("What is the capital of Japan?", "Tokyo"),
    ("How many continents are there on Earth?", "7"),
    ("What is the chemical symbol for gold?", "Au"),
    ("In what year did the first human land on the Moon?", "1969"),
    ("What is the square root of 144?", "12"),
    ("Who wrote the play 'Romeo and Juliet'?", "William Shakespeare"),
]


async def seed_if_empty() -> None:
    if not settings.seed_on_start:
        return
    cfg = {
        "base_url": "https://api.anthropic.com/v1/",
        "api_key": settings.judge_anthropic_api_key,
        "model": settings.judge_anthropic_model,
        "system_prompt": _GAIA_PROMPT,
    }
    async with SessionFactory() as session:
        # Upsert the demo agent — refreshing its config self-heals a stale model.
        agent = (
            await session.execute(select(Agent).where(Agent.name == "Claude Assistant"))
        ).scalar_one_or_none()
        if agent is None:
            session.add(
                Agent(
                    name="Claude Assistant",
                    description="Single Claude call — a working demo agent for answer-match benchmarks.",
                    agent_type=AgentType.LLM_ENDPOINT,
                    config=cfg,
                )
            )
        else:
            agent.config = cfg

        # Create the demo benchmark only if it's missing.
        bench = (
            await session.execute(
                select(Benchmark).where(Benchmark.name == "General Knowledge (answer-match)")
            )
        ).scalar_one_or_none()
        if bench is None:
            b = Benchmark(
                name="General Knowledge (answer-match)",
                description="A quick objective benchmark — answers are matched against ground truth.",
            )
            b.tasks = [
                Task(prompt=q, reference_answer=a, grading_type=GradingType.MATCH, max_score=5)
                for q, a in _DEMO_TASKS
            ]
            session.add(b)
        await session.commit()
        logger.info("seed.ensured_demo_data", agent="Claude Assistant")
