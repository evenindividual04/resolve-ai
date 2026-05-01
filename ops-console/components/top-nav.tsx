"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const items = [
  ["Overview", "/"],
  ["Escalations", "/escalations"],
  ["Workflows", "/workflows"],
  ["Borrowers", "/borrowers"],
  ["Economics", "/economics"],
  ["Feedback", "/feedback"],
  ["Incidents", "/incidents"],
];

export default function TopNav() {
  const pathname = usePathname();

  return (
    <nav className="topnav">
      <div className="brand-block">
        <div className="brand-mark">RA</div>
        <div>
          <div className="brand">Resolve AI</div>
          <div className="brand-subtitle">Collections Console</div>
        </div>
      </div>
      <div className="topnav-links" aria-label="Primary navigation">
        {items.map(([label, href]) => {
          const active = pathname === href || (href !== "/" && pathname.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              className={`navlink ${active ? "active" : ""}`}
              aria-current={active ? "page" : undefined}
            >
              {label}
            </Link>
          );
        })}
      </div>
      <div className="topnav-status">
        <span className="status-dot" />
        Live · Direct
      </div>
    </nav>
  );
}
