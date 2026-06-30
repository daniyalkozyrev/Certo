/**
 * Typed client for the Certo FastAPI backend.
 *
 * Base URL comes from NEXT_PUBLIC_API_URL (defaults to local backend).
 * All resource routes live under /api/v1.
 */

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

const PREFIX = "/api/v1";

// ── Backend domain types (mirror app/schemas on the server) ──────────────

export type EvaluationStatus = "pending" | "running" | "completed" | "failed";
export type GradingType = "judge" | "code" | "match";

export interface AgentConfig {
  base_url?: string | null;
  api_key?: string | null;
  model?: string | null;
  system_prompt?: string | null;
  provider?: string | null; // "anthropic" | "openai"
  max_steps?: number | null;
}

export type AgentType = "llm_endpoint" | "agentic" | "multi_agent";

export interface Agent {
  id: string;
  name: string;
  description: string | null;
  agent_type: string;
  config: AgentConfig & Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface Task {
  id: string;
  benchmark_id: string;
  prompt: string;
  rubric: string | null;
  reference_answer: string | null;
  grading_type: GradingType;
  test_code: string | null;
  max_score: number;
  created_at: string;
}

export interface Benchmark {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  tasks: Task[];
}

export interface JudgeVote {
  judge: string;
  score: number;
  feedback: string;
}

export interface AgentStep {
  id: string;
  step_index: number;
  role: string; // "agent" | "planner" | "worker" | "reviewer"
  thought: string | null;
  action_code: string | null;
  observation_stdout: string | null;
  observation_stderr: string | null;
  exit_code: number | null;
  judge_score: number | null;
  judge_feedback: string | null;
  judge_votes: JudgeVote[] | null;
}

export interface TaskResult {
  id: string;
  task_id: string;
  agent_output: string | null;
  sandbox_stdout: string | null;
  sandbox_stderr: string | null;
  sandbox_exit_code: number | null;
  judge_score: number | null;
  judge_feedback: string | null;
  judge_votes: JudgeVote[] | null;
  disagreement: "Low" | "Medium" | "High" | null;
  normalized_score: number | null;
  reward: number | null;
  // Agentic runs: final answer + graded per-step trajectory.
  final_answer: string | null;
  step_count: number | null;
  mean_step_score: number | null;
  steps: AgentStep[];
  created_at: string;
}

export interface Evaluation {
  id: string;
  agent_id: string;
  benchmark_id: string;
  status: EvaluationStatus;
  trust_score: number | null;
  pass_rate: number | null;
  summary: Record<string, unknown> | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface EvaluationDetail extends Evaluation {
  results: TaskResult[];
}

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

// ── Request helpers ──────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// ── Auth token storage ───────────────────────────────────────────────────

const TOKEN_KEY = "certo.token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${PREFIX}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(init?.headers || {}),
      },
      cache: "no-store",
    });
  } catch {
    throw new ApiError(0, `Cannot reach backend at ${API_BASE}. Is it running?`);
  }
  if (!res.ok) {
    let msg = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      msg = body?.error?.message || body?.detail || msg;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, msg);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ── Auth ─────────────────────────────────────────────────────────────────

export interface User {
  id: string;
  email: string;
  name: string | null;
  auth_provider: string;
  created_at: string;
}

export interface AuthConfig {
  google_enabled: boolean;
  email_mode: string;
}

export function getAuthConfig() {
  return request<AuthConfig>(`/auth/config`);
}
export function requestLoginCode(email: string) {
  return request<{ sent: boolean; dev_code: string | null }>(`/auth/request-code`, {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}
export function verifyLoginCode(email: string, code: string) {
  return request<{ access_token: string; token_type: string; user: User }>(`/auth/verify`, {
    method: "POST",
    body: JSON.stringify({ email, code }),
  });
}
export function getMe() {
  return request<User>(`/auth/me`);
}
export function googleAuthorizeUrl(): string {
  return `${API_BASE}${PREFIX}/auth/google/authorize`;
}

// ── Health ───────────────────────────────────────────────────────────────

export async function health(): Promise<{ status: string; env: string }> {
  const res = await fetch(`${API_BASE}/health`, { cache: "no-store" });
  if (!res.ok) throw new ApiError(res.status, "Health check failed");
  return res.json();
}

// ── Agents ───────────────────────────────────────────────────────────────

export function listAgents(limit = 100, offset = 0) {
  return request<Page<Agent>>(`/agents?limit=${limit}&offset=${offset}`);
}
export function getAgent(id: string) {
  return request<Agent>(`/agents/${id}`);
}
export function createAgent(payload: {
  name: string;
  description?: string;
  agent_type?: AgentType;
  config?: AgentConfig;
}) {
  return request<Agent>(`/agents`, {
    method: "POST",
    body: JSON.stringify({ agent_type: "llm_endpoint", config: {}, ...payload }),
  });
}

// ── Benchmarks ───────────────────────────────────────────────────────────

export function listBenchmarks(limit = 100, offset = 0) {
  return request<Page<Benchmark>>(`/benchmarks?limit=${limit}&offset=${offset}`);
}
export function getBenchmark(id: string) {
  return request<Benchmark>(`/benchmarks/${id}`);
}
export function createBenchmark(payload: {
  name: string;
  description?: string;
  tasks: Array<{
    prompt: string;
    rubric?: string;
    reference_answer?: string;
    grading_type?: GradingType;
    test_code?: string;
    max_score?: number;
  }>;
}) {
  return request<Benchmark>(`/benchmarks`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ── Evaluations ──────────────────────────────────────────────────────────

export function listEvaluations(limit = 100, offset = 0) {
  return request<Page<Evaluation>>(`/evaluations?limit=${limit}&offset=${offset}`);
}
export function getEvaluation(id: string) {
  return request<EvaluationDetail>(`/evaluations/${id}`);
}
export function createEvaluation(payload: { agent_id: string; benchmark_id: string }) {
  return request<Evaluation>(`/evaluations`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/** Poll an evaluation until it reaches a terminal state (or times out). */
export async function pollEvaluation(
  id: string,
  { intervalMs = 1500, timeoutMs = 180_000 } = {},
): Promise<EvaluationDetail> {
  const start = Date.now();
  // eslint-disable-next-line no-constant-condition
  while (true) {
    const ev = await getEvaluation(id);
    if (ev.status === "completed" || ev.status === "failed") return ev;
    if (Date.now() - start > timeoutMs) return ev;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}

/** A ready-made demo benchmark so the UI is usable without backend seeding. */
export function createDemoBenchmark() {
  return createBenchmark({
    name: "Sanity Benchmark",
    description: "Quick demo benchmark created from the UI.",
    tasks: [
      {
        prompt: "Write a program that prints the sum of 2 and 3.",
        rubric:
          "Does the response correctly output 5?\nScore 1: wrong or no output.\nScore 3: partially correct.\nScore 5: prints exactly 5.",
        reference_answer: "5",
        grading_type: "judge",
        max_score: 5,
      },
      {
        prompt: "Print the string 'hello world'.",
        grading_type: "code",
        test_code: "assert True",
        max_score: 5,
      },
    ],
  });
}

// ── Traces (trace-ingestion core) ─────────────────────────────────────────

export type TraceStatus = "running" | "completed" | "failed";

export interface Span {
  id: string;
  step_index: number;
  kind: string; // llm | tool | agent | observation | handoff
  name: string | null;
  input: unknown;
  output: unknown;
  error: string | null;
  tokens: number | null;
  latency_ms: number | null;
  judge_score: number | null;
  judge_feedback: string | null;
  judge_votes: JudgeVote[] | null;
}

export interface Trace {
  id: string;
  agent_id: string | null;
  name: string | null;
  task: string | null;
  final_output: string | null;
  status: TraceStatus;
  source: string; // sdk | sandbox | agentic
  meta: Record<string, unknown> | null;
  trust_score: number | null;
  summary: Record<string, unknown> | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface TraceDetail extends Trace {
  spans: Span[];
}

export function listTraces(limit = 100, offset = 0) {
  return request<Page<Trace>>(`/traces?limit=${limit}&offset=${offset}`);
}
export function getTrace(id: string) {
  return request<TraceDetail>(`/traces/${id}`);
}
export function ingestTrace(payload: {
  task: string;
  name?: string;
  spans?: Array<{ kind: string; name?: string; input?: unknown; output?: unknown; error?: string }>;
  final_output?: string;
  expected_output?: string;
  test_code?: string;
  meta?: Record<string, unknown>;
}) {
  return request<Trace>(`/traces`, { method: "POST", body: JSON.stringify(payload) });
}

/** Poll a trace until it is scored (or times out). */
export async function pollTrace(
  id: string,
  { intervalMs = 1500, timeoutMs = 180_000 } = {},
): Promise<TraceDetail> {
  const start = Date.now();
  // eslint-disable-next-line no-constant-condition
  while (true) {
    const t = await getTrace(id);
    if (t.status === "completed" || t.status === "failed") return t;
    if (Date.now() - start > timeoutMs) return t;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}
