"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getAttempts, type AttemptSummaryOut } from "@/lib/api";
import { getStoredUserId } from "@/lib/localUser";

interface MetricConfig {
  key: keyof Pick<
    AttemptSummaryOut,
    "filler_rate_per_100_words" | "hedging_rate_per_100_words" | "point_position_score"
  >;
  label: string;
  lowerIsBetter: boolean;
}

const METRICS: MetricConfig[] = [
  { key: "filler_rate_per_100_words", label: "Fillers / 100 words", lowerIsBetter: true },
  { key: "hedging_rate_per_100_words", label: "Hedging / 100 words", lowerIsBetter: true },
  { key: "point_position_score", label: "Point-first score", lowerIsBetter: false },
];

function bestAttempt(attempts: AttemptSummaryOut[], metric: MetricConfig): AttemptSummaryOut {
  return attempts.reduce((best, a) => {
    const better = metric.lowerIsBetter ? a[metric.key] < best[metric.key] : a[metric.key] > best[metric.key];
    return better ? a : best;
  }, attempts[0]);
}

function TrendRow({ attempts, metric }: { attempts: AttemptSummaryOut[]; metric: MetricConfig }) {
  const first = attempts[0];
  const best = bestAttempt(attempts, metric);
  const latest = attempts[attempts.length - 1];

  return (
    <div className="card stack">
      <div className="pill">{metric.label}</div>
      <div className="metric-grid">
        <div className="metric-tile">
          <div className="label">First attempt</div>
          <div className="value">{first[metric.key]}</div>
        </div>
        <div className="metric-tile">
          <div className="label">Best attempt</div>
          <div className="value">{best[metric.key]}</div>
        </div>
        <div className="metric-tile">
          <div className="label">Latest attempt</div>
          <div className="value">{latest[metric.key]}</div>
        </div>
      </div>
    </div>
  );
}

export default function Progress() {
  const [attempts, setAttempts] = useState<AttemptSummaryOut[] | null>(null);
  const [hasUser, setHasUser] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Deferred to a microtask (not called synchronously in the effect body)
    // so this reads as "react to the async result", not a direct setState.
    const userId = getStoredUserId();
    Promise.resolve().then(async () => {
      setHasUser(userId !== null);
      if (!userId) {
        setAttempts([]);
        return;
      }
      try {
        setAttempts(await getAttempts(userId));
      } catch (err) {
        setError(err instanceof Error ? err.message : "couldn't load progress");
      }
    });
  }, []);

  return (
    <div className="container stack">
      <h1>Progress</h1>
      <p style={{ color: "var(--muted)" }}>
        Self-relative only — first attempt vs. best attempt vs. latest attempt. No ranking
        against other users.
      </p>

      {error && <p className="error-banner">{error}</p>}

      {hasUser === false && (
        <div className="card stack">
          <p>Complete onboarding to start tracking progress across attempts.</p>
          <Link href="/onboarding" className="btn btn-primary" style={{ width: "fit-content" }}>
            Get started
          </Link>
        </div>
      )}

      {hasUser === true && attempts !== null && attempts.length === 0 && (
        <div className="card stack">
          <p>No completed attempts yet.</p>
          <Link href="/practice" className="btn btn-primary" style={{ width: "fit-content" }}>
            Start a practice session
          </Link>
        </div>
      )}

      {attempts !== null && attempts.length > 0 && (
        <div className="stack">
          {METRICS.map((m) => (
            <TrendRow key={m.key} attempts={attempts} metric={m} />
          ))}

          <div className="card stack">
            <div className="pill">All attempts ({attempts.length})</div>
            {[...attempts].reverse().map((a) => (
              <div key={a.session_id} className="feedback-item">
                <div className="criterion">
                  {new Date(a.created_at).toLocaleString()} · {a.scenario.replace(/_/g, " ")}
                  {a.parent_session_id ? " · retry" : ""}
                </div>
                <p>
                  {a.wpm_overall} wpm · {a.filler_rate_per_100_words} fillers/100w ·{" "}
                  {a.hedging_rate_per_100_words} hedges/100w · point-first {a.point_position_score}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
