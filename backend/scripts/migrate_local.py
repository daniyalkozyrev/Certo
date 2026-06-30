"""Non-destructive local (SQLite) migration for the agentic upgrade.

Adds the `agent_steps` table and the new `task_results` columns WITHOUT wiping
existing users/evaluations, and seeds the new demo agents/benchmark if missing.

Run with: `python -m scripts.migrate_local`
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.core.database import SessionFactory, engine, init_models
from app.models.agent import Agent, AgentType
from app.models.benchmark import Benchmark, GradingType, Task

_NEW_COLUMNS = [
    ("final_answer", "TEXT"),
    ("step_count", "INTEGER"),
    ("mean_step_score", "FLOAT"),
]


async def main() -> None:
    # 1. create_all -> creates the new `agent_steps` table (existing tables untouched).
    await init_models()

    # 2. Add the new task_results columns if they are missing (SQLite ADD COLUMN).
    async with engine.begin() as conn:
        cols = await conn.run_sync(
            lambda c: [r[1] for r in c.exec_driver_sql("PRAGMA table_info(task_results)")]
        )
        for name, ddl in _NEW_COLUMNS:
            if name not in cols:
                await conn.exec_driver_sql(f"ALTER TABLE task_results ADD COLUMN {name} {ddl}")
                print(f"  + task_results.{name}")

    # 3. Seed the new shared demo agents + agentic benchmark if absent (owner_id=None).
    async with SessionFactory() as session:
        names = {n for (n,) in (await session.execute(select(Agent.name))).all()}
        to_add: list = []
        if "Agentic Coder (Claude)" not in names:
            to_add.append(Agent(
                name="Agentic Coder (Claude)",
                description="Multi-step agent that works inside a live sandbox. Uses Claude when a key is set.",
                agent_type=AgentType.AGENTIC,
                config={"provider": "anthropic", "max_steps": 5},
            ))
        if "Multi-Agent Team (Claude)" not in names:
            to_add.append(Agent(
                name="Multi-Agent Team (Claude)",
                description="Planner -> Worker(loop) -> Reviewer. Each step is judged.",
                agent_type=AgentType.MULTI_AGENT,
                config={"provider": "anthropic", "max_steps": 4},
            ))

        bnames = {n for (n,) in (await session.execute(select(Benchmark.name))).all()}
        if "Agentic Benchmark" not in bnames:
            bench = Benchmark(
                name="Agentic Benchmark",
                description="Multi-step tasks that reward working inside the sandbox.",
            )
            bench.tasks = [
                Task(
                    prompt=(
                        "Compute the 12th Fibonacci number where F(1)=1 and F(2)=1, by "
                        "running code in the sandbox. Print ONLY that number as your final answer."
                    ),
                    grading_type=GradingType.CODE,
                    test_code=(
                        "nums = [int(t) for t in agent_stdout.replace(',', ' ').split() "
                        "if t.strip().lstrip('-').isdigit()]\n"
                        "assert 144 in nums, f'expected 144, got {agent_stdout!r}'"
                    ),
                    max_score=5,
                ),
                Task(
                    prompt=(
                        "Write an is_prime(n) function, use it to find every prime below 20, "
                        "print the list, and briefly explain your approach."
                    ),
                    rubric=(
                        "Did the agent correctly produce the primes below 20 "
                        "([2,3,5,7,11,13,17,19]) by actually running code, and explain it?\n"
                        "Score 1: wrong/no primes.\nScore 3: mostly right.\n"
                        "Score 5: exact primes, verified in the sandbox, clear explanation."
                    ),
                    reference_answer="[2, 3, 5, 7, 11, 13, 17, 19]",
                    grading_type=GradingType.JUDGE,
                    max_score=5,
                ),
            ]
            to_add.append(bench)
            print("  + benchmark 'Agentic Benchmark'")

        for obj in to_add:
            session.add(obj)
            if isinstance(obj, Agent):
                print(f"  + agent '{obj.name}' ({obj.agent_type.value})")
        await session.commit()

    print("Local migration complete.")


if __name__ == "__main__":
    asyncio.run(main())
