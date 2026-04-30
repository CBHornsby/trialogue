// Streaming SSE client for the debate API.

export type DebateEvent =
  | { type: "debate_started"; debate_id: string }
  | { type: "role_start"; role: string; provider: string; model: string }
  | { type: "token"; role: string; content: string }
  | { type: "usage"; role: string; input: number; output: number }
  | { type: "role_complete"; role: string }
  | { type: "error"; role?: string; message: string; debate_id?: string }
  | { type: "stopped"; role?: string; debate_id?: string }
  | { type: "done"; debate_id: string };

const API_BASE = "http://127.0.0.1:8000";

export async function streamDebate(
  question: string,
  onEvent: (event: DebateEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`${API_BASE}/api/debate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      messages: [{ role: "user", content: question }],
    }),
    signal,
  });
  await consumeSSE(response, onEvent);
}

export async function resumeDebate(
  debateId: string,
  fromRole: "proposer" | "critic" | "judge",
  onEvent: (event: DebateEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`${API_BASE}/api/debate/resume`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ debate_id: debateId, from_role: fromRole }),
    signal,
  });
  await consumeSSE(response, onEvent);
}

async function consumeSSE(
  response: Response,
  onEvent: (event: DebateEvent) => void,
): Promise<void> {
  if (!response.ok) {
    let errMsg = `Request failed: ${response.status}`;
    try {
      const data = await response.json();
      if (data?.detail) errMsg = data.detail;
    } catch {}
    throw new Error(errMsg);
  }

  if (!response.body) throw new Error("No response body");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const json = line.slice(6).trim();
        if (!json) continue;
        try {
          const event = JSON.parse(json) as DebateEvent;
          onEvent(event);
        } catch (e) {
          console.warn("Failed to parse SSE event:", json);
        }
      }
    }
  }
}

export async function getSettings(): Promise<any> {
  const r = await fetch(`${API_BASE}/api/settings`);
  if (!r.ok) throw new Error("Failed to load settings");
  return r.json();
}

export async function updateSettings(settings: any): Promise<void> {
  const r = await fetch(`${API_BASE}/api/settings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings),
  });
  if (!r.ok) throw new Error("Failed to save settings");
}

export async function clearApiKey(provider: "anthropic" | "openai" | "google"): Promise<void> {
  const r = await fetch(`${API_BASE}/api/settings/clear-key/${provider}`, {
    method: "POST",
  });
  if (!r.ok) throw new Error(`Failed to clear ${provider} key`);
}

export async function checkBackendHealth(): Promise<boolean> {
  try {
    const r = await fetch(`${API_BASE}/api/health`);
    return r.ok;
  } catch {
    return false;
  }
}

export async function listProviderModels(provider: string): Promise<string[]> {
  const r = await fetch(`${API_BASE}/api/list-models/${provider}`);
  if (!r.ok) {
    let errMsg = `Failed to list ${provider} models`;
    try {
      const data = await r.json();
      if (data?.detail) errMsg = data.detail;
    } catch {}
    throw new Error(errMsg);
  }
  const data = await r.json();
  return data.models || [];
}

export async function loadDebate(debateId: string): Promise<any> {
  const r = await fetch(`${API_BASE}/api/debate/${debateId}`);
  if (!r.ok) throw new Error("Failed to load debate");
  return r.json();
}
