"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { CONTEXTS } from "@/lib/contexts";
import { createUser, upsertL1Profile } from "@/lib/api";
import { setStoredUserId } from "@/lib/localUser";

const CONFIDENCE_LEVELS = [
  { id: "building", label: "Still building it" },
  { id: "comfortable", label: "Comfortable, but not automatic" },
  { id: "fluent", label: "Fluent" },
];

export default function Onboarding() {
  const router = useRouter();
  const [contextId, setContextId] = useState(CONTEXTS[0].id);
  const [firstLanguage, setFirstLanguage] = useState("");
  const [confidence, setConfidence] = useState(CONFIDENCE_LEVELS[1].id);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    setSubmitting(true);
    setError(null);
    try {
      const user = await createUser();
      if (firstLanguage.trim()) {
        await upsertL1Profile(user.id, firstLanguage.trim(), confidence);
      }
      setStoredUserId(user.id);
      router.push(`/practice?context=${contextId}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "couldn't start onboarding");
      setSubmitting(false);
    }
  }

  return (
    <div className="container stack">
      <h1>Let&apos;s set up your practice</h1>
      <p style={{ color: "var(--muted)" }}>
        This isn&apos;t about your accent — it&apos;s about being heard. Two quick questions,
        then a 90-second baseline recording. First useful feedback in under 5 minutes.
      </p>

      <div className="card stack">
        <p>What are you preparing for?</p>
        <div className="row">
          {CONTEXTS.map((c) => (
            <button
              key={c.id}
              className="btn"
              style={c.id === contextId ? { borderColor: "var(--accent)", fontWeight: 600 } : undefined}
              onClick={() => setContextId(c.id)}
            >
              {c.label}
            </button>
          ))}
        </div>
      </div>

      <div className="card stack">
        <label htmlFor="first-language">
          First language <span style={{ color: "var(--muted)" }}>(optional)</span>
        </label>
        <input
          id="first-language"
          className="btn"
          style={{ textAlign: "left", cursor: "text" }}
          placeholder="e.g. Russian, Dutch, Mandarin"
          value={firstLanguage}
          onChange={(e) => setFirstLanguage(e.target.value)}
        />

        <p>How confident do you feel speaking English in meetings?</p>
        <div className="row">
          {CONFIDENCE_LEVELS.map((c) => (
            <button
              key={c.id}
              className="btn"
              style={c.id === confidence ? { borderColor: "var(--accent)", fontWeight: 600 } : undefined}
              onClick={() => setConfidence(c.id)}
            >
              {c.label}
            </button>
          ))}
        </div>
        <p style={{ color: "var(--muted)", fontSize: "0.85rem" }}>
          This only shapes onboarding copy — it&apos;s never used to score your recordings.
        </p>
      </div>

      {error && <p className="error-banner">{error}</p>}

      <button className="btn btn-primary" onClick={handleSubmit} disabled={submitting}>
        {submitting ? "Setting up…" : "Start baseline recording"}
      </button>
    </div>
  );
}
