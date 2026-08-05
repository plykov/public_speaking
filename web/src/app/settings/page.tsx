"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { deleteAccount, exportUserData } from "@/lib/api";
import { clearStoredUserId, getStoredUserId } from "@/lib/localUser";
import { ReminderSettings } from "@/components/ReminderSettings";

export default function Settings() {
  const router = useRouter();
  const [userId, setUserId] = useState<string | null | undefined>(undefined);
  const [exporting, setExporting] = useState(false);
  const [deleteArmed, setDeleteArmed] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.resolve().then(() => setUserId(getStoredUserId()));
  }, []);

  async function handleExport() {
    if (!userId) return;
    setExporting(true);
    setError(null);
    try {
      const data = await exportUserData(userId);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `cadence-export-${userId}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "export failed");
    } finally {
      setExporting(false);
    }
  }

  async function handleDelete() {
    if (!userId) return;
    if (!deleteArmed) {
      setDeleteArmed(true);
      return;
    }
    setDeleting(true);
    setError(null);
    try {
      await deleteAccount(userId);
      clearStoredUserId();
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "account delete failed");
      setDeleting(false);
    }
  }

  if (userId === undefined) {
    return <div className="container">Loading…</div>;
  }

  if (userId === null) {
    return (
      <div className="container stack">
        <h1>Settings</h1>
        <div className="card stack">
          <p>No account on this device yet.</p>
          <Link href="/onboarding" className="btn btn-primary" style={{ width: "fit-content" }}>
            Get started
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="container stack">
      <h1>Settings</h1>

      {error && <p className="error-banner">{error}</p>}

      <div className="card stack">
        <div className="pill">Privacy</div>
        <p style={{ color: "var(--muted)" }}>
          We never train on your voice, at any tier. Raw recordings auto-delete after 30
          days; your derived metrics and feedback history stay so your progress is never lost.
        </p>
      </div>

      <ReminderSettings userId={userId} />

      <div className="card stack">
        <div className="pill">Export your data</div>
        <p>Download every session&apos;s transcript, metrics, and feedback as JSON.</p>
        <button className="btn" onClick={handleExport} disabled={exporting}>
          {exporting ? "Preparing export…" : "Export my data"}
        </button>
      </div>

      <div className="card stack">
        <div className="pill" style={{ borderColor: "var(--danger)", color: "var(--danger)" }}>
          Delete account
        </div>
        <p>
          Permanently deletes your account, all recordings, transcripts, and feedback
          history. This cannot be undone.
        </p>
        <button className="btn btn-danger" onClick={handleDelete} disabled={deleting}>
          {deleting
            ? "Deleting…"
            : deleteArmed
              ? "Click again to confirm — this cannot be undone"
              : "Delete my account"}
        </button>
      </div>
    </div>
  );
}
