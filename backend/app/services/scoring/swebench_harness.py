"""Bridge to the official SWE-bench evaluation harness.

The harness is Linux-only (it imports the Unix ``resource`` module) and drives
Docker to build a per-instance repo environment, apply a candidate patch, and run
the repo's test suite (``FAIL_TO_PASS`` must pass, ``PASS_TO_PASS`` must stay
passing). On Windows the Certo backend therefore invokes it inside **WSL2**, where
``swebench`` + Docker live, then reads the resulting JSON report back.

This is the SWE-bench counterpart of ``answer_match`` (GAIA) and ``test_code``:
the objective, ground-truth axis — except "the test" is an entire real project's
suite, run for real. Returns, per instance, whether the patch *resolved* the issue.
"""

from __future__ import annotations

import asyncio
import json
import re
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_PATCH_FENCE = re.compile(r"```(?:diff|patch)?\s*\n(.*?)```", re.DOTALL)


def extract_patch(text: str | None) -> str:
    """Pull a unified diff out of an agent's reply: a ```diff fenced block, or a
    raw diff if the text itself looks like one. `git apply` wants a trailing newline."""
    if not text:
        return ""
    m = _PATCH_FENCE.search(text)
    body = m.group(1) if m else text
    body = body.strip()
    if not body:
        return ""
    return body if body.endswith("\n") else body + "\n"


@dataclass
class SwebenchResult:
    instance_id: str
    resolved: bool
    errored: bool
    detail: str


def _win_to_wsl(path: str) -> str:
    """C:\\Users\\x\\f.jsonl -> /mnt/c/Users/x/f.jsonl (so WSL can read it)."""
    p = Path(path).resolve()
    drive = p.drive[0].lower()
    tail = p.as_posix()[len(p.drive):]  # strip 'C:' -> '/Users/x/f.jsonl'
    return f"/mnt/{drive}{tail}"


def _wsl(args: list[str], *, timeout: int) -> subprocess.CompletedProcess:
    """Run a command inside the configured WSL distro as root."""
    cmd = ["wsl.exe", "-d", settings.swebench_wsl_distro, "-u", "root", "-e", *args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _docker_ready() -> bool:
    """The harness's docker SDK needs the unix socket inside WSL. Docker Desktop's
    WSL integration mounts it only while Desktop is running — check before paying
    for a doomed harness run."""
    try:
        out = _wsl(["bash", "-lc", "test -S /var/run/docker.sock && echo READY"], timeout=25)
        return "READY" in out.stdout
    except Exception:
        return False


def grade_patches(
    patches: dict[str, str], *, run_id: str | None = None, model: str = "certo"
) -> dict[str, SwebenchResult]:
    """Run the harness over ``{instance_id: unified_diff}`` and return per-instance
    results. A patch that doesn't resolve (or errors / is empty) is a fail.

    Instances that come back *errored* (e.g. a transient image build/pull race on a
    cold cache) are retried once — a genuine "did not resolve" is a real fail and is
    NOT retried."""
    if not patches:
        return {}
    if not _docker_ready():
        msg = (
            "Docker is not reachable in WSL — start Docker Desktop and enable WSL "
            "integration for the distro, then re-run."
        )
        logger.error("swebench.docker_unavailable")
        return {iid: SwebenchResult(iid, resolved=False, errored=True, detail=msg) for iid in patches}
    run_id = run_id or f"certo_{uuid.uuid4().hex[:8]}"
    results = _run_once(patches, run_id=run_id, model=model)

    retry = {iid: patches[iid] for iid, r in results.items() if r.errored}
    if retry:
        logger.warning("swebench.retry_errored", instances=list(retry))
        for iid, r in _run_once(retry, run_id=f"{run_id}_retry", model=model).items():
            results[iid] = r
    return results


def _run_once(
    patches: dict[str, str], *, run_id: str, model: str = "certo"
) -> dict[str, SwebenchResult]:
    instance_ids = list(patches)

    predictions = [
        {"instance_id": iid, "model_name_or_path": model, "model_patch": patch or ""}
        for iid, patch in patches.items()
    ]

    # 1. Predictions go to a shared temp file the WSL side can read via /mnt/c.
    tmp = Path(tempfile.gettempdir()) / f"certo_swebench_{run_id}.jsonl"
    tmp.write_text("\n".join(json.dumps(p) for p in predictions), encoding="utf-8")
    preds_wsl = _win_to_wsl(str(tmp))

    # 2. Invoke the harness inside WSL2 (CWD on the native WSL fs for Docker perf).
    #    Wait for the Docker socket first: Desktop's WSL integration can mount it a
    #    beat late, and docker.from_env() otherwise dies before the harness starts.
    inner = (
        "for i in $(seq 1 20); do test -S /var/run/docker.sock && break; sleep 1; done; "
        f"cd {settings.swebench_workdir} && "
        f"{settings.swebench_python} -m swebench.harness.run_evaluation "
        f"--dataset_name {settings.swebench_dataset} "
        f"--predictions_path {preds_wsl} "
        f"--run_id {run_id} "
        f"--instance_ids {' '.join(instance_ids)} "
        f"--max_workers {settings.swebench_max_workers} "
        f"--timeout {settings.swebench_timeout}"
    )
    budget = settings.swebench_timeout * max(1, len(instance_ids)) + 900
    logger.info("swebench.harness_start", run_id=run_id, instances=instance_ids)
    proc = _wsl(["bash", "-lc", inner], timeout=budget)
    if proc.returncode != 0:
        logger.error("swebench.harness_failed", rc=proc.returncode, stderr=proc.stderr[-1500:])

    # 3. Read the report (<model>.<run_id>.json, on the WSL fs) back via `cat`.
    report_name = f"{model.replace('/', '__')}.{run_id}.json"
    cat = _wsl(["cat", f"{settings.swebench_workdir}/{report_name}"], timeout=60)
    if cat.returncode != 0 or not cat.stdout.strip():
        # Harness produced no report — treat every instance as an error/fail.
        detail = (proc.stderr or proc.stdout or "harness produced no report")[-400:]
        return {
            iid: SwebenchResult(iid, resolved=False, errored=True, detail=detail)
            for iid in instance_ids
        }

    report = json.loads(cat.stdout)
    resolved = set(report.get("resolved_ids", []))
    errored = set(report.get("error_ids", []))
    empty = set(report.get("empty_patch_ids", []))
    results: dict[str, SwebenchResult] = {}
    for iid in instance_ids:
        if iid in resolved:
            results[iid] = SwebenchResult(iid, True, False, "patch resolved the issue (tests pass)")
        elif iid in errored:
            # The harness lumps two very different things into error_ids: a
            # deterministic "the patch doesn't apply to the repo" (the agent's fault,
            # final) and a transient infra error like an image race (worth a retry).
            # Tell them apart from the instance log so we don't retry hopeless patches.
            log = _read_instance_log(run_id, model, iid)
            if "Patch Apply Failed" in log or "malformed patch" in log:
                results[iid] = SwebenchResult(iid, False, False, "patch did not apply to the repo")
            else:
                results[iid] = SwebenchResult(iid, False, True, "harness error while evaluating the patch")
        elif iid in empty:
            results[iid] = SwebenchResult(iid, False, False, "empty patch (agent produced no diff)")
        else:
            results[iid] = SwebenchResult(iid, False, False, "patch did not resolve the issue (tests still fail)")
    return results


def _read_instance_log(run_id: str, model: str, instance_id: str) -> str:
    """Best-effort read of a per-instance harness log (to classify failures)."""
    path = (
        f"{settings.swebench_workdir}/logs/run_evaluation/"
        f"{run_id}/{model.replace('/', '__')}/{instance_id}/run_instance.log"
    )
    try:
        out = _wsl(["cat", path], timeout=30)
        return out.stdout or ""
    except Exception:
        return ""


async def grade_patches_async(
    patches: dict[str, str], *, run_id: str | None = None, model: str = "certo"
) -> dict[str, SwebenchResult]:
    """Async wrapper — the harness is a long blocking subprocess, so run it off the
    event loop."""
    return await asyncio.to_thread(grade_patches, patches, run_id=run_id, model=model)
