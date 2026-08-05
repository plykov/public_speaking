"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { RecorderPanel } from "@/components/RecorderPanel";
import { DevTranscriptPicker } from "@/components/DevTranscriptPicker";
import { Scorecard } from "@/components/Scorecard";
import { EditableTranscript } from "@/components/EditableTranscript";
import { SlideDeckPanel } from "@/components/SlideDeckPanel";
import { ExemplarPanel } from "@/components/ExemplarPanel";
import {
  createSession,
  analyzeSession,
  rateFeedbackItem,
  upsertSlideTransitions,
  type AnalysisResultOut,
  type SlideDeckOut,
  type SlideTransitionOut,
} from "@/lib/api";
import { uploadBlobChunked } from "@/lib/chunkedUpload";
import { SAMPLE_TRANSCRIPTS } from "@/lib/sampleTranscripts";
import { CONTEXTS } from "@/lib/contexts";
import { getStoredUserId } from "@/lib/localUser";

type Step =
  | "context"
  | "baseline-record"
  | "baseline-analyzing"
  | "baseline-result"
  | "drill-record"
  | "retry-analyzing"
  | "retry-result";

async function runAnalysis(
  scenario: string,
  transcriptId: string,
  options: { userId?: string; parentSessionId?: string; existingSessionId?: string },
): Promise<AnalysisResultOut> {
  const sample = SAMPLE_TRANSCRIPTS.find((t) => t.id === transcriptId) ?? SAMPLE_TRANSCRIPTS[0];
  const sessionId = options.existingSessionId ?? (await createSession(scenario, options)).id;
  const blob = new Blob([JSON.stringify(sample.words)], { type: "application/json" });
  await uploadBlobChunked(sessionId, blob);
  return analyzeSession(sessionId);
}

function applyRating(
  result: AnalysisResultOut,
  feedbackItemId: string,
  useful: boolean,
): AnalysisResultOut {
  return {
    ...result,
    feedback_items: result.feedback_items.map((item) =>
      item.id === feedbackItemId ? { ...item, user_rating: useful } : item,
    ),
  };
}

function PracticeStudioInner() {
  const searchParams = useSearchParams();
  const preselectedContextId = searchParams.get("context");
  const preselectedContext = CONTEXTS.find((c) => c.id === preselectedContextId);

  const [step, setStep] = useState<Step>(preselectedContext ? "baseline-record" : "context");
  const [context, setContext] = useState(preselectedContext ?? CONTEXTS[0]);
  const [transcriptId, setTranscriptId] = useState(SAMPLE_TRANSCRIPTS[0].id);
  const [baselineResult, setBaselineResult] = useState<AnalysisResultOut | null>(null);
  const [retryResult, setRetryResult] = useState<AnalysisResultOut | null>(null);
  const [recordedUrl, setRecordedUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [quotaExceeded, setQuotaExceeded] = useState(false);

  // §4.2 slide-linked transcript: the session is created up front (rather
  // than inside runAnalysis) so a slide deck and its transitions have
  // somewhere to attach before the recording is even analyzed.
  const [baselineSessionId, setBaselineSessionId] = useState<string | null>(null);
  const [slideDeck, setSlideDeck] = useState<SlideDeckOut | null>(null);
  const [slideTransitions, setSlideTransitions] = useState<SlideTransitionOut[]>([]);

  useEffect(() => {
    if (step === "baseline-record" && baselineSessionId === null) {
      createSession(context.id, { userId: getStoredUserId() ?? undefined }).then((session) =>
        setBaselineSessionId(session.id),
      );
    }
  }, [step, baselineSessionId, context.id]);

  async function handleBaselineComplete(audioUrl: string) {
    setRecordedUrl(audioUrl);
    setStep("baseline-analyzing");
    setError(null);
    setQuotaExceeded(false);
    try {
      if (baselineSessionId && slideTransitions.length > 0) {
        await upsertSlideTransitions(baselineSessionId, slideTransitions);
      }
      const result = await runAnalysis(context.id, transcriptId, {
        userId: getStoredUserId() ?? undefined,
        existingSessionId: baselineSessionId ?? undefined,
      });
      setBaselineResult(result);
      setStep("baseline-result");
    } catch (err) {
      if (err instanceof Error && err.message.startsWith("402")) {
        setQuotaExceeded(true);
      } else {
        setError(err instanceof Error ? err.message : "analysis failed");
      }
      setStep("baseline-record");
    }
  }

  async function handleRetryComplete(audioUrl: string) {
    setRecordedUrl(audioUrl);
    setStep("retry-analyzing");
    setError(null);
    setQuotaExceeded(false);
    try {
      const result = await runAnalysis(context.id, transcriptId, {
        userId: getStoredUserId() ?? undefined,
        parentSessionId: baselineResult?.session_id,
      });
      setRetryResult(result);
      setStep("retry-result");
    } catch (err) {
      if (err instanceof Error && err.message.startsWith("402")) {
        setQuotaExceeded(true);
      } else {
        setError(err instanceof Error ? err.message : "analysis failed");
      }
      setStep("drill-record");
    }
  }

  async function handleRate(target: "baseline" | "retry", feedbackItemId: string, useful: boolean) {
    const setter = target === "baseline" ? setBaselineResult : setRetryResult;
    setter((prev) => (prev ? applyRating(prev, feedbackItemId, useful) : prev));
    try {
      await rateFeedbackItem(feedbackItemId, useful);
    } catch {
      // Non-critical — the optimistic update stays even if the PUT fails silently.
    }
  }

  return (
    <div className="container stack">
      <h1>Practice Studio</h1>

      {error && <p className="error-banner">{error}</p>}

      {quotaExceeded && (
        <div className="dev-banner stack">
          <div>
            You&apos;ve used your 3 free analyses this month. Upgrade to Pro for unlimited
            analyses, or grab an Event Sprint pass for 30 days of unlimited access.
          </div>
          <Link href="/settings" className="btn btn-primary" style={{ width: "fit-content" }}>
            See upgrade options
          </Link>
        </div>
      )}

      {step === "context" && (
        <div className="card stack">
          <p>What are you preparing for?</p>
          <div className="row">
            {CONTEXTS.map((c) => (
              <button
                key={c.id}
                className="btn"
                style={c.id === context.id ? { borderColor: "var(--accent)", fontWeight: 600 } : undefined}
                onClick={() => setContext(c)}
              >
                {c.label}
              </button>
            ))}
          </div>
          <button className="btn btn-primary" onClick={() => setStep("baseline-record")}>
            Start baseline recording
          </button>
        </div>
      )}

      {step === "baseline-record" && (
        <div className="stack">
          {baselineSessionId && (
            <SlideDeckPanel sessionId={baselineSessionId} deck={slideDeck} onUploaded={setSlideDeck} />
          )}
          <RecorderPanel
            prompt={context.prompt}
            onComplete={handleBaselineComplete}
            slidePageCount={slideDeck?.page_count}
            onSlideAdvance={(slideIndex, elapsedMs) =>
              setSlideTransitions((prev) => [...prev, { slide_index: slideIndex, timestamp_ms: elapsedMs }])
            }
          />
          <DevTranscriptPicker selectedId={transcriptId} onSelect={setTranscriptId} />
        </div>
      )}

      {step === "baseline-analyzing" && <div className="card">Analyzing your attempt…</div>}

      {step === "baseline-result" && baselineResult && (
        <div className="stack">
          {recordedUrl && <audio controls src={recordedUrl} style={{ width: "100%" }} />}
          <Scorecard
            result={baselineResult}
            onRate={(id, useful) => handleRate("baseline", id, useful)}
            slideDeck={slideDeck}
            slideTransitions={slideTransitions}
          />
          <EditableTranscript sessionId={baselineResult.session_id} onReanalyzed={setBaselineResult} />
          <ExemplarPanel sessionId={baselineResult.session_id} />
          <button className="btn btn-primary" onClick={() => setStep("drill-record")}>
            Try the drill: {baselineResult.drill.title}
          </button>
        </div>
      )}

      {step === "drill-record" && baselineResult && (
        <div className="stack">
          <RecorderPanel prompt={baselineResult.drill.prompt} onComplete={handleRetryComplete} />
          <DevTranscriptPicker selectedId={transcriptId} onSelect={setTranscriptId} />
        </div>
      )}

      {step === "retry-analyzing" && <div className="card">Analyzing your retry…</div>}

      {step === "retry-result" && retryResult && baselineResult && (
        <div className="stack">
          {recordedUrl && <audio controls src={recordedUrl} style={{ width: "100%" }} />}
          <p className="pill">Before / after</p>
          <Scorecard
            result={retryResult}
            previous={baselineResult}
            onRate={(id, useful) => handleRate("retry", id, useful)}
          />
          <EditableTranscript sessionId={retryResult.session_id} onReanalyzed={setRetryResult} />
          <ExemplarPanel sessionId={retryResult.session_id} />
          <button
            className="btn"
            onClick={() => {
              setStep("context");
              setBaselineResult(null);
              setRetryResult(null);
              setRecordedUrl(null);
              setBaselineSessionId(null);
              setSlideDeck(null);
              setSlideTransitions([]);
            }}
          >
            Start a new attempt
          </button>
        </div>
      )}
    </div>
  );
}

export default function PracticeStudio() {
  return (
    <Suspense fallback={<div className="container">Loading…</div>}>
      <PracticeStudioInner />
    </Suspense>
  );
}
