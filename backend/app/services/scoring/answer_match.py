"""Objective answer-matching — the ground-truth axis (no code execution).

GAIA-style scoring: an agent's free-form final answer is checked against a known
correct answer by normalising both. Numbers are compared numerically, comma-lists
element-by-element, strings after lowercasing + stripping punctuation/articles.
This gives a verifiable pass/fail without running any untrusted code.
"""

from __future__ import annotations

import re
import string

_ARTICLES = {"a", "an", "the"}
_PUNCT = str.maketrans("", "", string.punctuation)

# GAIA protocol: the agent finishes with "FINAL ANSWER: <x>". Matching the whole
# reasoning trace is unreliable (stray numbers/words), so we extract that line.
_FINAL_RE = re.compile(r"final\s*answer\s*:\s*", re.IGNORECASE)


def extract_final_answer(text: str | None) -> str:
    """Return the text after the last 'FINAL ANSWER:' marker, else the input.

    Lets a verbose agent reason out loud yet still be graded on its stated final
    answer. Harmless on already-clean answers (no marker -> returned as-is)."""
    if not text:
        return text or ""
    matches = list(_FINAL_RE.finditer(text))
    if matches:
        tail = text[matches[-1].end():].strip()
        # Keep only the first line of the answer (drop any trailing prose).
        return tail.splitlines()[0].strip() if tail else tail
    return text.strip()


def _norm(s: str) -> str:
    s = str(s).strip().lower().translate(_PUNCT)
    return " ".join(w for w in s.split() if w not in _ARTICLES)


def _as_number(s: str) -> float | None:
    t = str(s).strip().replace(",", "").replace("$", "").replace("%", "").replace(" ", "")
    try:
        return float(t)
    except ValueError:
        return None


def _numbers_in(text: str) -> list[float]:
    out: list[float] = []
    for tok in re.findall(r"-?\d[\d,]*\.?\d*", text or ""):
        n = _as_number(tok)
        if n is not None:
            out.append(n)
    return out


def answer_match(predicted: str | None, expected: str | None) -> bool:
    """True if `predicted` answers `expected`. Lenient enough for prose answers,
    strict enough to require the right value(s)."""
    if expected is None:
        return False
    pred = (predicted or "").strip()
    exp = str(expected).strip()
    if not exp:
        return False

    # Comma-list answer: every expected element must appear in the prediction.
    if "," in exp:
        parts = [p for p in (x.strip() for x in exp.split(",")) if p]
        if len(parts) > 1:
            return all(answer_match(pred, p) for p in parts)

    # Numeric answer: compare values (tolerant of formatting / surrounding prose).
    exp_num = _as_number(exp)
    if exp_num is not None:
        return any(abs(exp_num - n) <= 1e-6 * max(1.0, abs(exp_num)) for n in _numbers_in(pred))

    # String answer: normalised exact match, or expected appears as a phrase.
    np, ne = _norm(pred), _norm(exp)
    if not ne:
        return False
    if np == ne:
        return True
    # whole-word/phrase containment (avoids 'cat' matching 'category')
    return re.search(rf"(?<!\w){re.escape(ne)}(?!\w)", np) is not None
