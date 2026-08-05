"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { acceptTeamInvite } from "@/lib/api";
import { getStoredUserId } from "@/lib/localUser";

export default function JoinTeamPage() {
  const params = useParams<{ token: string }>();
  const router = useRouter();
  const [status, setStatus] = useState<"idle" | "joining" | "joined" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  async function handleJoin() {
    const userId = getStoredUserId();
    if (!userId) {
      setError("No account on this device yet — start a practice session first, then reopen this link.");
      setStatus("error");
      return;
    }
    setStatus("joining");
    setError(null);
    try {
      await acceptTeamInvite(params.token, userId);
      setStatus("joined");
      setTimeout(() => router.push("/team"), 1200);
    } catch (err) {
      setError(err instanceof Error ? err.message : "couldn't accept this invite");
      setStatus("error");
    }
  }

  return (
    <div className="container stack">
      <h1>Join team</h1>
      {status === "idle" && (
        <button className="btn btn-primary" onClick={handleJoin}>
          Accept invite
        </button>
      )}
      {status === "joining" && <p>Joining…</p>}
      {status === "joined" && <p>You&apos;re in — redirecting…</p>}
      {status === "error" && <p className="error-banner">{error}</p>}
    </div>
  );
}
