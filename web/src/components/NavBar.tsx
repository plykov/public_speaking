import Link from "next/link";

const LINKS = [
  { href: "/", label: "Home" },
  { href: "/practice", label: "Practice" },
  { href: "/progress", label: "Progress" },
  { href: "/meeting-import", label: "Meeting import" },
  { href: "/settings", label: "Settings" },
];

export function NavBar() {
  return (
    <nav className="row" style={{ padding: "16px 20px 0", maxWidth: 720, margin: "0 auto" }}>
      {LINKS.map((l) => (
        <Link key={l.href} href={l.href} className="pill">
          {l.label}
        </Link>
      ))}
    </nav>
  );
}
