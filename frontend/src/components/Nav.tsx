"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

export default function Nav() {
  const path = usePathname();
  const links = [
    { href: "/", label: "Dashboard" },
    { href: "/admin", label: "Admin" },
  ];

  return (
    <nav
      style={{
        background: "var(--bg-surface)",
        borderBottom: "1px solid var(--border)",
        padding: "0 24px",
        height: "56px",
        display: "flex",
        alignItems: "center",
        gap: "32px",
        position: "sticky",
        top: 0,
        zIndex: 100,
      }}
    >
      {/* Logo */}
      <span
        style={{
          fontWeight: 700,
          fontSize: "15px",
          color: "var(--text-primary)",
          letterSpacing: "-0.01em",
          display: "flex",
          alignItems: "center",
          gap: "8px",
        }}
      >
        <span style={{ fontSize: "20px" }}>⚡</span>
        Job Aggregator
      </span>

      {/* Links */}
      <div style={{ display: "flex", gap: "4px", marginLeft: "auto" }}>
        {links.map(({ href, label }) => {
          const active = path === href;
          return (
            <Link
              key={href}
              href={href}
              style={{
                padding: "6px 14px",
                borderRadius: "8px",
                fontSize: "13px",
                fontWeight: active ? 600 : 500,
                color: active ? "var(--accent-light)" : "var(--text-secondary)",
                background: active ? "var(--accent-dim)" : "transparent",
                textDecoration: "none",
                transition: "all 0.15s",
              }}
            >
              {label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
