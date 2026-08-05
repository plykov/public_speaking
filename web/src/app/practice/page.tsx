"use client";

import { useState } from "react";
import { RecorderPanel } from "@/components/RecorderPanel";
import { DevTranscriptPicker } from "@/components/DevTranscriptPicker";
import { Scorecard } from "@/components/Scorecard";
import { createSession, analyzeSession, type AnalysisResultOut } from "@/lib/api";
import { uploadBlobChunked } from "@/lib/chunkedUpload";
import { SAMPLE_TRANSCRIPTS } from "@/lib/sampleTranscripts";

type Step =
  | "context"
  | "baseline-record"
  | "baseline-analyzing"
  | "baseline-result"
  | "drill-record"
  | "retry-analyzing"
  | "retry-result";

const CONTEXTS = [
  { id: "recurring_meetings", label: "Recurring meetings", prompt: "You're in a status standup. Give a 30-second update on your team's biggest risk this week, and what you recommend doing about it." },
  { id: "presentation", label: "Presentation", prompt: "Open a five-minute update to leadership. In one sentence, what's the headline they should walk away with?" },
  { id: "interview", label: "Interview", prompt: "You're asked: \"Tell me about a time you disagreed with a decision.\" Answer in under 90 seconds, recommendation first." },
  { id: "difficult_conversation", label: "Difficult conversation", prompt: "You need to tell a stakeholder their requested deadline isn't realistic. Open with what you'd actually say." },
];

async function runAnalysis(scenario: string, transcriptId: string): Promise<AnalysisResultOut> {
  const sample = SAMPLE_TRANSCRIPTS.find((t) => t.id === transcriptId) ?? SAMPLE_TRANSCRIPTS[0];
  const session = await createSession(scenario);
  const blob = new Blob([JSON.stringify(sample.words)], { type: "application/json" });
  await uploadBlobChunked(session.id, blob);
  return analyzeSession(session.id);
}

export default function PracticeStudio() {
  const [step, setStep] = useState<Step>("context");
  const [context, setContext] = useState(CONTEXTS[0]);
  const [transcriptId, setTranscriptId] = useState(SAMPLE_TRANSCRIPTS[0].id);
  const [baselineResult, setBaselineResult] = useState<AnalysisResultOut | null>(null);
  const [retryResult, setRetryResult] = useState<AnalysisResultOut | null>(null);
  const [recordedUrl, setRecordedUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleBaselineComplete(audioUrl: string) {
    setRecordedUrl(audioUrl);
    setStep("baseline-analyzing");
    setError(null);
    try {
      const result = await runAnalysis(context.id, transcriptId);
      setBaselineResult(result);
      setStep("baseline-result");
    } catch (err) {
      setError(err instanceof Error ? err.message : "analysis failed");
      setStep("baseline-record");
    }
  }

  async function handleRetryComplete(audioUrl: string) {
    setRecordedUrl(audioUrl);
    setStep("retry-analyzing");
    setError(null);
    try {
      const result = await runAnalysis(context.id, transcriptId);
      setRetryResult(result);
      setStep("retry-result");
    } catch (err) {
      setError(err instanceof Error ? err.message : "analysis failed");
      setStep("drill-record");
    }
  }

  return (
    <div className="container stack">
      <h1>Practice Studio</h1>

      {error && <p className="error-banner">{error}</p>}

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
          <RecorderPanel prompt={context.prompt} onComplete={handleBaselineComplete} />
          <DevTranscriptPicker selectedId={transcriptId} onSelect={setTranscriptId} />
        </div>
      )}

      {step === "baseline-analyzing" && <div className="card">Analyzing your attempt…</div>}

      {step === "baseline-result" && baselineResult && (
        <div className="stack">
          {recordedUrl && <audio controls src={recordedUrl} style={{ width: "100%" }} />}
          <Scorecard result={baselineResult} />
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
          <Scorecard result={retryResult} previous={baselineResult} />
          <button
            className="btn"
            onClick={() => {
              setStep("context");
              setBaselineResult(null);
              setRetryResult(null);
              setRecordedUrl(null);
            }}
          >
            Start a new attempt
          </button>
        </div>
      )}
    </div>
  );
}
