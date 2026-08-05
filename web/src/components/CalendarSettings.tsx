"use client";

import { useEffect, useState } from "react";
import { connectCalendar, disconnectCalendar, getCalendarConnection } from "@/lib/api";

export function CalendarSettings({ userId }: { userId: string }) {
  const [connected, setConnected] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getCalendarConnection(userId)
      .then((c) => setConnected(c.connected))
      .catch(() => setConnected(false));
  }, [userId]);

  async function handleConnect() {
    setBusy(true);
    setError(null);
    try {
      await connectCalendar(userId);
      setConnected(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "couldn't connect a calendar");
    } finally {
      setBusy(false);
    }
  }

  async function handleDisconnect() {
    setBusy(true);
    setError(null);
    try {
      await disconnectCalendar(userId);
      setConnected(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "couldn't disconnect");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card stack">
      <div className="pill">Calendar (§4.2)</div>
      <p style={{ color: "var(--muted)" }}>
        Connect a calendar to get a practice prompt before your next meeting — &quot;Standup in
        40 minutes — one interjection drill?&quot;
      </p>
      <p style={{ color: "var(--muted)", fontSize: "0.85rem" }}>
        No real Google/Microsoft OAuth in this environment — connecting here simulates a
        successful connection with a couple of sample upcoming meetings, so the pre-meeting
        prompt itself is fully real and testable.
      </p>
      {error && <p className="error-banner">{error}</p>}
      {connected === null ? (
        <p>Loading…</p>
      ) : connected ? (
        <button className="btn" onClick={handleDisconnect} disabled={busy}>
          {busy ? "Disconnecting…" : "Disconnect calendar"}
        </button>
      ) : (
        <button className="btn btn-primary" onClick={handleConnect} disabled={busy}>
          {busy ? "Connecting…" : "Connect calendar"}
        </button>
      )}
    </div>
  );
}
