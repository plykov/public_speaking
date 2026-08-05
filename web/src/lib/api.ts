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
  first_language_code: string | null;
  calibration_note: string | null;
}

export interface L1CalibrationProfileOut {
  code: string;
  label: string;
  calibration_note: string;
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

export interface TranscriptWordOut {
  seq_index: number;
  text: string;
  start_ms: number;
  end_ms: number;
  confidence: number;
}

export interface ReminderOut {
  id: string;
  user_id: string;
  days: string[];
  time_of_day: string;
}

export interface StreakOut {
  current_streak: number;
  longest_streak: number;
  freeze_used_in_current_streak: boolean;
  last_practice_date: string | null;
}

export interface CheckoutSessionOut {
  id: string;
  tier: string;
  status: string;
  url: string;
}

export interface SubscriptionOut {
  tier: string;
  status: string;
  current_period_end: string | null;
  analyses_this_month: number;
  analyses_limit: number | null;
}

export interface SlideDeckOut {
  filename: string;
  page_count: number;
  thumbnail_urls: string[];
}

export interface SlideTransitionOut {
  slide_index: number;
  timestamp_ms: number;
}

export interface AttemptSummaryOut {
  session_id: string;
  parent_session_id: string | null;
  scenario: string;
  created_at: string;
  wpm_overall: number;
  filler_rate_per_100_words: number;
  hedging_rate_per_100_words: number;
  point_position_score: number;
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
  firstLanguageCode: string | null = null,
): Promise<L1ProfileOut> {
  const res = await fetch(`${API_BASE}/users/${userId}/l1-profile`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      first_language: firstLanguage,
      self_declared_confidence: selfDeclaredConfidence,
      first_language_code: firstLanguageCode,
    }),
  });
  return asJson<L1ProfileOut>(res);
}

export async function fetchL1CalibrationProfiles(): Promise<L1CalibrationProfileOut[]> {
  const res = await fetch(`${API_BASE}/l1-calibration-profiles`);
  return asJson<L1CalibrationProfileOut[]>(res);
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

export async function uploadSlideDeck(
  sessionId: string,
  file: File,
): Promise<SlideDeckOut> {
  const res = await fetch(
    `${API_BASE}/sessions/${sessionId}/slides?filename=${encodeURIComponent(file.name)}`,
    { method: "POST", body: file, headers: { "Content-Type": "application/pdf" } },
  );
  return asJson<SlideDeckOut>(res);
}

export async function fetchSlideDeck(sessionId: string): Promise<SlideDeckOut | null> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/slides`);
  if (res.status === 404) return null;
  return asJson<SlideDeckOut>(res);
}

export function slideThumbnailUrl(path: string): string {
  return `${API_BASE}${path}`;
}

export async function upsertSlideTransitions(
  sessionId: string,
  transitions: SlideTransitionOut[],
): Promise<SlideTransitionOut[]> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/slide-transitions`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ transitions }),
  });
  return asJson<SlideTransitionOut[]>(res);
}

export async function fetchSlideTransitions(sessionId: string): Promise<SlideTransitionOut[]> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/slide-transitions`);
  return asJson<SlideTransitionOut[]>(res);
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

/** §4.1 M8: the editable word list for a session. */
export async function getTranscript(sessionId: string): Promise<TranscriptWordOut[]> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/transcript`);
  return asJson<TranscriptWordOut[]>(res);
}

/** Submit corrected words (same length/order as the original) and re-score. */
export async function updateTranscript(
  sessionId: string,
  words: string[],
): Promise<AnalysisResultOut> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/transcript`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ words }),
  });
  return asJson<AnalysisResultOut>(res);
}

export async function getAttempts(userId: string): Promise<AttemptSummaryOut[]> {
  const res = await fetch(`${API_BASE}/users/${userId}/attempts`);
  return asJson<AttemptSummaryOut[]>(res);
}

/** Full account export (§4.1 M11) — profile + every session's transcript, metrics, feedback. */
export async function exportUserData(userId: string): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_BASE}/users/${userId}/export`);
  return asJson<Record<string, unknown>>(res);
}

/** Account delete (§4.1 M11, §6.5) — every session's media/rows, the L1 profile, and the user row. */
export async function deleteAccount(userId: string): Promise<void> {
  await fetch(`${API_BASE}/users/${userId}`, { method: "DELETE" });
}

export interface ShareLinkOut {
  id: string;
  token: string;
  label: string | null;
  can_view_progress: boolean;
  can_view_transcripts: boolean;
  can_view_feedback: boolean;
  created_at: string;
  expires_at: string | null;
  revoked: boolean;
}

export interface SharedFeedbackItemOut {
  criterion: string;
  observation: string;
  rationale: string;
  repair: string;
}

export interface SharedAttemptOut {
  session_id: string;
  scenario: string;
  created_at: string;
  wpm_overall: number | null;
  filler_rate_per_100_words: number | null;
  hedging_rate_per_100_words: number | null;
  point_position_score: number | null;
  transcript_text: string | null;
  feedback_items: SharedFeedbackItemOut[] | null;
}

export interface SharedViewOut {
  label: string | null;
  can_view_progress: boolean;
  can_view_transcripts: boolean;
  can_view_feedback: boolean;
  attempts: SharedAttemptOut[];
}

/** §4.2 — private coach/manager share links, granular permissions. */
export async function createShareLink(
  userId: string,
  options: {
    label?: string;
    canViewProgress?: boolean;
    canViewTranscripts?: boolean;
    canViewFeedback?: boolean;
    expiresInDays?: number;
  },
): Promise<ShareLinkOut> {
  const res = await fetch(`${API_BASE}/users/${userId}/share-links`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      label: options.label ?? null,
      can_view_progress: options.canViewProgress ?? true,
      can_view_transcripts: options.canViewTranscripts ?? false,
      can_view_feedback: options.canViewFeedback ?? false,
      expires_in_days: options.expiresInDays ?? null,
    }),
  });
  return asJson<ShareLinkOut>(res);
}

export async function listShareLinks(userId: string): Promise<ShareLinkOut[]> {
  const res = await fetch(`${API_BASE}/users/${userId}/share-links`);
  return asJson<ShareLinkOut[]>(res);
}

export async function revokeShareLink(userId: string, shareId: string): Promise<void> {
  await fetch(`${API_BASE}/users/${userId}/share-links/${shareId}`, { method: "DELETE" });
}

export async function fetchSharedView(token: string): Promise<SharedViewOut> {
  const res = await fetch(`${API_BASE}/share/${token}`);
  return asJson<SharedViewOut>(res);
}

/** §4.1 M10: store a reminder window. Storing the preference only — no
 * calendar integration or delivery infra exists to act on it yet. */
export async function upsertReminder(
  userId: string,
  days: string[],
  timeOfDay: string,
): Promise<ReminderOut> {
  const res = await fetch(`${API_BASE}/users/${userId}/reminder`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ days, time_of_day: timeOfDay }),
  });
  return asJson<ReminderOut>(res);
}

export async function getReminder(userId: string): Promise<ReminderOut | null> {
  const res = await fetch(`${API_BASE}/users/${userId}/reminder`);
  if (res.status === 404) return null;
  return asJson<ReminderOut>(res);
}

/** §4.1 M10: non-punitive streak, self-relative — see api/streaks.py. */
export async function getStreak(userId: string): Promise<StreakOut> {
  const res = await fetch(`${API_BASE}/users/${userId}/streak`);
  return asJson<StreakOut>(res);
}

/** §4.1 M12: no real Stripe here — see api/billing.py. "pro" | "event_sprint" only. */
export async function createCheckout(userId: string, tier: string): Promise<CheckoutSessionOut> {
  const res = await fetch(`${API_BASE}/users/${userId}/checkout`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tier }),
  });
  return asJson<CheckoutSessionOut>(res);
}

/** Dev-mode stand-in for a verified Stripe webhook firing after payment. */
export async function confirmCheckout(checkoutSessionId: string): Promise<CheckoutSessionOut> {
  const res = await fetch(`${API_BASE}/billing/checkout/${checkoutSessionId}/confirm`, {
    method: "POST",
  });
  return asJson<CheckoutSessionOut>(res);
}

export async function getSubscription(userId: string): Promise<SubscriptionOut> {
  const res = await fetch(`${API_BASE}/users/${userId}/subscription`);
  return asJson<SubscriptionOut>(res);
}
