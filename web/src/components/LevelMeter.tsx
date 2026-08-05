"use client";

export function LevelMeter({ level }: { level: number }) {
  return (
    <div className="level-meter-track" role="meter" aria-valuenow={Math.round(level * 100)} aria-valuemin={0} aria-valuemax={100} aria-label="Microphone level">
      <div className="level-meter-fill" style={{ width: `${Math.round(level * 100)}%` }} />
    </div>
  );
}
