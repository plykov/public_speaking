"use client";

import { useEffect, useState } from "react";
import {
  importMeetingRecording,
  listMeetingImports,
  listMeetingRecordings,
  type AnalysisResultOut,
  type ConsentedImportOut,
  type MeetingRecordingOut,
} from "@/lib/api";
import { getStoredUserId } from "@/lib/localUser";
import { Scorecard } from "@/components/Scorecard";

export default function MeetingImportPage() {
  const [userId, setUserId] = useState<string | null | undefined>(undefined);
  const [recordings, setRecordings] = useState<MeetingRecordingOut[]>([]);
  const [imports, setImports] = useState<ConsentedImportOut[]>([]);
  const [importingId, setImportingId] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResultOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.resolve().then(() => setUserId(getStoredUserId()));
  }, []);

  useEffect(() => {
    if (!userId) return;
    refresh(userId);
  }, [userId]);

  async function refresh(uid: string) {
    const [fetchedRecordings, fetchedImports] = await Promise.all([
      listMeetingRecordings(uid),
      listMeetingImports(uid),
    ]);
    setRecordings(fetchedRecordings);
    setImports(fetchedImports);
  }

  async function handleImport(recordingId: string) {
    if (!userId) return;
    setError(null);
    setImportingId(recordingId);
    setResult(null);
    try {
      const analyzed = await importMeetingRecording(recordingId, userId);
      setResult(analyzed);
      await refresh(userId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed");
    } finally {
      setImportingId(null);
    }
  }

  if (userId === undefined) return null;

  if (!userId) {
    return (
      <div className="container stack">
        <h1>Meeting import</h1>
        <p style={{ color: "var(--muted)" }}>
          Create a profile first from the home page, then come back here.
        </p>
      </div>
    );
  }

  return (
    <div className="container stack">
      <h1>Meeting import</h1>
      <p style={{ color: "var(--muted)" }}>
        Analyze a real meeting you already recorded on Zoom, Teams, or Google Meet — same
        scoring pipeline as a live practice attempt. This sandbox has no connected Zoom/Teams/
        Meet account, so the recordings below are a synthetic mock catalog standing in for a
        real cloud-recording API; the two meetings shown are always in the past, and nothing
        here can join a live meeting or start a recording — see the README for details.
      </p>

      {error && <div className="error-banner">{error}</div>}

      <div className="card stack">
        <h2>Available recordings</h2>
        {recordings.length === 0 && <p style={{ color: "var(--muted)" }}>None found.</p>}
        {recordings.map((r) => (
          <div key={r.id} className="row" style={{ justifyContent: "space-between" }}>
            <div>
              <div>{r.title}</div>
              <div style={{ color: "var(--muted)", fontSize: "0.9em" }}>
                {r.platform} · {new Date(r.occurred_at).toLocaleString()}
              </div>
            </div>
            <button
              className="btn btn-primary"
              disabled={importingId === r.id}
              onClick={() => handleImport(r.id)}
            >
              {importingId === r.id ? "Importing…" : "Import & analyze"}
            </button>
          </div>
        ))}
      </div>

      {result && (
        <div className="stack">
          <h2>Analysis</h2>
          <Scorecard result={result} />
        </div>
      )}

      <div className="card stack">
        <h2>Past imports</h2>
        {imports.length === 0 && (
          <p style={{ color: "var(--muted)" }}>No recordings imported yet.</p>
        )}
        {imports.map((i) => (
          <div key={i.id} className="row" style={{ justifyContent: "space-between" }}>
            <div>{i.title}</div>
            <div style={{ color: "var(--muted)", fontSize: "0.9em" }}>
              {i.platform} · {new Date(i.consented_at).toLocaleString()}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
