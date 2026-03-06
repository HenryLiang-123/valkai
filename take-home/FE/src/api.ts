const API_BASE = "http://localhost:8000/api";

export interface Strategy {
  key: string;
  name: string;
  description: string;
}

export interface ChatEvent {
  type: "chat_message" | "saved_memory";
  content: string;
}

export interface Message {
  id: number;
  role: "user" | "assistant";
  message_type: "chat_message" | "saved_memory";
  content: string;
  created_at: string;
}

export interface SessionInfo {
  session_id: string;
  strategy: string;
  messages: Message[];
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
