"use client";

import { useEffect, useState } from "react";
import { confirmCheckout, createCheckout, getSubscription, type SubscriptionOut } from "@/lib/api";

const TIER_LABELS: Record<string, string> = {
  free: "Free",
  pro: "Pro",
  event_sprint: "Event Sprint",
  team: "Team",
};

export function BillingSettings({ userId }: { userId: string }) {
  const [subscription, setSubscription] = useState<SubscriptionOut | null>(null);
  const [upgrading, setUpgrading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function refresh() {
    getSubscription(userId)
      .then(setSubscription)
      .catch((err) => setError(err instanceof Error ? err.message : "couldn't load subscription"));
  }

  useEffect(refresh, [userId]);

  async function handleUpgrade(tier: "pro" | "event_sprint") {
    setUpgrading(tier);
    setError(null);
    try {
      const checkout = await createCheckout(userId, tier);
      // No real Stripe here — there's no hosted checkout page to redirect
      // to, so "completing" a mock checkout is just confirming it directly.
      await confirmCheckout(checkout.id);
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "upgrade failed");
    } finally {
      setUpgrading(null);
    }
  }

  if (!subscription) return null;

  return (
    <div className="card stack">
      <div className="pill">Plan</div>
      <p>
        <strong>{TIER_LABELS[subscription.tier] ?? subscription.tier}</strong>
        {subscription.analyses_limit !== null && (
          <>
            {" "}
            — {subscription.analyses_this_month}/{subscription.analyses_limit} analyses used this
            month
          </>
        )}
      </p>
      {error && <p className="error-banner">{error}</p>}
      {subscription.tier === "free" && (
        <div className="stack">
          <p style={{ color: "var(--muted)", fontSize: "0.85rem" }}>
            No real payment processing exists in this environment — upgrading here simulates a
            completed Stripe checkout instantly, for demonstration.
          </p>
          <div className="row">
            <button
              className="btn btn-primary"
              onClick={() => handleUpgrade("pro")}
              disabled={upgrading !== null}
            >
              {upgrading === "pro" ? "Upgrading…" : "Upgrade to Pro (mock)"}
            </button>
            <button
              className="btn"
              onClick={() => handleUpgrade("event_sprint")}
              disabled={upgrading !== null}
            >
              {upgrading === "event_sprint" ? "Upgrading…" : "Buy Event Sprint — 30 days (mock)"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
