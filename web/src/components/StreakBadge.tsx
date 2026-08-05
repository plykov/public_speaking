"use client";

import { useEffect, useState } from "react";
import { getStreak, type StreakOut } from "@/lib/api";

export function StreakBadge({ userId }: { userId: string }) {
  const [streak, setStreak] = useState<StreakOut | null>(null);

  useEffect(() => {
    getStreak(userId).then(setStreak).catch(() => setStreak(null));
  }, [userId]);

  if (!streak || streak.current_streak === 0) return null;

  return (
    <div className="card stack">
      <div className="pill">Streak</div>
      <p>
        <strong>{streak.current_streak}-day streak</strong>
        {streak.freeze_used_in_current_streak ? " — one day covered by your freeze" : ""}.
        Longest so far: {streak.longest_streak} days. Non-punitive — a single missed day
        won&apos;t reset this.
      </p>
    </div>
  );
}
