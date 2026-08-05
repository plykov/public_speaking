"use client";

import type { AnalysisResultOut } from "@/lib/api";

interface MetricsSummary {
  wpm_overall?: number;
  filler_rate_per_100_words?: number;
  hedging_rate_per_100_words?: number;
  point_position?: { found: boolean; sentence_index: number | null; score: number };
  word_count?: number;
}

function summaryOf(result: AnalysisResultOut): MetricsSummary {
  return result.metrics_summary as MetricsSummary;
}

function deriveStrength(summary: MetricsSummary): string {
  if (summary.point_position?.found && summary.point_position.sentence_index === 0) {
    return "Your recommendation led the response — that's exactly the structure to keep.";
  }
  if ((summary.filler_rate_per_100_words ?? 0) < 3) {
    return "Very few fillers — your delivery stayed clean under pressure.";
  }
  if ((summary.hedging_rate_per_100_words ?? 0) === 0) {
    return "No hedging detected — you stated things directly.";
  }
  return "You completed a full attempt end to end — that's the rep that matters.";
}

function MetricTile({
  label,
  value,
  previous,
  higherIsBetter,
}: {
  label: string;
  value: number;
  previous?: number;
  higherIsBetter: boolean;
}) {
  const delta = previous !== undefined ? value - previous : undefined;
  const improved =
    delta !== undefined && (higherIsBetter ? delta > 0 : delta < 0) && delta !== 0;
  const worsened =
    delta !== undefined && (higherIsBetter ? delta < 0 : delta > 0) && delta !== 0;
  return (
    <div className="metric-tile">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
      {delta !== undefined && delta !== 0 && (
        <div className={improved ? "delta-up" : worsened ? "delta-down" : undefined}>
          {delta > 0 ? "+" : ""}
          {Math.round(delta * 100) / 100} vs first attempt
        </div>
      )}
    </div>
  );
}

export function Scorecard({
  result,
  previous,
  onSeek,
  onRate,
}: {
  result: AnalysisResultOut;
  previous?: AnalysisResultOut;
  onSeek?: (ms: number) => void;
  onRate?: (feedbackItemId: string, useful: boolean) => void;
}) {
  const summary = summaryOf(result);
  const prevSummary = previous ? summaryOf(previous) : undefined;

  return (
    <div className="stack">
      <div className="card stack">
        <div className="pill" style={{ borderColor: "var(--good)", color: "var(--good)" }}>
          Strength
        </div>
        <p>{deriveStrength(summary)}</p>
      </div>

      <div className="metric-grid">
        <MetricTile
          label="Words / min"
          value={summary.wpm_overall ?? 0}
          previous={prevSummary?.wpm_overall}
          higherIsBetter={false}
        />
        <MetricTile
          label="Fillers / 100 words"
          value={summary.filler_rate_per_100_words ?? 0}
          previous={prevSummary?.filler_rate_per_100_words}
          higherIsBetter={false}
        />
        <MetricTile
          label="Hedging / 100 words"
          value={summary.hedging_rate_per_100_words ?? 0}
          previous={prevSummary?.hedging_rate_per_100_words}
          higherIsBetter={false}
        />
        <MetricTile
          label="Point-first score"
          value={summary.point_position?.score ?? 0}
          previous={prevSummary?.point_position?.score}
          higherIsBetter={true}
        />
      </div>

      <div className="card stack">
        <div className="pill">Top {result.feedback_items.length} priorities</div>
        {result.feedback_items.length === 0 && (
          <p style={{ color: "var(--muted)" }}>
            No specific issues surfaced from this attempt.
          </p>
        )}
        {result.feedback_items.map((item) => (
          <div className="feedback-item" key={item.id}>
            <div className="criterion">{item.criterion.replace(/_/g, " ")}</div>
            <p>
              <strong>{item.observation}</strong> {item.rationale}
            </p>
            <p>→ {item.repair}</p>
            <p className="evidence">
              &ldquo;{item.evidence_text}&rdquo;{" "}
              {onSeek && (
                <button
                  className="evidence-link"
                  onClick={() => onSeek(item.evidence_start_ms)}
                >
                  jump to moment
                </button>
              )}
            </p>
            {onRate && (
              <div className="row" style={{ marginTop: 4 }}>
                <button
                  className="btn"
                  style={
                    item.user_rating === true
                      ? { borderColor: "var(--good)", color: "var(--good)" }
                      : undefined
                  }
                  onClick={() => onRate(item.id, true)}
                  aria-label="This feedback was useful"
                >
                  Useful
                </button>
                <button
                  className="btn"
                  style={
                    item.user_rating === false
                      ? { borderColor: "var(--danger)", color: "var(--danger)" }
                      : undefined
                  }
                  onClick={() => onRate(item.id, false)}
                  aria-label="This feedback was not useful"
                >
                  Not useful
                </button>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="card stack">
        <div className="pill">Next drill · {result.drill.duration_minutes} min</div>
        <h3>{result.drill.title}</h3>
        <p>{result.drill.prompt}</p>
      </div>
    </div>
  );
}
