"use client";

import { SAMPLE_TRANSCRIPTS } from "@/lib/sampleTranscripts";

export function DevTranscriptPicker({
  selectedId,
  onSelect,
}: {
  selectedId: string;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="dev-banner stack">
      <div>
        <strong>Dev mode:</strong> a live speech-to-text vendor isn&apos;t connected yet
        (see <code>api/pipeline/stt.py</code>). Your recording above plays back for real,
        locally — but analysis below runs on one of these scripted sample transcripts
        instead, uploaded to the backend through the same resumable-upload path a real
        recording would use. Evidence timestamps in the scorecard refer to the sample
        transcript, not your real recording, so they aren&apos;t wired to seek playback here.
      </div>
      <div className="row">
        {SAMPLE_TRANSCRIPTS.map((t) => (
          <button
            key={t.id}
            className="btn"
            style={
              t.id === selectedId
                ? { borderColor: "var(--accent)", fontWeight: 600 }
                : undefined
            }
            onClick={() => onSelect(t.id)}
            title={t.description}
          >
            {t.label}
          </button>
        ))}
      </div>
    </div>
  );
}
