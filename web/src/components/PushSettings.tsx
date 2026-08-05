"use client";

import { useEffect, useState } from "react";
import {
  getExistingSubscription,
  pushSupported,
  sendTestPush,
  subscribeToPush,
  unsubscribeFromPush,
} from "@/lib/push";

export function PushSettings({ userId }: { userId: string }) {
  const [supported, setSupported] = useState<boolean | null>(null);
  const [subscribed, setSubscribed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.resolve().then(async () => {
      const isSupported = pushSupported();
      setSupported(isSupported);
      if (!isSupported) return;
      try {
        const existing = await getExistingSubscription();
        setSubscribed(existing !== null);
      } catch {
        // Service worker not registered yet — treat as not subscribed.
      }
    });
  }, []);

  async function handleEnable() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await subscribeToPush(userId);
      setSubscribed(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "couldn't enable push notifications");
    } finally {
      setBusy(false);
    }
  }

  async function handleDisable() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await unsubscribeFromPush(userId);
      setSubscribed(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "couldn't disable push notifications");
    } finally {
      setBusy(false);
    }
  }

  async function handleTest() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await sendTestPush(userId);
      setMessage(
        result.sent > 0
          ? "Test notification sent — check your system notifications."
          : "No notification could be delivered (subscription may have expired).",
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "couldn't send test notification");
    } finally {
      setBusy(false);
    }
  }

  if (supported === false) {
    return (
      <div className="card stack">
        <div className="pill">Push notifications</div>
        <p style={{ color: "var(--muted)" }}>
          Not supported in this browser.
        </p>
      </div>
    );
  }

  return (
    <div className="card stack">
      <div className="pill">Push notifications</div>
      <p style={{ color: "var(--muted)" }}>
        Real Web Push — no scheduler exists yet to send these automatically before a
        meeting (see the reminder window above), but delivery itself works today.
      </p>
      {error && <p className="error-banner">{error}</p>}
      {message && <p style={{ color: "var(--good)", fontSize: "0.85rem" }}>{message}</p>}
      <div className="row">
        {!subscribed ? (
          <button className="btn btn-primary" onClick={handleEnable} disabled={busy || supported === null}>
            {busy ? "Enabling…" : "Enable push notifications"}
          </button>
        ) : (
          <>
            <button className="btn" onClick={handleTest} disabled={busy}>
              {busy ? "Sending…" : "Send test notification"}
            </button>
            <button className="btn" onClick={handleDisable} disabled={busy}>
              Disable
            </button>
          </>
        )}
      </div>
    </div>
  );
}
