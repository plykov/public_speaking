"use client";

import { useEffect, useState } from "react";
import {
  createShareLink,
  listShareLinks,
  revokeShareLink,
  type ShareLinkOut,
} from "@/lib/api";

function shareUrl(token: string): string {
  const origin = typeof window !== "undefined" ? window.location.origin : "";
  return `${origin}/share/${token}`;
}

export function ShareLinkSettings({ userId }: { userId: string }) {
  const [links, setLinks] = useState<ShareLinkOut[] | null>(null);
  const [label, setLabel] = useState("");
  const [canViewTranscripts, setCanViewTranscripts] = useState(false);
  const [canViewFeedback, setCanViewFeedback] = useState(false);
  const [creating, setCreating] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listShareLinks(userId)
      .then(setLinks)
      .catch(() => setLinks([]));
  }, [userId]);

  async function handleCreate() {
    setCreating(true);
    setError(null);
    try {
      const link = await createShareLink(userId, {
        label: label.trim() || undefined,
        canViewProgress: true,
        canViewTranscripts,
        canViewFeedback,
      });
      setLinks((prev) => [link, ...(prev ?? [])]);
      setLabel("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "couldn't create share link");
    } finally {
      setCreating(false);
    }
  }

  async function handleRevoke(shareId: string) {
    setLinks((prev) => prev?.map((l) => (l.id === shareId ? { ...l, revoked: true } : l)) ?? null);
    try {
      await revokeShareLink(userId, shareId);
    } catch {
      // optimistic update stays even if the DELETE fails silently
    }
  }

  async function handleCopy(link: ShareLinkOut) {
    try {
      await navigator.clipboard.writeText(shareUrl(link.token));
      setCopiedId(link.id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch {
      // clipboard API unavailable — the URL is still visible in the row
    }
  }

  return (
    <div className="card stack">
      <div className="pill">Coach / manager share links</div>
      <p style={{ color: "var(--muted)" }}>
        Share a read-only, no-login link with a coach or manager. Raw recordings are never
        shared, at any setting — only whatever you turn on below.
      </p>

      <input
        className="btn"
        style={{ textAlign: "left", cursor: "text" }}
        placeholder="Label (optional, e.g. For Priya)"
        value={label}
        onChange={(e) => setLabel(e.target.value)}
      />
      <label className="row" style={{ alignItems: "center", gap: 6 }}>
        <input
          type="checkbox"
          checked={canViewTranscripts}
          onChange={(e) => setCanViewTranscripts(e.target.checked)}
        />
        Include transcripts
      </label>
      <label className="row" style={{ alignItems: "center", gap: 6 }}>
        <input
          type="checkbox"
          checked={canViewFeedback}
          onChange={(e) => setCanViewFeedback(e.target.checked)}
        />
        Include coaching feedback
      </label>
      <p style={{ color: "var(--muted)", fontSize: "0.85rem" }}>
        Progress trends (words/min, filler rate, etc.) are always included.
      </p>
      <button className="btn btn-primary" onClick={handleCreate} disabled={creating}>
        {creating ? "Creating…" : "Create share link"}
      </button>

      {error && <p className="error-banner">{error}</p>}

      {links && links.length > 0 && (
        <div className="stack" style={{ marginTop: 8 }}>
          {links.map((link) => (
            <div key={link.id} className="row" style={{ alignItems: "center", gap: 8 }}>
              <span className="pill" style={link.revoked ? { color: "var(--muted)" } : undefined}>
                {link.label || "Untitled"}
                {link.revoked ? " (revoked)" : ""}
              </span>
              {!link.revoked && (
                <>
                  <button className="btn" onClick={() => handleCopy(link)}>
                    {copiedId === link.id ? "Copied!" : "Copy link"}
                  </button>
                  <button className="btn btn-danger" onClick={() => handleRevoke(link.id)}>
                    Revoke
                  </button>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
