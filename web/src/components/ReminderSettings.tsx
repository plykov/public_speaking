"use client";

import { useEffect, useState } from "react";
import { getReminder, upsertReminder } from "@/lib/api";

const DAYS = [
  { id: "mon", label: "Mon" },
  { id: "tue", label: "Tue" },
  { id: "wed", label: "Wed" },
  { id: "thu", label: "Thu" },
  { id: "fri", label: "Fri" },
  { id: "sat", label: "Sat" },
  { id: "sun", label: "Sun" },
];

export function ReminderSettings({ userId }: { userId: string }) {
  const [selectedDays, setSelectedDays] = useState<string[]>([]);
  const [timeOfDay, setTimeOfDay] = useState("09:00");
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getReminder(userId)
      .then((reminder) => {
        if (reminder) {
          setSelectedDays(reminder.days);
          setTimeOfDay(reminder.time_of_day);
        }
      })
      .catch(() => {
        // No reminder set yet — defaults stay.
      });
  }, [userId]);

  function toggleDay(day: string) {
    setSelectedDays((prev) =>
      prev.includes(day) ? prev.filter((d) => d !== day) : [...prev, day],
    );
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      await upsertReminder(userId, selectedDays, timeOfDay);
      setSavedAt(Date.now());
    } catch (err) {
      setError(err instanceof Error ? err.message : "couldn't save reminder");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="card stack">
      <div className="pill">Reminder window</div>
      <p style={{ color: "var(--muted)" }}>
        Pick the days and time you&apos;d want a nudge before practicing. This only stores
        the preference — sending the actual reminder needs a notification channel this
        environment doesn&apos;t have yet.
      </p>
      <div className="row">
        {DAYS.map((d) => (
          <button
            key={d.id}
            className="btn"
            style={
              selectedDays.includes(d.id)
                ? { borderColor: "var(--accent)", fontWeight: 600 }
                : undefined
            }
            onClick={() => toggleDay(d.id)}
          >
            {d.label}
          </button>
        ))}
      </div>
      <label htmlFor="reminder-time">Time of day</label>
      <input
        id="reminder-time"
        type="time"
        className="btn"
        style={{ width: "fit-content", cursor: "text" }}
        value={timeOfDay}
        onChange={(e) => setTimeOfDay(e.target.value)}
      />
      {error && <p className="error-banner">{error}</p>}
      <button
        className="btn btn-primary"
        onClick={handleSave}
        disabled={saving || selectedDays.length === 0}
        style={{ width: "fit-content" }}
      >
        {saving ? "Saving…" : "Save reminder"}
      </button>
      {savedAt !== null && <p style={{ color: "var(--good)", fontSize: "0.85rem" }}>Saved.</p>}
    </div>
  );
}
