"use client";

/**
 * §4.2 roleplay's "TTS" leg: the browser's own SpeechSynthesis API.
 * Real, standards-based, no vendor account — same idea as Web Push using
 * the browser's own push service instead of a paid vendor.
 */
export function ttsSupported(): boolean {
  return typeof window !== "undefined" && "speechSynthesis" in window;
}

export function speak(text: string): void {
  if (!ttsSupported()) return;
  window.speechSynthesis.cancel(); // don't let turns overlap/queue indefinitely
  window.speechSynthesis.speak(new SpeechSynthesisUtterance(text));
}
