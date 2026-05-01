import Link from "next/link";

const items = [
  ["Overview", "/"],
  ["Escalations", "/escalations"],
  ["Economics", "/economics"],
  ["Feedback", "/feedback"],
  ["Incidents", "/incidents"],
];

export default function TopNav() {
  return (
    <nav className="topnav">
      <div className="brand">Negotiation Ops</div>
      <div className="topnav-links">
        {items.map(([label, href]) => (
          <Link key={href} href={href} className="navlink">
            {label}
          </Link>
        ))}
      </div>
    </nav>
  );
}
