import Link from "next/link";

export default function Home() {
  return (
    <div className="container stack">
      <h1>Cadence</h1>
      <p style={{ color: "var(--muted)" }}>
        Be heard in English meetings. Practice the meeting-fluency skills nobody else
        teaches: interjection, hedging, point-first structure.
      </p>
      <Link href="/practice" className="btn btn-primary" style={{ width: "fit-content" }}>
        Start a practice session
      </Link>
    </div>
  );
}
