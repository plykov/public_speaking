"use client";

import { useEffect, useState } from "react";
import { getTranscript, updateTranscript, type AnalysisResultOut, type TranscriptWordOut } from "@/lib/api";

export function EditableTranscript({
  sessionId,
  onReanalyzed,
}: {
  sessionId: string;
  onReanalyzed: (result: AnalysisResultOut) => void;
}) {
  const [original, setOriginal] = useState<TranscriptWordOut[] | null>(null);
  const [words, setWords] = useState<TranscriptWordOut[] | null>(null);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getTranscript(sessionId)
      .then((fetched) => {
        setOriginal(fetched);
        setWords(fetched);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "couldn't load transcript"));
  }, [sessionId]);

  if (error) return <p className="error-banner">{error}</p>;
  if (!words) return null;

  const hasChanges =
    original !== null && words.some((w, i) => w.text !== original[i].text);

  function commitEdit(index: number) {
    setWords((prev) =>
      prev ? prev.map((w, i) => (i === index ? { ...w, text: draft } : w)) : prev,
    );
    setEditingIndex(null);
  }

  async function handleSave() {
    if (!words) return;
    setSaving(true);
    setError(null);
    try {
      const result = await updateTranscript(
        sessionId,
        words.map((w) => w.text),
      );
      setOriginal(words);
      onReanalyzed(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "re-analysis failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="card stack">
      <div className="pill">Transcript — click a word to correct it</div>
      <p>
        {words.map((w, i) => (
          <span key={w.seq_index}>
            {editingIndex === i ? (
              <input
                autoFocus
                className="btn"
                style={{ padding: "2px 6px", width: `${Math.max(draft.length, 3)}ch` }}
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onBlur={() => commitEdit(i)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") commitEdit(i);
                  if (e.key === "Escape") setEditingIndex(null);
                }}
              />
            ) : (
              <button
                className="evidence-link"
                style={{
                  color: w.text !== original?.[i]?.text ? "var(--accent)" : "inherit",
                  textDecoration: "none",
                  fontWeight: w.text !== original?.[i]?.text ? 600 : 400,
                }}
                onClick={() => {
                  setDraft(w.text);
                  setEditingIndex(i);
                }}
              >
                {w.text}
              </button>
            )}{" "}
          </span>
        ))}
      </p>
      <button className="btn btn-primary" onClick={handleSave} disabled={!hasChanges || saving}>
        {saving ? "Re-analyzing…" : "Save corrections & re-analyze"}
      </button>
    </div>
  );
}
