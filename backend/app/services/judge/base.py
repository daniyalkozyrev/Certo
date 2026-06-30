"""Judge provider interface and shared types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class JudgeRequest:
    instruction: str
    response: str
    rubric: str
    reference_answer: str | None = None


@dataclass
class JudgeResult:
    """Output of a single judge."""

    score: int  # absolute grade, 1..5
    feedback: str


@dataclass
class JudgeVote:
    """One judge's vote within an ensemble."""

    judge: str  # human-readable judge name (model id)
    score: int
    feedback: str


@dataclass
class EnsembleResult:
    """Aggregated verdict from one or more judges."""

    score: int  # consensus (rounded mean), 1..5
    feedback: str  # combined feedback
    votes: list[JudgeVote] = field(default_factory=list)
    disagreement: str = "Low"  # "Low" | "Medium" | "High"


class JudgeProvider(Protocol):
    """Any LLM-as-a-Judge backend. Swap implementations behind this interface."""

    name: str

    async def grade(self, request: JudgeRequest) -> JudgeResult: ...
