"""First-boot seeding so a fresh deploy is immediately usable.

Creates one working Claude-backed agent and a small answer-match benchmark when
the database has none. Idempotent: does nothing if any agent already exists.
"""

from __future__ import annotations

from sqlalchemy import func, select

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
    async with SessionFactory() as session:
        n_agents = (await session.execute(select(func.count()).select_from(Agent))).scalar()
        if n_agents and n_agents > 0:
            return  # already seeded / has data

        agent = Agent(
            name="Claude Assistant",
            description="Single Claude call — a working demo agent for answer-match benchmarks.",
            agent_type=AgentType.LLM_ENDPOINT,
            config={
                "base_url": "https://api.anthropic.com/v1/",
                "api_key": settings.judge_anthropic_api_key,
                "model": settings.judge_anthropic_model,
                "system_prompt": _GAIA_PROMPT,
            },
        )
        session.add(agent)

        bench = Benchmark(
            name="General Knowledge (answer-match)",
            description="A quick objective benchmark — answers are matched against ground truth.",
        )
        bench.tasks = [
            Task(prompt=q, reference_answer=a, grading_type=GradingType.MATCH, max_score=5)
            for q, a in _DEMO_TASKS
        ]
        session.add(bench)
        await session.commit()
        logger.info("seed.created_demo_data", agent="Claude Assistant", tasks=len(_DEMO_TASKS))
