export interface PracticeContext {
  id: string;
  label: string;
  prompt: string;
}

export const CONTEXTS: PracticeContext[] = [
  {
    id: "recurring_meetings",
    label: "Recurring meetings",
    prompt:
      "You're in a status standup. Give a 30-second update on your team's biggest risk this week, and what you recommend doing about it.",
  },
  {
    id: "presentation",
    label: "Presentation",
    prompt: "Open a five-minute update to leadership. In one sentence, what's the headline they should walk away with?",
  },
  {
    id: "interview",
    label: "Interview",
    prompt: 'You\'re asked: "Tell me about a time you disagreed with a decision." Answer in under 90 seconds, recommendation first.',
  },
  {
    id: "difficult_conversation",
    label: "Difficult conversation",
    prompt: "You need to tell a stakeholder their requested deadline isn't realistic. Open with what you'd actually say.",
  },
];
