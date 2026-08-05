"use client";

import { useRef, useState } from "react";
import { slideThumbnailUrl, uploadSlideDeck, type SlideDeckOut } from "@/lib/api";

export function SlideDeckPanel({
  sessionId,
  deck,
  onUploaded,
}: {
  sessionId: string;
  deck: SlideDeckOut | null;
  onUploaded: (deck: SlideDeckOut) => void;
}) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleFile(file: File) {
    setUploading(true);
    setError(null);
    try {
      const uploaded = await uploadSlideDeck(sessionId, file);
      onUploaded(uploaded);
    } catch (err) {
      setError(err instanceof Error ? err.message : "couldn't upload that PDF");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="card stack">
      <p>
        Slides <span style={{ color: "var(--muted)" }}>(optional — PDF)</span>
      </p>
      <p style={{ color: "var(--muted)", fontSize: "0.85rem" }}>
        Upload your deck and mark slide changes while you record — feedback will show which
        slide you were on.
      </p>
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf"
        style={{ display: "none" }}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleFile(file);
        }}
      />
      <button className="btn" onClick={() => inputRef.current?.click()} disabled={uploading}>
        {uploading ? "Uploading…" : deck ? `Replace deck (${deck.filename})` : "Upload PDF"}
      </button>
      {error && <p className="error-banner">{error}</p>}
      {deck && (
        <div className="row" style={{ flexWrap: "wrap" }}>
          {deck.thumbnail_urls.map((url, i) => (
            // eslint-disable-next-line @next/next/no-img-element -- backend-served thumbnail, not a Next static asset
            <img
              key={i}
              src={slideThumbnailUrl(url)}
              alt={`Slide ${i + 1}`}
              style={{ width: 96, border: "1px solid var(--border)", borderRadius: 4 }}
            />
          ))}
        </div>
      )}
    </div>
  );
}
