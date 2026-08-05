/**
 * Typed client for the Cadence FastAPI backend (api/routers/sessions.py).
 * Base URL is env-configurable so the same build can point at a local
 * dev server or a deployed API.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface SessionOut {
  id: string;
  scenario: string;
  status: string;
  created_at: string;
}

export interface FeedbackItemOut {
  criterion: string;
  observation: string;
  rationale: string;
  repair: string;
  evidence_text: string;
  evidence_start_ms: number;
  evidence_end_ms: number;
}

export interface DrillOut {
  id: string;
  title: string;
  prompt: string;
  duration_minutes: string;
  targets_criterion: string | null;
}

export interface AnalysisResultOut {
  session_id: string;
  rubric_version: string;
  model_version: string;
  transcript_text: string;
  metrics_summary: Record<string, unknown>;
  feedback_items: FeedbackItemOut[];
  drill: DrillOut;
  created_at: string;
}

async function asJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // response wasn't JSON — keep statusText
    }
    throw new Error(`${res.status} ${detail}`);
  }
  return res.json() as Promise<T>;
}

export async function createSession(scenario: string): Promise<SessionOut> {
  const res = await fetch(`${API_BASE}/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scenario }),
  });
  return asJson<SessionOut>(res);
}

/** Upload one chunk at `offset`. Safe to retry the same offset after a dropped connection. */
export async function uploadChunk(
  sessionId: string,
  offset: number,
  chunk: Blob,
): Promise<{ bytes_received: number }> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/media?offset=${offset}`, {
    method: "POST",
    body: chunk,
  });
  return asJson<{ bytes_received: number }>(res);
}

export async function getUploadStatus(sessionId: string): Promise<{ bytes_received: number }> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/media/status`);
  return asJson<{ bytes_received: number }>(res);
}

export async function analyzeSession(sessionId: string): Promise<AnalysisResultOut> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/analyze`, { method: "POST" });
  return asJson<AnalysisResultOut>(res);
}

export async function getResult(sessionId: string): Promise<AnalysisResultOut> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/result`);
  return asJson<AnalysisResultOut>(res);
}

export async function deleteSession(sessionId: string): Promise<void> {
  await fetch(`${API_BASE}/sessions/${sessionId}`, { method: "DELETE" });
}
