"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { fetchSharedView, type SharedViewOut } from "@/lib/api";

export default function SharedViewPage() {
  const params = useParams<{ token: string }>();
  const [view, setView] = useState<SharedViewOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSharedView(params.token)
      .then(setView)
      .catch((err) =>
        setError(
          err instanceof Error && err.message.startsWith("410")
            ? "This share link has been revoked or has expired."
            : "This share link doesn't exist.",
        ),
      );
  }, [params.token]);

  if (error) {
    return (
      <div className="container stack">
        <h1>Shared progress</h1>
        <p className="error-banner">{error}</p>
      </div>
    );
  }

  if (!view) {
    return <div className="container">Loading…</div>;
  }

  return (
    <div className="container stack">
      <h1>{view.label ? `Shared progress — ${view.label}` : "Shared progress"}</h1>
      <p style={{ color: "var(--muted)" }}>
        A read-only view shared by a Cadence user. Raw recordings are never included in a
        share link, at any setting.
      </p>

      {view.attempts.length === 0 && (
        <div className="card">
          <p style={{ color: "var(--muted)" }}>No completed attempts yet.</p>
        </div>
      )}

      {view.attempts.map((attempt) => (
        <div className="card stack" key={attempt.session_id}>
          <div className="pill">
            {attempt.scenario} · {new Date(attempt.created_at).toLocaleDateString()}
          </div>

          {view.can_view_progress && (
            <div className="metric-grid">
              <div className="metric-tile">
                <div className="label">Words / min</div>
                <div className="value">{attempt.wpm_overall}</div>
              </div>
              <div className="metric-tile">
                <div className="label">Fillers / 100 words</div>
                <div className="value">{attempt.filler_rate_per_100_words}</div>
              </div>
              <div className="metric-tile">
                <div className="label">Hedging / 100 words</div>
                <div className="value">{attempt.hedging_rate_per_100_words}</div>
              </div>
              <div className="metric-tile">
                <div className="label">Point-first score</div>
                <div className="value">{attempt.point_position_score}</div>
              </div>
            </div>
          )}

          {attempt.transcript_text && (
            <div className="stack">
              <div className="pill">Transcript</div>
              <p>{attempt.transcript_text}</p>
            </div>
          )}

          {attempt.feedback_items && attempt.feedback_items.length > 0 && (
            <div className="stack">
              <div className="pill">Coaching feedback</div>
              {attempt.feedback_items.map((item, i) => (
                <div className="feedback-item" key={i}>
                  <div className="criterion">{item.criterion.replace(/_/g, " ")}</div>
                  <p>
                    <strong>{item.observation}</strong> {item.rationale}
                  </p>
                  <p>→ {item.repair}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
