"""Evaluation orchestration — the core end-to-end use-case.

For one evaluation: load the agent + benchmark, and for every task run the
agent, grade it, and persist a TaskResult (+ a per-step trajectory for agentic
agents), then aggregate the TrustScore.

Two agent execution paths:

* one-shot (`llm_endpoint`): prompt -> one code block -> sandbox -> grade.
* agentic (`agentic` / `multi_agent`): the agent works inside a LIVE sandbox
  over many steps; the judge grades EVERY step and then the whole run.

Grading is correctness-aware: a `code` task with `test_code` is judged by
actually running that test in the sandbox (so "didn't crash" is no longer an
automatic 5/5); a `code` task without a test, and every `judge` task, are
graded by the LLM judge ensemble.
"""

from __future__ import annotations

import json
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.models.agent import AgentType
from app.models.benchmark import GradingType, Task
from app.models.evaluation import AgentStep, Evaluation, EvaluationStatus, TaskResult
from app.models.trace import TraceSource
from app.repositories.agent import AgentRepository
from app.repositories.benchmark import BenchmarkRepository
from app.repositories.evaluation import EvaluationRepository
from app.services.agent_runner.agentic import AgenticRunner, StepRecord
from app.services.agent_runner.runner import AgentRunner
from app.services.judge.base import JudgeRequest
from app.services.judge.ensemble import EnsembleJudge
from app.services.judge.prompts import (
    FINAL_RUBRIC,
    MAS_FINAL_RUBRIC,
    STEP_RUBRIC,
    build_step_instruction,
    format_step_response,
    format_trajectory,
)
from app.services.sandbox.e2b_sandbox import SandboxRunner
from app.services.scoring.answer_match import answer_match, extract_final_answer
from app.services.scoring.swebench_harness import extract_patch, grade_patches_async
from app.services.scoring.trust_score import (
    TaskScore,
    blend_agentic_score,
    compute_trust_score,
)
from app.services.trace_recorder import record_trace

logger = get_logger(__name__)

_AGENTIC_TYPES = {AgentType.AGENTIC, AgentType.MULTI_AGENT}


def _unpack(grade) -> tuple[int, str, list[dict] | None, str | None]:
    """Flatten an EnsembleResult into the fields a TaskResult/AgentStep stores."""
    votes = [
        {"judge": v.judge, "score": v.score, "feedback": v.feedback} for v in grade.votes
    ]
    return grade.score, grade.feedback, (votes or None), grade.disagreement


class EvaluationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.evaluations = EvaluationRepository(session)
        self.agents = AgentRepository(session)
        self.benchmarks = BenchmarkRepository(session)
        self.sandbox = SandboxRunner()
        self.judge = EnsembleJudge()

    async def run(self, evaluation_id: uuid.UUID) -> None:
        evaluation = await self.evaluations.get(evaluation_id)
        if evaluation is None:
            raise NotFoundError("Evaluation not found")

        evaluation.status = EvaluationStatus.RUNNING
        await self.session.flush()

        try:
            await self._execute(evaluation)
            evaluation.status = EvaluationStatus.COMPLETED
        except Exception as exc:
            logger.exception("evaluation.failed", evaluation_id=str(evaluation_id))
            evaluation.status = EvaluationStatus.FAILED
            evaluation.error = str(exc)
        await self.session.commit()

    async def _execute(self, evaluation: Evaluation) -> None:
        agent = await self.agents.get(evaluation.agent_id)
        if agent is None:
            raise NotFoundError("Agent not found")
        benchmark = await self.benchmarks.get_with_tasks(evaluation.benchmark_id)
        if benchmark is None:
            raise NotFoundError("Benchmark not found")

        task_scores: list[TaskScore] = []
        for task in benchmark.tasks:
            # Isolate per-task failures: a transient agent/network/harness error on
            # ONE task must not sink the whole evaluation. Record it as a failed task
            # (clearly flagged as an execution error) and carry on.
            try:
                if agent.agent_type in _AGENTIC_TYPES:
                    result, score = await self._run_agentic_task(
                        evaluation.id, task, agent.config, multi=agent.agent_type == AgentType.MULTI_AGENT
                    )
                else:
                    result, score = await self._run_oneshot_task(
                        evaluation.id, task, AgentRunner(agent.config)
                    )
            except Exception as exc:
                logger.exception("evaluation.task_failed", task_id=str(task.id))
                score = TaskScore(judge_score=1, max_score=task.max_score, passed=False)
                result = TaskResult(
                    evaluation_id=evaluation.id,
                    task_id=task.id,
                    agent_output=None,
                    judge_score=1,
                    judge_feedback=f"task execution error (not scored on merit): {exc}",
                    normalized_score=score.normalized,
                    reward=score.reward,
                )
            self.session.add(result)
            task_scores.append(score)
            # Unify: also record this run as a Trace so it appears in /traces.
            await self._record_task_trace(evaluation, agent, task, result, score)

        aggregate = compute_trust_score(task_scores)
        evaluation.trust_score = aggregate.trust_score
        evaluation.pass_rate = aggregate.pass_rate
        evaluation.summary = {**aggregate.summary, "agent_type": agent.agent_type.value}
        await self.session.flush()

    async def _record_task_trace(
        self, evaluation: Evaluation, agent, task: Task, result: TaskResult, score: TaskScore
    ) -> None:
        """Mirror an executed task as a unified Trace so it shows up in /traces."""
        spans: list[dict] = []
        if result.steps:  # agentic / multi-agent trajectory
            for st in result.steps:
                obs = (st.observation_stdout or "").strip()
                spans.append({
                    "kind": "tool" if st.action_code else "agent",
                    "name": st.role,
                    "input": st.thought or st.action_code,
                    "output": obs or None,
                    "error": st.observation_stderr if st.exit_code not in (None, 0) else None,
                    "judge_score": st.judge_score,
                    "judge_feedback": st.judge_feedback,
                    "judge_votes": st.judge_votes,
                })
        else:  # one-shot answer
            spans.append({
                "kind": "agent",
                "name": "answer",
                "input": task.prompt,
                "output": result.final_answer or result.agent_output,
                "judge_score": result.judge_score,
                "judge_feedback": result.judge_feedback,
                "judge_votes": result.judge_votes,
            })
        await record_trace(
            self.session,
            owner_id=evaluation.owner_id,
            agent_id=evaluation.agent_id,
            source=TraceSource.AGENTIC,
            name=f"{agent.name} · {task.prompt[:50]}",
            task=task.prompt,
            final_output=result.final_answer or result.agent_output,
            trust_score=round(score.normalized * 100, 2),
            summary={
                "final_score": result.judge_score,
                "reward": result.reward,
                "n_spans": len(spans),
                "is_multi_agent": agent.agent_type == AgentType.MULTI_AGENT,
                "evaluation_id": str(evaluation.id),
                "agent_type": agent.agent_type.value,
            },
            spans=spans,
        )

    # ── correctness check: actually run the task's test_code ─────────────
    async def _check_test_code(
        self, *, agent_stdout: str, agent_code: str | None, test_code: str, session=None
    ) -> tuple[bool, str]:
        """Run test_code in the sandbox. It may assert against `agent_stdout`
        (and `agent_code`); for agentic runs the agent's own variables are also
        in scope (same persistent session). Returns (passed, detail)."""
        harness = (
            f"agent_stdout = {json.dumps(agent_stdout)}\n"
            f"agent_code = {json.dumps(agent_code or '')}\n"
            f"{test_code}"
        )
        res = await (session.run(harness) if session is not None else self.sandbox.run_python(harness))
        passed = res.exit_code == 0
        detail = "test_code passed" if passed else f"test_code failed: {res.stderr.strip()[:500]}"
        return passed, detail

    # ── one-shot agent (llm_endpoint) ────────────────────────────────────
    async def _run_oneshot_task(
        self, evaluation_id: uuid.UUID, task: Task, runner: AgentRunner
    ) -> tuple[TaskResult, TaskScore]:
        agent_output = await runner.solve(task.prompt)

        # Only execute in the sandbox if the agent actually returned a code block
        # to run. Answer agents (e.g. Hermes, which run their own tools and reply
        # in prose) have nothing to execute — we judge/verify their answer text
        # directly instead of running prose as Python (which only produced noise).
        # SWE-bench output is a patch (often a ```diff block), not a runnable
        # program — never feed it to the Python sandbox; the harness grades it.
        if agent_output.has_code and task.grading_type != GradingType.SWEBENCH:
            sandbox = await self.sandbox.run_python(agent_output.code)
            response_text = sandbox.stdout.strip() or agent_output.raw
            sb_stdout, sb_stderr, sb_exit = sandbox.stdout, sandbox.stderr, sandbox.exit_code
            verify_stdout = sandbox.stdout  # tests assert against program output
        else:
            response_text = agent_output.raw
            sb_stdout = sb_stderr = sb_exit = None
            verify_stdout = agent_output.raw  # tests assert against the answer text

        votes: list[dict] | None = None
        disagreement: str | None = None
        passed: bool | None

        if task.grading_type == GradingType.CODE and task.test_code and settings.allow_code_execution:
            ok, detail = await self._check_test_code(
                agent_stdout=verify_stdout, agent_code=agent_output.code, test_code=task.test_code
            )
            passed = ok
            judge_score = 5 if ok else 1
            feedback = detail
        elif task.grading_type == GradingType.MATCH:
            final = extract_final_answer(response_text)
            ok = answer_match(final, task.reference_answer)
            passed = ok
            judge_score = 5 if ok else 1
            feedback = (
                f"answer matched reference (extracted {final!r})" if ok
                else f"answer {final!r} did not match reference: {task.reference_answer!r}"
            )
        elif task.grading_type == GradingType.SWEBENCH and settings.swebench_enabled:
            # Objective code axis: apply the agent's patch to the real repo and run
            # its test suite via the official SWE-bench harness (in WSL2 + Docker).
            instance_id = (task.meta or {}).get("instance_id")
            patch = extract_patch(response_text)
            if not instance_id:
                passed, judge_score, feedback = False, 1, "task has no SWE-bench instance_id"
            elif not patch:
                passed, judge_score, feedback = False, 1, "agent produced no patch (empty diff)"
            else:
                graded = await grade_patches_async({instance_id: patch})
                r = graded[instance_id]
                passed = r.resolved
                judge_score = 5 if r.resolved else 1
                feedback = f"[{instance_id}] {r.detail}"
        else:
            # JUDGE task, or CODE task without a test -> let the judge decide
            # correctness (no more automatic 5/5 for merely not crashing).
            grade = await self.judge.grade(
                JudgeRequest(
                    instruction=task.prompt,
                    response=response_text,
                    # Default to the single-agent auditor rubric when the task
                    # itself doesn't carry one.
                    rubric=task.rubric or FINAL_RUBRIC,
                    reference_answer=task.reference_answer,
                )
            )
            judge_score, feedback, votes, disagreement = _unpack(grade)
            passed = None  # reward derived from the pass threshold

        score = TaskScore(judge_score=judge_score, max_score=task.max_score, passed=passed)
        result = TaskResult(
            evaluation_id=evaluation_id,
            task_id=task.id,
            agent_output=agent_output.raw,
            sandbox_stdout=sb_stdout,
            sandbox_stderr=sb_stderr,
            sandbox_exit_code=sb_exit,
            judge_score=judge_score,
            judge_feedback=feedback,
            judge_votes=votes,
            disagreement=disagreement,
            normalized_score=score.normalized,
            reward=score.reward,
            final_answer=response_text,
        )
        return result, score

    # ── agentic / multi-agent ────────────────────────────────────────────
    async def _run_agentic_task(
        self, evaluation_id: uuid.UUID, task: Task, config: dict, *, multi: bool
    ) -> tuple[TaskResult, TaskScore]:
        runner = AgenticRunner(config, multi_agent=multi)
        step_models: list[AgentStep] = []
        step_scores: list[int] = []

        async with self.sandbox.open_session() as session:
            outcome = await runner.run(task.prompt, session)

            # 1. Grade EVERY step of the trajectory.
            for idx, st in enumerate(outcome.steps, start=1):
                grade = await self.judge.grade(
                    JudgeRequest(
                        instruction=build_step_instruction(task.prompt, idx, st.role, outcome.plan),
                        response=format_step_response(
                            thought=st.thought, code=st.code,
                            stdout=st.stdout, stderr=st.stderr, exit_code=st.exit_code,
                        ),
                        rubric=STEP_RUBRIC,
                    )
                )
                s_score, s_fb, s_votes, _ = _unpack(grade)
                step_scores.append(s_score)
                step_models.append(_to_step_model(st, idx, s_score, s_fb, s_votes))

            # 2. Holistic grade of the whole run.
            traj = [_step_dict(st, i) for i, st in enumerate(outcome.steps, start=1)]
            final_grade = await self.judge.grade(
                JudgeRequest(
                    instruction=task.prompt,
                    response=format_trajectory(traj, outcome.final_answer),
                    # Multi-agent systems get the MAS criteria; single agents the
                    # single-agent criteria. A task's own rubric still wins.
                    rubric=task.rubric or (MAS_FINAL_RUBRIC if multi else FINAL_RUBRIC),
                    reference_answer=task.reference_answer,
                )
            )
            final_score, final_fb, final_votes, disagreement = _unpack(final_grade)

            # 3. Deterministic correctness gate for CODE tasks (same live session).
            passed: bool | None
            if task.grading_type == GradingType.CODE and task.test_code and settings.allow_code_execution:
                ok, detail = await self._check_test_code(
                    agent_stdout=outcome.final_answer, agent_code=None,
                    test_code=task.test_code, session=session,
                )
                passed = ok
                final_fb = f"{detail}\n\n{final_fb}"
            elif task.grading_type == GradingType.MATCH:
                final = extract_final_answer(outcome.final_answer)
                passed = answer_match(final, task.reference_answer)
                detail = (
                    f"answer matched reference (extracted {final!r})" if passed
                    else f"answer {final!r} did not match reference: {task.reference_answer!r}"
                )
                final_fb = f"{detail}\n\n{final_fb}"
            else:
                passed = None

        # 4. Blend per-step quality with the final outcome.
        effective = blend_agentic_score(step_scores, final_score)
        if passed is False:
            effective = min(effective, 2)
        mean_step = round(sum(step_scores) / len(step_scores), 3) if step_scores else None

        score = TaskScore(judge_score=effective, max_score=task.max_score, passed=passed)
        last = outcome.steps[-1] if outcome.steps else None
        result = TaskResult(
            evaluation_id=evaluation_id,
            task_id=task.id,
            agent_output=outcome.final_answer,
            sandbox_stdout=(last.stdout if last else None),
            sandbox_stderr=(last.stderr if last else None),
            sandbox_exit_code=(last.exit_code if last else None),
            judge_score=effective,
            judge_feedback=final_fb,
            judge_votes=final_votes,
            disagreement=disagreement,
            normalized_score=score.normalized,
            reward=score.reward,
            final_answer=outcome.final_answer,
            step_count=len(outcome.steps),
            mean_step_score=mean_step,
            steps=step_models,
        )
        return result, score


def _step_dict(st: StepRecord, idx: int) -> dict:
    return {
        "step_index": idx,
        "role": st.role,
        "thought": st.thought,
        "action_code": st.code,
        "observation_stdout": st.stdout,
        "observation_stderr": st.stderr,
    }


def _to_step_model(
    st: StepRecord, idx: int, score: int, feedback: str, votes: list[dict] | None
) -> AgentStep:
    return AgentStep(
        step_index=idx,
        role=st.role,
        thought=st.thought,
        action_code=st.code,
        observation_stdout=st.stdout,
        observation_stderr=st.stderr,
        exit_code=st.exit_code,
        judge_score=score,
        judge_feedback=feedback,
        judge_votes=votes,
    )
