"""Agentic runner — an agent that *works inside* the sandbox over many steps.

Unlike the one-shot runner (prompt -> one code block), this drives a loop:

    think -> run code in the LIVE sandbox -> observe result -> think again ...

until the agent declares it is done (``FINAL: ...``) or hits the step cap. The
sandbox session is persistent, so state built up in one step is visible in the
next — the agent genuinely lives in the environment.

`multi_agent=True` adds collaborating roles around the worker loop:
    Planner (drafts a plan) -> Worker (the loop) -> Reviewer (final critique)
which is the shape real "multi-agent systems" use for hard tasks.

Provider is pluggable: an OpenAI-compatible endpoint or Anthropic Claude. With
no usable API key it falls back to a deterministic offline mock so the whole
pipeline (steps, per-step judging, scoring) is exercisable without spend.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import get_logger
from app.services.sandbox.e2b_sandbox import SandboxSession

logger = get_logger(__name__)

_CODE_FENCE_RE = re.compile(r"```(?:python)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)
_FINAL_RE = re.compile(r"^\s*FINAL:\s*(.*)$", re.IGNORECASE | re.DOTALL | re.MULTILINE)

_WORKER_SYSTEM = (
    "You are an autonomous coding agent operating inside a LIVE Python sandbox. "
    "State (variables, files, installed packages) PERSISTS between your steps, so "
    "build the solution up incrementally. Each turn do exactly ONE of:\n"
    "  • Take an action: write a short THOUGHT, then a single ```python``` code "
    "block to execute in the sandbox.\n"
    "  • Finish: write a line starting with `FINAL:` followed by the answer, with "
    "NO code block that turn.\n"
    "Be efficient: no aimless, repeated, or off-task actions. Verify your result "
    "before finishing."
)

_PLANNER_SYSTEM = (
    "You are a planning agent. Given a task that another agent will solve by "
    "writing and running code in a sandbox, produce a short numbered plan (3-5 "
    "concise steps). Output only the plan."
)

_REVIEWER_SYSTEM = (
    "You are a critical reviewer agent. Given the task, what the worker agent did, "
    "and its final answer, judge whether the task was actually solved correctly. "
    "Point out any errors or gaps in 2-4 sentences and end with VERDICT: PASS or "
    "VERDICT: FAIL."
)


@dataclass
class StepRecord:
    role: str  # "agent" | "planner" | "worker" | "reviewer"
    thought: str
    code: str | None = None
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None


@dataclass
class AgenticOutcome:
    steps: list[StepRecord] = field(default_factory=list)
    final_answer: str = ""
    plan: str | None = None


@dataclass
class _Action:
    thought: str
    code: str | None = None
    final: str | None = None


def _parse_action(text: str) -> _Action:
    """Turn an agent reply into an action: run code, or finish."""
    final_match = _FINAL_RE.search(text)
    code_match = _CODE_FENCE_RE.search(text)
    # Prefer a code action unless FINAL clearly comes without code.
    if code_match:
        thought = text[: code_match.start()].strip()
        return _Action(thought=thought, code=code_match.group(1).strip())
    if final_match:
        thought = text[: final_match.start()].strip()
        return _Action(thought=thought, final=final_match.group(1).strip())
    # No code and no FINAL marker: treat the whole reply as the final answer.
    return _Action(thought="", final=text.strip())


class AgenticRunner:
    def __init__(self, agent_config: dict | None, *, multi_agent: bool) -> None:
        self.config = agent_config or {}
        self.multi_agent = multi_agent
        self.max_steps = int(self.config.get("max_steps") or settings.agent_max_steps)

    # ── Provider resolution ──────────────────────────────────
    def _provider(self) -> str:
        p = str(self.config.get("provider") or "").lower()
        if p in ("openai", "anthropic"):
            return p
        if self.config.get("base_url"):
            return "openai"
        return "anthropic"  # default demo provider (reuses the Anthropic account)

    def _api_key(self, provider: str) -> str | None:
        if self.config.get("api_key"):
            return self.config["api_key"]
        if provider == "anthropic":
            return settings.judge_anthropic_api_key
        return settings.agent_default_api_key

    def _is_mock(self) -> bool:
        return not self._api_key(self._provider())

    # ── Public entrypoint ────────────────────────────────────
    async def run(self, task_prompt: str, session: SandboxSession) -> AgenticOutcome:
        worker_role = "worker" if self.multi_agent else "agent"
        steps: list[StepRecord] = []
        plan: str | None = None

        if self.multi_agent:
            plan = await self._plan(task_prompt)
            steps.append(StepRecord(role="planner", thought=plan))

        transcript: list[tuple[str, str, str, str, int]] = []  # thought, code, stdout, stderr, exit
        final_answer = ""

        for _ in range(self.max_steps):
            action = await self._next_action(task_prompt, plan, transcript)
            if action.final is not None and action.code is None:
                if action.thought:
                    steps.append(StepRecord(role=worker_role, thought=action.thought))
                final_answer = action.final
                break
            obs = await session.run(action.code or "")
            steps.append(
                StepRecord(
                    role=worker_role,
                    thought=action.thought,
                    code=action.code,
                    stdout=obs.stdout,
                    stderr=obs.stderr,
                    exit_code=obs.exit_code,
                )
            )
            transcript.append(
                (action.thought, action.code or "", obs.stdout, obs.stderr, obs.exit_code)
            )
            # Stop early if the agent loops on the exact same action.
            if len(transcript) >= 2 and transcript[-1][1] and transcript[-1][1] == transcript[-2][1]:
                final_answer = obs.stdout.strip()
                break

        if not final_answer:
            final_answer = transcript[-1][2].strip() if transcript else ""

        if self.multi_agent:
            review = await self._review(task_prompt, transcript, final_answer)
            steps.append(StepRecord(role="reviewer", thought=review))

        return AgenticOutcome(steps=steps, final_answer=final_answer, plan=plan)

    # ── Role calls ───────────────────────────────────────────
    async def _plan(self, task_prompt: str) -> str:
        if self._is_mock():
            return (
                "1. Understand what the task asks.\n"
                "2. Write a small program to compute the result.\n"
                "3. Run it in the sandbox and check the output.\n"
                "4. Report the final answer."
            )
        return await self._chat(_PLANNER_SYSTEM, f"Task:\n{task_prompt.strip()}")

    async def _review(self, task_prompt: str, transcript: list, final_answer: str) -> str:
        if self._is_mock():
            return (
                "[mock-reviewer] The worker ran code and produced output. Results look "
                "plausible but verification was limited. VERDICT: PASS"
            )
        user = (
            f"Task:\n{task_prompt.strip()}\n\n"
            f"What the worker did:\n{_render_transcript(transcript)}\n\n"
            f"Final answer:\n{final_answer.strip() or '(none)'}"
        )
        return await self._chat(_REVIEWER_SYSTEM, user)

    async def _next_action(self, task_prompt: str, plan: str | None, transcript: list) -> _Action:
        if self._is_mock():
            return self._mock_action(task_prompt, transcript)
        plan_block = f"\nYour plan:\n{plan.strip()}\n" if plan else ""
        history = _render_transcript(transcript)
        history_block = f"\nWhat you've done so far:\n{history}\n" if history else ""
        user = (
            f"Task:\n{task_prompt.strip()}\n{plan_block}{history_block}\n"
            "What is your next step?"
        )
        reply = await self._chat(_WORKER_SYSTEM, user)
        return _parse_action(reply)

    def _mock_action(self, task_prompt: str, transcript: list) -> _Action:
        """Deterministic offline behaviour: one real sandbox action, then finish."""
        if not transcript:
            snippet = task_prompt.strip().replace("\n", " ")[:80]
            code = (
                "result = 'mock agent working on: " + snippet.replace("'", " ") + "'\n"
                "print(result)"
            )
            return _Action(thought="Start by running a small program in the sandbox.", code=code)
        last_stdout = transcript[-1][2].strip()
        return _Action(thought="Output produced; finishing.", final=last_stdout or "done")

    # ── LLM transport ────────────────────────────────────────
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8), reraise=True)
    async def _chat(self, system: str, user: str) -> str:
        provider = self._provider()
        key = self._api_key(provider)
        model = self.config.get("model")
        if provider == "anthropic":
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(api_key=key)
            message = await client.messages.create(
                model=model or settings.judge_anthropic_model,
                max_tokens=1024,
                temperature=0.2,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return "".join(
                b.text for b in message.content if getattr(b, "type", None) == "text"
            )
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            base_url=self.config.get("base_url") or settings.agent_default_base_url,
            api_key=key,
        )
        completion = await client.chat.completions.create(
            model=model or settings.agent_default_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
            max_tokens=1024,
        )
        return completion.choices[0].message.content or ""


def _render_transcript(transcript: list) -> str:
    lines: list[str] = []
    for i, (thought, code, stdout, stderr, exit_code) in enumerate(transcript, start=1):
        lines.append(f"Step {i}:")
        if thought:
            lines.append(f"  thought: {thought.strip()[:300]}")
        if code:
            lines.append(f"  code: {code.strip()[:400]}")
        if stdout.strip():
            lines.append(f"  stdout: {stdout.strip()[:400]}")
        if stderr.strip():
            lines.append(f"  error: {stderr.strip()[:300]} (exit {exit_code})")
    return "\n".join(lines)
