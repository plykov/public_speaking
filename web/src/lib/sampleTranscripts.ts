/**
 * DEV-MODE ONLY. No real STT vendor is wired up yet (see api/pipeline/stt.py) —
 * the backend's mock provider expects a JSON word-list "transcript" rather than
 * decoded audio. These canned transcripts stand in for that vendor call so the
 * scorecard / repair-loop flow can be exercised end-to-end today. They are sent
 * to the API instead of the user's real recording; the real recording is only
 * used for local playback in the browser. Delete this file once a real STT
 * provider (AssemblyAI/Deepgram) is wired up — see api/pipeline/stt.py.
 */

export interface SampleWord {
  text: string;
  start_ms: number;
  end_ms: number;
  confidence: number;
}

export interface SampleTranscript {
  id: string;
  label: string;
  description: string;
  words: SampleWord[];
}

export const SAMPLE_TRANSCRIPTS: SampleTranscript[] = [
  {
    id: "hedged",
    label: "Hedged recommendation",
    description: 'Opens with "maybe" and buries the point.',
    words: [
      { text: "So", start_ms: 0, end_ms: 150, confidence: 0.97 },
      { text: "maybe", start_ms: 200, end_ms: 420, confidence: 0.9 },
      { text: "we", start_ms: 430, end_ms: 520, confidence: 0.97 },
      { text: "could", start_ms: 530, end_ms: 680, confidence: 0.96 },
      { text: "consider", start_ms: 690, end_ms: 950, confidence: 0.95 },
      { text: "moving", start_ms: 960, end_ms: 1150, confidence: 0.96 },
      { text: "the", start_ms: 1160, end_ms: 1230, confidence: 0.97 },
      { text: "launch", start_ms: 1240, end_ms: 1500, confidence: 0.96 },
      { text: "date,", start_ms: 1510, end_ms: 1750, confidence: 0.95 },
      { text: "I", start_ms: 1850, end_ms: 1920, confidence: 0.97 },
      { text: "think.", start_ms: 1930, end_ms: 2150, confidence: 0.94 },
      { text: "We", start_ms: 2300, end_ms: 2400, confidence: 0.97 },
      { text: "should", start_ms: 2410, end_ms: 2600, confidence: 0.97 },
      { text: "push", start_ms: 2610, end_ms: 2780, confidence: 0.96 },
      { text: "it", start_ms: 2790, end_ms: 2860, confidence: 0.97 },
      { text: "two", start_ms: 2870, end_ms: 2990, confidence: 0.96 },
      { text: "weeks.", start_ms: 3000, end_ms: 3250, confidence: 0.95 },
    ],
  },
  {
    id: "point-first",
    label: "Point-first & clean",
    description: "Recommendation lands in the first sentence, minimal fillers.",
    words: [
      { text: "We", start_ms: 0, end_ms: 120, confidence: 0.98 },
      { text: "should", start_ms: 130, end_ms: 320, confidence: 0.98 },
      { text: "push", start_ms: 330, end_ms: 500, confidence: 0.97 },
      { text: "the", start_ms: 510, end_ms: 580, confidence: 0.98 },
      { text: "launch", start_ms: 590, end_ms: 850, confidence: 0.97 },
      { text: "two", start_ms: 860, end_ms: 980, confidence: 0.97 },
      { text: "weeks.", start_ms: 990, end_ms: 1250, confidence: 0.96 },
      { text: "QA", start_ms: 1400, end_ms: 1600, confidence: 0.95 },
      { text: "found", start_ms: 1610, end_ms: 1780, confidence: 0.97 },
      { text: "three", start_ms: 1790, end_ms: 1950, confidence: 0.97 },
      { text: "blockers", start_ms: 1960, end_ms: 2300, confidence: 0.96 },
      { text: "yesterday.", start_ms: 2310, end_ms: 2700, confidence: 0.95 },
    ],
  },
  {
    id: "filler-heavy",
    label: "Filler-heavy",
    description: "Frequent um/uh under time pressure.",
    words: [
      { text: "Um,", start_ms: 0, end_ms: 200, confidence: 0.9 },
      { text: "so", start_ms: 210, end_ms: 320, confidence: 0.95 },
      { text: "uh,", start_ms: 330, end_ms: 480, confidence: 0.88 },
      { text: "I", start_ms: 490, end_ms: 550, confidence: 0.97 },
      { text: "think", start_ms: 560, end_ms: 720, confidence: 0.96 },
      { text: "um", start_ms: 730, end_ms: 880, confidence: 0.89 },
      { text: "we", start_ms: 890, end_ms: 960, confidence: 0.97 },
      { text: "should", start_ms: 970, end_ms: 1150, confidence: 0.96 },
      { text: "uh", start_ms: 1160, end_ms: 1290, confidence: 0.88 },
      { text: "probably", start_ms: 1300, end_ms: 1550, confidence: 0.95 },
      { text: "push", start_ms: 1560, end_ms: 1720, confidence: 0.96 },
      { text: "the", start_ms: 1730, end_ms: 1800, confidence: 0.97 },
      { text: "launch.", start_ms: 1810, end_ms: 2100, confidence: 0.95 },
    ],
  },
];
