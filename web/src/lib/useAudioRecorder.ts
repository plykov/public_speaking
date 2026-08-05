"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export type RecorderStatus = "idle" | "requesting" | "ready" | "recording" | "stopped" | "error";

/**
 * Mic capture + live level meter (§4.1 M2). Real getUserMedia/MediaRecorder,
 * no backend involved — recording and playback both happen entirely in the
 * browser. Chunked upload (for the resumable-upload requirement) is handled
 * separately by `uploadBlobChunked`, since what gets uploaded for analysis
 * is decoupled from what gets played back locally (see sampleTranscripts.ts
 * for why).
 */
export function useAudioRecorder() {
  const [status, setStatus] = useState<RecorderStatus>("idle");
  const [level, setLevel] = useState(0); // 0..1
  const [elapsedMs, setElapsedMs] = useState(0);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const streamRef = useRef<MediaStream | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const rafRef = useRef<number | null>(null);
  const timerRef = useRef<number | null>(null);
  const startedAtRef = useRef<number>(0);

  const stopLevelLoop = useCallback(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
  }, []);

  // Stored in a ref (not useCallback) so the rAF loop can call the latest
  // version of itself without a temporal-dead-zone self-reference. Assigned
  // in an effect, not during render, since refs aren't render inputs.
  const tickLevelRef = useRef<() => void>(() => {});
  useEffect(() => {
    tickLevelRef.current = () => {
      const analyser = analyserRef.current;
      if (!analyser) return;
      const data = new Uint8Array(analyser.frequencyBinCount);
      analyser.getByteTimeDomainData(data);
      let sumSquares = 0;
      for (const v of data) {
        const centered = (v - 128) / 128;
        sumSquares += centered * centered;
      }
      const rms = Math.sqrt(sumSquares / data.length);
      setLevel(Math.min(1, rms * 3));
      rafRef.current = requestAnimationFrame(() => tickLevelRef.current());
    };
  });

  const requestMic = useCallback(async () => {
    setStatus("requesting");
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const AudioCtx = window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const ctx = new AudioCtx();
      const source = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 512;
      source.connect(analyser);
      audioCtxRef.current = ctx;
      analyserRef.current = analyser;

      setStatus("ready");
      rafRef.current = requestAnimationFrame(() => tickLevelRef.current());
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "microphone permission denied");
    }
  }, []);

  const start = useCallback(() => {
    const stream = streamRef.current;
    if (!stream) return;
    chunksRef.current = [];
    setAudioUrl(null);
    setElapsedMs(0);

    const recorder = new MediaRecorder(stream);
    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };
    recorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: recorder.mimeType });
      setAudioUrl(URL.createObjectURL(blob));
    };
    recorder.start(1000); // 1s timeslice — local chunked recording that survives a drop
    recorderRef.current = recorder;
    startedAtRef.current = Date.now();
    setStatus("recording");

    timerRef.current = window.setInterval(() => {
      setElapsedMs(Date.now() - startedAtRef.current);
    }, 200);
  }, []);

  const stop = useCallback(() => {
    recorderRef.current?.stop();
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
    setStatus("stopped");
  }, []);

  const reset = useCallback(() => {
    chunksRef.current = [];
    setAudioUrl(null);
    setElapsedMs(0);
    setStatus(streamRef.current ? "ready" : "idle");
  }, []);

  useEffect(() => {
    return () => {
      stopLevelLoop();
      if (timerRef.current !== null) window.clearInterval(timerRef.current);
      streamRef.current?.getTracks().forEach((t) => t.stop());
      audioCtxRef.current?.close();
    };
  }, [stopLevelLoop]);

  return { status, level, elapsedMs, audioUrl, error, requestMic, start, stop, reset };
}
