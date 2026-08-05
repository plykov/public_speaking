"use client";

import { useState } from "react";
import { LevelMeter } from "@/components/LevelMeter";
import { useAudioRecorder } from "@/lib/useAudioRecorder";

function formatMs(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function RecorderPanel({
  prompt,
  onComplete,
}: {
  prompt: string;
  onComplete: (audioUrl: string) => void;
}) {
  const { status, level, elapsedMs, audioUrl, error, requestMic, start, stop, reset } =
    useAudioRecorder();
  const [countdown, setCountdown] = useState<number | null>(null);

  function runCountdown(n: number) {
    setCountdown(n);
    if (n === 0) {
      setTimeout(() => {
        setCountdown(null);
        start();
      }, 500);
      return;
    }
    setTimeout(() => runCountdown(n - 1), 700);
  }

  if (status === "idle") {
    return (
      <div className="card stack">
        <p>Recording is at most two clicks from any screen — let&apos;s check your mic.</p>
        <button className="btn btn-primary" onClick={requestMic}>
          Enable microphone
        </button>
      </div>
    );
  }

  if (status === "requesting") {
    return <div className="card">Requesting microphone access…</div>;
  }

  if (status === "error") {
    return (
      <div className="card stack">
        <p className="error-banner">{error ?? "Microphone permission was denied."}</p>
        <button className="btn" onClick={requestMic}>
          Try again
        </button>
      </div>
    );
  }

  return (
    <div className="card stack">
      <div>
        <div className="pill">Prompt</div>
        <p style={{ marginTop: 6 }}>{prompt}</p>
      </div>

      {status === "ready" && (
        <div className="stack">
          <LevelMeter level={level} />
          <p style={{ color: "var(--muted)", fontSize: "0.85rem" }}>
            Speak normally to check your level, then start when ready.
          </p>
          {countdown === null ? (
            <button className="btn btn-primary" onClick={() => runCountdown(3)}>
              Start recording
            </button>
          ) : (
            <div className="timer" aria-live="polite">
              {countdown === 0 ? "Go" : countdown}
            </div>
          )}
        </div>
      )}

      {status === "recording" && (
        <div className="stack">
          <div className="recording-indicator" role="status" aria-live="assertive">
            <span className="recording-dot" />
            Recording
          </div>
          <LevelMeter level={level} />
          <div className="timer" aria-live="polite">
            {formatMs(elapsedMs)}
          </div>
          <button className="btn btn-danger" onClick={stop}>
            Stop
          </button>
        </div>
      )}

      {status === "stopped" && audioUrl && (
        <div className="stack">
          <audio controls src={audioUrl} style={{ width: "100%" }} />
          <div className="row">
            <button className="btn" onClick={reset}>
              Restart
            </button>
            <button className="btn btn-primary" onClick={() => onComplete(audioUrl)}>
              Use this take
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
