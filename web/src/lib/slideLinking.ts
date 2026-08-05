import type { SlideTransitionOut } from "@/lib/api";

/**
 * §4.2 slide-linked transcript: which slide was showing at a given
 * elapsed-ms timestamp, given the ordered list of "advanced to slide N"
 * marks. Kept as a pure function (no React, no fetch) so it's testable
 * and reusable anywhere a timestamp needs a slide — same "pure core"
 * pattern as metrics/.
 */
export function buildSlideLookup(
  transitions: SlideTransitionOut[],
): (ms: number) => number | null {
  const sorted = [...transitions].sort((a, b) => a.timestamp_ms - b.timestamp_ms);
  return (ms: number) => {
    let current: number | null = null;
    for (const t of sorted) {
      if (t.timestamp_ms > ms) break;
      current = t.slide_index;
    }
    return current;
  };
}
