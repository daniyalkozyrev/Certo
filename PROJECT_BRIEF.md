# For Daniyal Kozyrev

## Certo — Trust Scoring for AI Agents

### Description

Building an AI agent is one thing; knowing whether you can *trust* it is much harder. An agent that runs to completion without crashing looks like a success — but "it didn't error out" says nothing about whether it actually solved the task, reasoned soundly, used its tools correctly, or simply produced plausible-looking output that happens to be wrong. The hardest part of agent evaluation is exactly this: a single final answer hides everything that matters — the wrong turns, the lucky guesses, the steps that quietly failed. Judging an agent from its output alone is unreliable, and it gets worse as agents grow into multi-step and multi-agent systems whose real work happens out of sight.

Certo is a platform that evaluates an agent on what it *did*, not just what it *said*. An agent runs wherever it lives and sends Certo its full execution trace — the trajectory of every step it took: each reasoning move, tool call, sub-agent hand-off, and intermediate result. Certo ingests that trace and scores it on two independent axes. The **objective** axis asks the unforgiving question: is the answer actually right? — by matching it against a known ground-truth answer, or by running the agent's real code and patches against real test suites in an isolated sandbox. The **trajectory** axis asks the qualitative one: was the path itself good? — using an ensemble of LLM-as-a-judge graders that score every step and the run as a whole against explicit rubrics for correctness, tool mastery, efficiency, and safety.

Because Certo grades against real benchmarks with known outcomes (such as GAIA and SWE-bench) and executes the agent's own work rather than trusting its narration, it rewards genuine task-solving over confident-sounding guessing. The two axes blend into a single **TrustScore** (0–100), backed by per-step feedback and the judges' agreement or disagreement — turning a vague impression that "the agent worked" into a defensible, evidence-based verdict on how far that agent can actually be trusted.

### Goals

1. Ingest an agent's full execution trace — its trajectory of reasoning steps, tool calls, and sub-agent hand-offs — from wherever the agent runs, through a simple HTTP endpoint and a thin client SDK, so any agent can be evaluated without being rebuilt.
2. Score every trace on two independent axes: **objective correctness** against ground truth (answer-matching on benchmarks like GAIA; running the agent's code and patches against real test suites on SWE-bench, inside an isolated sandbox) and **trajectory quality** (an ensemble of LLM judges grading each step and the whole run against rubrics for correctness, tool use, efficiency, and safety).
3. Blend the two axes into a single 0–100 TrustScore with transparent, per-step feedback and judge-disagreement signals — so every score is backed by concrete evidence, never by "it didn't crash."
4. Validate across real, ground-truth benchmarks and many agent types — single-shot, multi-step (agentic), and multi-agent systems — to measure how well Certo separates agents that genuinely solve tasks from those that merely look like they do.
