"""Import an answer-match benchmark (e.g. GAIA validation) from JSONL or Parquet.

Each row is a question with its known answer. Field names are matched tolerantly,
so this works for the GAIA validation split (HuggingFace now ships it as `.parquet`)
AND any simple `{"question": ..., "answer": ...}` dataset. Creates a shared
Benchmark whose tasks use grading_type=MATCH (objective answer-match, no code run).

GAIA is gated on HuggingFace — accept its terms, then download `metadata.parquet`
(or `metadata.level1.parquet`) from the validation files. Answers live in the
`Final answer` column. Some GAIA tasks reference an attached file (`file_name`);
those can't be solved from text alone, so `--text-only` skips them.

Usage:
    python -m scripts.import_gaia path/to/metadata.parquet --name "GAIA validation" --limit 20 --text-only
"""

from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Iterator

from app.core.config import settings
from app.core.database import SessionFactory, init_models
from app.models.benchmark import Benchmark, GradingType, Task

_Q_FIELDS = ("Question", "question", "prompt", "task")
_A_FIELDS = ("Final answer", "final_answer", "answer", "expected", "expected_output")
_FILE_FIELDS = ("file_name", "file_path", "file")


def _field(row: dict, names: tuple[str, ...]) -> str | None:
    for n in names:
        if n in row and row[n] is not None and str(row[n]).strip():
            return str(row[n]).strip()
    return None


def _iter_rows(path: str) -> Iterator[dict]:
    """Yield rows from a .jsonl or .parquet file."""
    if path.lower().endswith(".parquet"):
        import pyarrow.parquet as pq  # local import: optional dependency

        table = pq.read_table(path)
        for batch in table.to_batches():
            yield from batch.to_pylist()
    else:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    yield json.loads(line)


async def run(path: str, name: str, limit: int, text_only: bool) -> None:
    if settings.is_sqlite:
        await init_models()

    tasks: list[Task] = []
    skipped_file = 0
    for row in _iter_rows(path):
        q = _field(row, _Q_FIELDS)
        a = _field(row, _A_FIELDS)
        if not q or not a or a == "?":  # skip hidden-answer (test) rows
            continue
        if text_only and _field(row, _FILE_FIELDS):  # needs an attachment to solve
            skipped_file += 1
            continue
        tasks.append(
            Task(prompt=q, reference_answer=a, grading_type=GradingType.MATCH, max_score=5)
        )
        if limit and len(tasks) >= limit:
            break

    if not tasks:
        print("No usable rows found (need a question + a non-empty answer field).")
        return

    async with SessionFactory() as session:
        bench = Benchmark(name=name, description=f"Answer-match benchmark ({len(tasks)} tasks)")
        bench.tasks = tasks
        session.add(bench)
        await session.commit()
        await session.refresh(bench)
        note = f" (skipped {skipped_file} tasks needing a file)" if skipped_file else ""
        print(f"Created benchmark {bench.name!r} id={bench.id} with {len(tasks)} MATCH tasks.{note}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("path", help="Path to the JSONL or Parquet file (e.g. GAIA metadata.parquet).")
    p.add_argument("--name", default="GAIA validation")
    p.add_argument("--limit", type=int, default=0, help="Import at most N tasks (0 = all).")
    p.add_argument(
        "--text-only",
        action="store_true",
        help="Skip tasks that reference an attached file (solvable from text only).",
    )
    args = p.parse_args()
    asyncio.run(run(args.path, args.name, args.limit, args.text_only))
