const API_BASE = "http://localhost:8000/api";

export interface Strategy {
  key: string;
  name: string;
  description: string;
}

export interface ChatMessage {
  type: "chat_message";
  role: "user" | "assistant";
  text: string;
}

export interface ToolUseMessage {
  type: "tool_use";
  role: "assistant";
  tool_name: string;
}

export type ChatEvent = ChatMessage | ToolUseMessage;

export interface SessionInfo {
  session_id: string;
  strategy: string;
  messages: ChatEvent[];
}

export interface SessionSummary {
  id: string;
  strategy: string;
  created_at: string;
}

export async function fetchSessions(): Promise<SessionSummary[]> {
  const res = await fetch(`${API_BASE}/sessions/list`);
  return res.json();
}

export async function fetchStrategies(): Promise<Strategy[]> {
  const res = await fetch(`${API_BASE}/strategies`);
  return res.json();
}

export async function createSession(strategy: string): Promise<{ id: string }> {
  const res = await fetch(`${API_BASE}/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ strategy }),
  });
  return res.json();
}

export async function fetchMessages(sessionId: string): Promise<SessionInfo> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/messages`);
  return res.json();
}

export async function sendMessage(
  sessionId: string,
  message: string
): Promise<{ session_id: string; events: ChatEvent[] }> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/send`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  return res.json();
}

// ---------------------------------------------------------------------------
// Evals API
// ---------------------------------------------------------------------------

export interface HarnessRecall {
  pass: boolean;
  expected: string[];
  found: string[];
}

export interface HarnessStrategyResult {
  strategy: string;
  recall: { turn_7: HarnessRecall; turn_8: HarnessRecall };
  responses: { turn: number; user: string; assistant: string }[];
  tool_calls: { turn: number; tool: string; input: Record<string, string> }[];
}

export interface HarnessResult {
  type: "harness";
  strategies: string[];
  results: HarnessStrategyResult[];
}

export interface TestResult {
  test: string;
  status: "PASSED" | "FAILED" | "ERROR" | string;
}

export interface TestsResult {
  type: "tests";
  test_path: string;
  exit_code: number;
  passed: number;
  failed: number;
  errored: number;
  tests: TestResult[];
  summary: string;
  stdout: string;
  stderr: string;
}

export async function runHarness(
  strategies?: string[]
): Promise<HarnessResult> {
  const res = await fetch(`${API_BASE}/evals/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ type: "harness", strategies }),
  });
  return res.json();
}

export async function runTests(
  testPath: string = "evals/"
): Promise<TestsResult> {
  const res = await fetch(`${API_BASE}/evals/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ type: "tests", test_path: testPath }),
  });
  return res.json();
}
