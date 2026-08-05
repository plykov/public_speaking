"use client";

import { useEffect, useState } from "react";
import {
  createRoleplaySession,
  fetchRoleplayPersonas,
  submitRoleplayTurn,
  type RoleplayPersonaOut,
  type RoleplaySessionOut,
  type RoleplayTurnOut,
} from "@/lib/api";
import { DevTranscriptPicker } from "@/components/DevTranscriptPicker";
import { SAMPLE_TRANSCRIPTS } from "@/lib/sampleTranscripts";
import { speak, ttsSupported } from "@/lib/tts";
import { getStoredUserId } from "@/lib/localUser";

export default function RoleplayPage() {
  const [personas, setPersonas] = useState<RoleplayPersonaOut[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [session, setSession] = useState<RoleplaySessionOut | null>(null);
  const [transcriptId, setTranscriptId] = useState(SAMPLE_TRANSCRIPTS[0].id);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [speechSupported, setSpeechSupported] = useState(true); // resolved client-side only, see effect below
  const spokenTurnIndexes = useState(() => new Set<number>())[0];

  useEffect(() => {
    fetchRoleplayPersonas()
      .then(setPersonas)
      .catch(() => setPersonas([]));
    Promise.resolve().then(() => setSpeechSupported(ttsSupported()));
  }, []);

  useEffect(() => {
    if (!session) return;
    for (const turn of session.turns) {
      if (turn.speaker === "persona" && !spokenTurnIndexes.has(turn.turn_index)) {
        spokenTurnIndexes.add(turn.turn_index);
        speak(turn.text);
      }
    }
  }, [session, spokenTurnIndexes]);

  function toggleSelected(personaId: string) {
    setSelectedIds((prev) =>
      prev.includes(personaId) ? prev.filter((id) => id !== personaId) : [...prev, personaId],
    );
  }

  function personaName(personaId: string | null): string {
    if (!personaId) return "You";
    return personas.find((p) => p.id === personaId)?.name ?? personaId;
  }

  async function handleStart() {
    if (selectedIds.length === 0) return;
    setError(null);
    try {
      const created = await createRoleplaySession(selectedIds, getStoredUserId() ?? undefined);
      setSession(created);
    } catch (err) {
      setError(err instanceof Error ? err.message : "couldn't start the roleplay");
    }
  }

  async function handleRespond() {
    if (!session) return;
    setSubmitting(true);
    setError(null);
    try {
      const sample = SAMPLE_TRANSCRIPTS.find((t) => t.id === transcriptId) ?? SAMPLE_TRANSCRIPTS[0];
      const result = await submitRoleplayTurn(session.id, sample.words);
      setSession((prev) =>
        prev
          ? { ...prev, status: result.session_status, turns: [...prev.turns, ...result.new_turns] }
          : prev,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "couldn't submit your response");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="container stack">
      <h1>Roleplay</h1>
      <p style={{ color: "var(--muted)" }}>
        Turn-based voice practice against a persona. The persona&apos;s lines are spoken aloud by
        your browser&apos;s built-in text-to-speech
        {!speechSupported && " (not supported in this browser — the text still appears below)"}.
      </p>

      {error && <p className="error-banner">{error}</p>}

      {!session && (
        <div className="card stack">
          <p>
            Choose one persona, or select more than one for a multi-persona panel — they take
            turns responding.
          </p>
          {personas.map((p) => (
            <div key={p.id} className="stack" style={{ gap: 4 }}>
              <button
                className="btn"
                style={
                  selectedIds.includes(p.id)
                    ? { borderColor: "var(--accent)", fontWeight: 600 }
                    : undefined
                }
                onClick={() => toggleSelected(p.id)}
              >
                {p.name} — {p.role}
              </button>
              <p style={{ color: "var(--muted)", fontSize: "0.85rem" }}>{p.description}</p>
            </div>
          ))}
          <button className="btn btn-primary" onClick={handleStart} disabled={selectedIds.length === 0}>
            {selectedIds.length > 1
              ? `Start panel (${selectedIds.length} personas)`
              : "Start roleplay"}
          </button>
        </div>
      )}

      {session && (
        <div className="stack">
          <div className="card stack">
            <div className="pill">
              {session.status === "completed" ? "Conversation complete" : "In progress"}
            </div>
            {session.turns.map((turn: RoleplayTurnOut) => (
              <div key={turn.turn_index} className="feedback-item">
                <div className="criterion">{personaName(turn.persona_id)}</div>
                <p>{turn.text}</p>
              </div>
            ))}
          </div>

          {session.status === "active" && (
            <div className="stack">
              <DevTranscriptPicker selectedId={transcriptId} onSelect={setTranscriptId} />
              <button className="btn btn-primary" onClick={handleRespond} disabled={submitting}>
                {submitting ? "Sending…" : "Respond"}
              </button>
            </div>
          )}

          {session.status === "completed" && (
            <button
              className="btn"
              onClick={() => {
                setSession(null);
                setSelectedIds([]);
              }}
            >
              Start a new roleplay
            </button>
          )}
        </div>
      )}
    </div>
  );
}
