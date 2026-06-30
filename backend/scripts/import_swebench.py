"""Import a SWE-bench benchmark (real GitHub bug-fix tasks) into Certo.

Each instance = a repo at a base commit + an issue (`problem_statement`). The
agent must produce a patch; grading (grading_type=SWEBENCH) applies that patch and
runs the repo's tests via the OFFICIAL swebench harness (Docker). We store the
harness inputs in `Task.meta` so the grader can build a predictions file and read
the gold result back.

SWE-bench_Lite (300 tasks) and SWE-bench_Verified (500) are PUBLIC on HuggingFace
(no gating, unlike GAIA). The first Docker run per instance is heavy, so default
to a tiny subset.

Usage:
    python -m scripts.import_swebench --limit 3
    python -m scripts.import_swebench --dataset princeton-nlp/SWE-bench_Verified --limit 5
    python -m scripts.import_swebench --instances sympy__sympy-20590 astropy__astropy-12907
"""

from __future__ import annotations

import argparse
import asyncio
import json

from app.core.config import settings
from app.core.database import SessionFactory, init_models
from app.models.benchmark import Benchmark, GradingType, Task


def _as_list(value) -> list[str]:
    """FAIL_TO_PASS / PASS_TO_PASS arrive as a JSON-encoded string or a list."""
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str) and value.strip():
        try:
            return [str(v) for v in json.loads(value)]
        except json.JSONDecodeError:
            return [value]
    return []


def _build_task(row: dict) -> Task:
    meta = {
        "instance_id": row["instance_id"],
        "repo": row["repo"],
        "base_commit": row["base_commit"],
        "version": row.get("version"),
        "environment_setup_commit": row.get("environment_setup_commit"),
        "FAIL_TO_PASS": _as_list(row.get("FAIL_TO_PASS")),
        "PASS_TO_PASS": _as_list(row.get("PASS_TO_PASS")),
        "gold_patch": row.get("patch"),  # reference solution (for the judge / sanity)
        "test_patch": row.get("test_patch"),
    }
    prompt = (
        f"Repository: {row['repo']} @ {row['base_commit'][:12]}\n\n"
        f"Resolve the following issue by producing a patch (a unified git diff).\n\n"
        f"--- ISSUE ---\n{row['problem_statement']}"
    )
    return Task(
        prompt=prompt,
        reference_answer=None,  # gold patch lives in meta; don't leak it to the agent
        grading_type=GradingType.SWEBENCH,
        meta=meta,
        max_score=5,
    )


async def run(dataset: str, split: str, name: str, limit: int, instances: list[str]) -> None:
    from datasets import load_dataset  # local import: optional heavy dep

    if settings.is_sqlite:
        await init_models()

    ds = load_dataset(dataset, split=split)
    wanted = set(instances)
    tasks: list[Task] = []
    for row in ds:
        if wanted and row["instance_id"] not in wanted:
            continue
        tasks.append(_build_task(row))
        if not wanted and limit and len(tasks) >= limit:
            break

    if not tasks:
        print("No matching instances found.")
        return

    async with SessionFactory() as session:
        bench = Benchmark(
            name=name,
            description=f"SWE-bench ({dataset.split('/')[-1]}) — {len(tasks)} real bug-fix tasks, harness-graded.",
        )
        bench.tasks = tasks
        session.add(bench)
        await session.commit()
        await session.refresh(bench)
        print(f"Created benchmark {bench.name!r} id={bench.id} with {len(tasks)} SWEBENCH tasks:")
        for t in tasks:
            print(f"  - {t.meta['instance_id']}  ({t.meta['repo']})")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", default="princeton-nlp/SWE-bench_Lite")
    p.add_argument("--split", default="test")
    p.add_argument("--name", default="SWE-bench Lite (subset)")
    p.add_argument("--limit", type=int, default=3, help="Import the first N instances (0 = all).")
    p.add_argument("--instances", nargs="*", default=[], help="Specific instance_ids to import.")
    args = p.parse_args()
    asyncio.run(run(args.dataset, args.split, args.name, args.limit, args.instances))
