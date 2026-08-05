/**
 * Typed client for the Cadence FastAPI backend (api/routers/*.py).
 * Base URL is env-configurable so the same build can point at a local
 * dev server or a deployed API.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface UserOut {
  id: string;
  created_at: string;
}

export interface L1ProfileOut {
  id: string;
  user_id: string;
  first_language: string;
  self_declared_confidence: string;
}

export interface SessionOut {
  id: string;
  user_id: string | null;
  parent_session_id: string | null;
  scenario: string;
  status: string;
  created_at: string;
}

export interface FeedbackItemOut {
  id: string;
  criterion: string;
  observation: string;
  rationale: string;
  repair: string;
  evidence_text: string;
  evidence_start_ms: number;
  evidence_end_ms: number;
  user_rating: boolean | null;
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

export async function createUser(): Promise<UserOut> {
  const res = await fetch(`${API_BASE}/users`, { method: "POST" });
  return asJson<UserOut>(res);
}

export async function upsertL1Profile(
  userId: string,
  firstLanguage: string,
  selfDeclaredConfidence: string,
): Promise<L1ProfileOut> {
  const res = await fetch(`${API_BASE}/users/${userId}/l1-profile`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      first_language: firstLanguage,
      self_declared_confidence: selfDeclaredConfidence,
    }),
  });
  return asJson<L1ProfileOut>(res);
}

export async function createSession(
  scenario: string,
  options?: { userId?: string; parentSessionId?: string },
): Promise<SessionOut> {
  const res = await fetch(`${API_BASE}/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      scenario,
      user_id: options?.userId ?? null,
      parent_session_id: options?.parentSessionId ?? null,
    }),
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

export async function rateFeedbackItem(
  feedbackItemId: string,
  useful: boolean,
): Promise<FeedbackItemOut> {
  const res = await fetch(`${API_BASE}/feedback-items/${feedbackItemId}/rating`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ useful }),
  });
  return asJson<FeedbackItemOut>(res);
}
