"""Seed demo data: agents (one-shot, agentic, multi-agent) + benchmarks.

Run with: `python -m scripts.seed`
Prints the created agent_id / benchmark_id values for the smoke test.
"""

from __future__ import annotations

import asyncio

from app.core.config import settings
from app.core.database import SessionFactory, init_models
from app.models.agent import Agent, AgentType
from app.models.benchmark import Benchmark, GradingType, Task


async def seed() -> None:
    # Local dev (SQLite): ensure tables exist without Alembic.
    if settings.is_sqlite:
        await init_models()

    async with SessionFactory() as session:
        # ── Agents ───────────────────────────────────────────────────────
        demo_agent = Agent(
            name="Demo Agent (one-shot)",
            description="One-shot LLM agent. No api_key -> runs in offline mock mode.",
            agent_type=AgentType.LLM_ENDPOINT,
            config={},
        )
        agentic_agent = Agent(
            name="Agentic Coder (Claude)",
            description=(
                "Works inside a LIVE sandbox over multiple steps: think -> run "
                "code -> observe -> repeat. Uses Claude when an Anthropic key is "
                "configured, otherwise an offline mock."
            ),
            agent_type=AgentType.AGENTIC,
            config={"provider": "anthropic", "max_steps": 5},
        )
        multi_agent = Agent(
            name="Multi-Agent Team (Claude)",
            description=(
                "Planner -> Worker(loop in sandbox) -> Reviewer. The shape real "
                "multi-agent systems use for hard tasks. Each step is judged."
            ),
            agent_type=AgentType.MULTI_AGENT,
            config={"provider": "anthropic", "max_steps": 4},
        )

        # ── Benchmark 1: quick sanity (one-shot friendly) ────────────────
        sanity = Benchmark(
            name="Sanity Benchmark",
            description="Minimal benchmark to exercise the pipeline.",
        )
        sanity.tasks = [
            Task(
                prompt="Write a program that prints the sum of 2 and 3.",
                rubric=(
                    "Does the response correctly output 5?\n"
                    "Score 1: wrong or no output.\n"
                    "Score 3: partially correct.\n"
                    "Score 5: prints exactly 5."
                ),
                reference_answer="5",
                grading_type=GradingType.JUDGE,
                max_score=5,
            ),
            Task(
                prompt="Print exactly the string: hello world",
                grading_type=GradingType.CODE,
                # Real correctness check (no longer a free pass for "didn't crash").
                test_code='assert agent_stdout.strip() == "hello world", f"got {agent_stdout!r}"',
                max_score=5,
            ),
        ]

        # ── Benchmark 2: agentic (needs real multi-step reasoning) ───────
        agentic_bench = Benchmark(
            name="Agentic Benchmark",
            description="Multi-step tasks that reward working inside the sandbox.",
        )
        agentic_bench.tasks = [
            Task(
                prompt=(
                    "Compute the 12th Fibonacci number where F(1)=1 and F(2)=1, "
                    "by running code in the sandbox. Print ONLY that number as your "
                    "final answer."
                ),
                grading_type=GradingType.CODE,
                # F(12) = 144. The test asserts the agent's final answer contains it.
                test_code=(
                    "nums = [int(t) for t in agent_stdout.replace(',', ' ').split() "
                    "if t.strip().lstrip('-').isdigit()]\n"
                    "assert 144 in nums, f'expected 144, got {agent_stdout!r}'"
                ),
                max_score=5,
            ),
            Task(
                prompt=(
                    "Write an is_prime(n) function, use it to find every prime below "
                    "20, print the list, and briefly explain your approach."
                ),
                rubric=(
                    "Did the agent correctly produce the primes below 20 "
                    "([2,3,5,7,11,13,17,19]) by actually running code, and explain it?\n"
                    "Score 1: wrong/no primes.\n"
                    "Score 3: mostly right with gaps.\n"
                    "Score 5: exact correct primes, verified in the sandbox, clear explanation."
                ),
                reference_answer="[2, 3, 5, 7, 11, 13, 17, 19]",
                grading_type=GradingType.JUDGE,
                max_score=5,
            ),
        ]

        session.add_all([demo_agent, agentic_agent, multi_agent, sanity, agentic_bench])
        await session.commit()
        for obj in (demo_agent, agentic_agent, multi_agent, sanity, agentic_bench):
            await session.refresh(obj)

        print("Seed complete:")
        print(f"  DEMO_AGENT_ID    = {demo_agent.id}  ({demo_agent.agent_type.value})")
        print(f"  AGENTIC_AGENT_ID = {agentic_agent.id}  ({agentic_agent.agent_type.value})")
        print(f"  MULTI_AGENT_ID   = {multi_agent.id}  ({multi_agent.agent_type.value})")
        print(f"  SANITY_BENCH_ID  = {sanity.id}")
        print(f"  AGENTIC_BENCH_ID = {agentic_bench.id}")


if __name__ == "__main__":
    asyncio.run(seed())
