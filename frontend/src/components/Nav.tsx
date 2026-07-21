"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_LINKS = [
  { href: "/", label: "Dashboard" },
  { href: "/admin", label: "Admin Portal" },
];

export default function Nav() {
  const path = usePathname();

  return (
    <nav
      style={{
        position: "sticky",
        top: 0,
        zIndex: 200,
        height: "var(--nav-height)",
        background: "rgba(255, 255, 255, 0.92)",
        backdropFilter: "blur(12px)",
        WebkitBackdropFilter: "blur(12px)",
        borderBottom: "1px solid var(--border)",
        boxShadow: "0 1px 0 rgba(15, 23, 42, 0.04)",
      }}
    >
      <div
        className="container"
        style={{
          height: "100%",
          display: "flex",
          alignItems: "center",
          gap: 0,
        }}
      >
        {/* Wordmark */}
        <Link
          href="/"
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            textDecoration: "none",
            marginRight: "auto",
          }}
        >
          <div
            style={{
              width: 30,
              height: 30,
              borderRadius: 8,
              background: "var(--accent)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <rect x="2" y="3" width="12" height="1.5" rx="0.75" fill="white" opacity="0.9" />
              <rect x="2" y="7" width="8" height="1.5" rx="0.75" fill="white" opacity="0.7" />
              <rect x="2" y="11" width="10" height="1.5" rx="0.75" fill="white" opacity="0.9" />
            </svg>
          </div>
          <div>
            <div
              style={{
                fontWeight: 700,
                fontSize: 14,
                color: "var(--text-primary)",
                letterSpacing: "-0.02em",
                lineHeight: 1.1,
              }}
            >
              JobAggregator
            </div>
            <div
              style={{
                fontSize: 10,
                color: "var(--text-muted)",
                letterSpacing: "0.04em",
                textTransform: "uppercase",
                fontWeight: 500,
              }}
            >
              Sri Lanka Tech Jobs
            </div>
          </div>
        </Link>

        {/* Navigation Links */}
        <div style={{ display: "flex", alignItems: "center", gap: 2 }}>
          {NAV_LINKS.map(({ href, label }) => {
            const active = path === href;
            return (
              <Link
                key={href}
                href={href}
                style={{
                  padding: "6px 14px",
                  borderRadius: "var(--radius)",
                  fontSize: 13,
                  fontWeight: active ? 600 : 500,
                  color: active ? "var(--accent)" : "var(--text-secondary)",
                  background: active ? "var(--accent-dim)" : "transparent",
                  textDecoration: "none",
                  transition: "all 0.15s",
                  letterSpacing: "-0.01em",
                }}
              >
                {label}
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
}
