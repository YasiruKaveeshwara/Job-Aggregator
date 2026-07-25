"use client";

import { useEffect, useState } from "react";
import { getSources } from "@/lib/api";
import type { Source } from "@/types/job";
import ScrapeControlPanel from "@/components/ScrapeControlPanel";
import RunHistoryTable from "@/components/RunHistoryTable";
import KeywordEditor from "@/components/KeywordEditor";
import SearchLocationEditor from "@/components/SearchLocationEditor";
import SettingsPanel from "@/components/SettingsPanel";

function SectionIcon({ id }: { id: string }) {
  const icons: Record<string, React.ReactElement> = {
    sources: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="10" />
        <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20" />
        <path d="M2 12h20" />
      </svg>
    ),
    settings: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
      </svg>
    ),
    keywords: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M4 9h16M4 15h16M10 3L8 21M16 3l-2 18" />
      </svg>
    ),
    locations: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
        <circle cx="12" cy="10" r="3" />
      </svg>
    ),
    history: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 8v4l3 3" />
        <circle cx="12" cy="12" r="9" />
      </svg>
    ),
  };
  return icons[id] ?? null;
}

function SectionHeader({ id, title, subtitle }: { id: string; title: string; subtitle?: string }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        marginBottom: 16,
        paddingBottom: 14,
        borderBottom: "1px solid var(--border)",
      }}
    >
      <div
        style={{
          width: 34,
          height: 34,
          borderRadius: "var(--radius)",
          background: "var(--accent-dim)",
          color: "var(--accent)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
        }}
      >
        <SectionIcon id={id} />
      </div>
      <div>
        <h2 style={{ fontSize: 16, fontWeight: 700, margin: 0, letterSpacing: "-0.02em", color: "var(--text-primary)" }}>{title}</h2>
        {subtitle && <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 2 }}>{subtitle}</p>}
      </div>
    </div>
  );
}

export default function AdminPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [historyRefreshKey, setHistoryRefreshKey] = useState(0);

  const loadSources = () => {
    getSources().then(setSources).catch(console.error);
  };

  useEffect(() => {
    loadSources();
  }, []);

  return (
    <div className="container" style={{ paddingTop: 32, paddingBottom: 64, maxWidth: "1200px" }}>
      {/* Executive Page Hero Header */}
      <div
        style={{
          marginBottom: 32,
          background: "linear-gradient(135deg, rgba(79, 70, 229, 0.05) 0%, rgba(168, 85, 247, 0.05) 100%)",
          border: "1px solid var(--accent-border)",
          borderRadius: "var(--radius-lg)",
          padding: "24px 28px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          boxShadow: "var(--shadow-xs)",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
            <span
              style={{
                fontSize: 11,
                fontWeight: 700,
                color: "var(--accent)",
                background: "var(--accent-dim)",
                border: "1px solid var(--accent-border)",
                padding: "3px 10px",
                borderRadius: "9999px",
                textTransform: "uppercase",
                letterSpacing: "0.06em",
              }}
            >
              Control Center
            </span>
          </div>
          <h1 style={{ fontSize: 24, fontWeight: 800, color: "var(--text-primary)", letterSpacing: "-0.03em", margin: 0 }}>
            Admin Portal
          </h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 4, maxWidth: "600px" }}>
            Execute real-time job scrapers, configure AI credentials, manage target engineering keywords and monitor run audit logs.
          </p>
        </div>

        {/* System Liveness Badge */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            background: "var(--bg-surface)",
            border: "1px solid var(--border)",
            padding: "8px 14px",
            borderRadius: "var(--radius)",
            boxShadow: "var(--shadow-xs)",
          }}
        >
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: "var(--green)",
              boxShadow: "0 0 8px var(--green)",
            }}
          />
          <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text-primary)" }}>
            Engine Ready
          </span>
        </div>
      </div>

      {/* Main Content Layout */}
      <div style={{ display: "flex", flexDirection: "column", gap: 28 }}>
        {/* Section 1: Sources & Live Scrape Control */}
        <section
          style={{
            background: "var(--bg-surface)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-lg)",
            padding: "24px",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          <SectionHeader
            id="sources"
            title="Sources & Fetch Operations Control"
            subtitle="Trigger scrape runs, monitor live real-time progress and configure platform sources."
          />
          <ScrapeControlPanel
            sources={sources}
            onSourcesChange={setSources}
            onRunFinished={() => {
              setHistoryRefreshKey((v) => v + 1);
              loadSources();
            }}
          />
        </section>

        {/* Section 2: Application Settings (Gemini AI Key) */}
        <section
          style={{
            background: "var(--bg-surface)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-lg)",
            padding: "24px",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          <SectionHeader
            id="settings"
            title="Application & Secret Credentials"
            subtitle="Manage Gemini API keys and local database secret configurations."
          />
          <SettingsPanel />
        </section>

        {/* Section 3: Target Keywords Configuration */}
        <section
          style={{
            background: "var(--bg-surface)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-lg)",
            padding: "24px",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          <SectionHeader
            id="keywords"
            title="Target Keywords & Exclusions"
            subtitle="Define role search terms sent to job boards and negative keyword rules."
          />
          <KeywordEditor />
        </section>

        {/* Section 4: Target Locations Configuration */}
        <section
          style={{
            background: "var(--bg-surface)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-lg)",
            padding: "24px",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          <SectionHeader
            id="locations"
            title="Search Locations & District Modifiers"
            subtitle="Configure geographic filters for rooster.jobs and Sri Lankan regions."
          />
          <SearchLocationEditor />
        </section>

        {/* Section 5: Run Audit Logs */}
        <section
          style={{
            background: "var(--bg-surface)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-lg)",
            padding: "24px",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          <SectionHeader
            id="history"
            title="Scrape Run Audit History"
            subtitle="Review execution timestamps, durations, and per-source result breakdowns."
          />
          <RunHistoryTable refreshKey={historyRefreshKey} />
        </section>
      </div>
    </div>
  );
}
