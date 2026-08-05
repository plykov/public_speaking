"use client";

import { useState } from "react";
import { fetchExemplar, type ExemplarOut } from "@/lib/api";

export function ExemplarPanel({ sessionId }: { sessionId: string }) {
  const [exemplar, setExemplar] = useState<ExemplarOut | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleShow() {
    setLoading(true);
    setError(null);
    try {
      setExemplar(await fetchExemplar(sessionId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "couldn't generate a stronger version");
    } finally {
      setLoading(false);
    }
  }

  if (!exemplar) {
    return (
      <div className="card stack">
        <button className="btn" onClick={handleShow} disabled={loading}>
          {loading ? "Generating…" : "Show a stronger version"}
        </button>
        {error && <p className="error-banner">{error}</p>}
      </div>
    );
  }

  return (
    <div className="card stack">
      <div className="pill">Stronger version</div>
      <p style={{ color: "var(--muted)", fontSize: "0.85rem" }}>
        Mechanically reordered/de-hedged from what you actually said — not an AI rewrite (see
        README §4.2 for why). A real exemplar model would compose more natural phrasing.
      </p>
      <div>
        <div className="label" style={{ color: "var(--muted)", fontSize: "0.8rem" }}>
          You said
        </div>
        <p>{exemplar.original_text}</p>
      </div>
      <div>
        <div className="label" style={{ color: "var(--muted)", fontSize: "0.8rem" }}>
          Stronger version
        </div>
        <p style={{ fontWeight: 600 }}>{exemplar.rewritten_text}</p>
      </div>
      <div className="stack">
        <div className="label" style={{ color: "var(--muted)", fontSize: "0.8rem" }}>
          What changed
        </div>
        {exemplar.explanation.map((line, i) => (
          <p key={i}>• {line}</p>
        ))}
      </div>
    </div>
  );
}
