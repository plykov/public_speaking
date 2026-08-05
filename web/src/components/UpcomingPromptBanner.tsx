"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchUpcomingPrompt, getCalendarConnection, type UpcomingPromptOut } from "@/lib/api";
import { getStoredUserId } from "@/lib/localUser";

/**
 * §8 mechanism #1 ("the highest-leverage feature in the entire document"):
 * "Standup in 40 minutes — one interjection drill?" Only renders anything
 * once a calendar is connected and an event actually qualifies — silent
 * otherwise, not an empty card.
 */
export function UpcomingPromptBanner() {
  const [prompt, setPrompt] = useState<UpcomingPromptOut | null>(null);

  useEffect(() => {
    const userId = getStoredUserId();
    if (!userId) return;
    getCalendarConnection(userId)
      .then((connection) => {
        if (!connection.connected) return null;
        return fetchUpcomingPrompt(userId);
      })
      .then((result) => setPrompt(result))
      .catch(() => setPrompt(null));
  }, []);

  if (!prompt || !prompt.has_prompt || !prompt.drill) return null;

  return (
    <div className="dev-banner stack">
      <div>
        <strong>
          {prompt.event_title} in {prompt.minutes_until} minutes
        </strong>{" "}
        — {prompt.drill.title.toLowerCase()}?
      </div>
      <Link href="/practice" className="btn btn-primary" style={{ width: "fit-content" }}>
        Do the {prompt.drill.duration_minutes}-min drill
      </Link>
    </div>
  );
}
