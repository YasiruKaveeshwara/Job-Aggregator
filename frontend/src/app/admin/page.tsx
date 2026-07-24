"use client";
import { useEffect, useState } from "react";
import { getSources } from "@/lib/api";
import type { Source } from "@/types/job";
import ScrapeControlPanel from "@/components/ScrapeControlPanel";
import RunHistoryTable from "@/components/RunHistoryTable";
import KeywordEditor from "@/components/KeywordEditor";
import SearchLocationEditor from "@/components/SearchLocationEditor";
import SettingsPanel from "@/components/SettingsPanel";

const SECTIONS = [
  { id: "sources", label: "Sources & Scrape Control" },
  { id: "settings", label: "Settings" },
  { id: "keywords", label: "Keywords" },
  { id: "locations", label: "Locations" },
  { id: "history", label: "Run History" },
];

function SectionIcon({ id }: { id: string }) {
  const icons: Record<string, React.ReactElement> = {
    sources: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <circle cx="8" cy="8" r="5.5" stroke="currentColor" strokeWidth="1.25" />
        <circle cx="8" cy="8" r="2.5" fill="currentColor" opacity="0.5" />
      </svg>
    ),
    settings: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <path d="M8 2v1.5M8 12.5V14M2 8h1.5M12.5 8H14M3.75 3.75l1.06 1.06M11.19 11.19l1.06 1.06M3.75 12.25l1.06-1.06M11.19 4.81l1.06-1.06" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" />
        <circle cx="8" cy="8" r="2" stroke="currentColor" strokeWidth="1.25" />
      </svg>
    ),
    keywords: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <path d="M2 4h12M2 8h8M2 12h10" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" />
      </svg>
    ),
    locations: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <path d="M8 2a4 4 0 0 1 4 4c0 3-4 8-4 8S4 9 4 6a4 4 0 0 1 4-4z" stroke="currentColor" strokeWidth="1.25" />
        <circle cx="8" cy="6" r="1.5" fill="currentColor" opacity="0.6" />
      </svg>
    ),
    history: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <circle cx="8" cy="8" r="5.5" stroke="currentColor" strokeWidth="1.25" />
        <path d="M8 5v3.5l2 1.5" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" />
      </svg>
    ),
  };
  return icons[id] ?? null;
}

function SectionHeader({ id, title }: { id: string; title: string }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        marginBottom: 14,
        paddingBottom: 12,
        borderBottom: "1px solid var(--border)",
      }}
    >
      <span
        style={{
          width: 28,
          height: 28,
          borderRadius: "var(--radius-sm)",
          background: "var(--accent-dim)",
          color: "var(--accent)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
        }}
      >
        <SectionIcon id={id} />
      </span>
      <h2 style={{ fontSize: 15, fontWeight: 700, margin: 0, letterSpacing: "-0.01em" }}>{title}</h2>
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
    <div className="container" style={{ paddingTop: 28, paddingBottom: 48 }}>

      {/* Page Header */}
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ marginBottom: 6 }}>Admin Portal</h1>
        <p style={{ fontSize: 13, color: "var(--text-muted)" }}>
          Trigger scrape runs, manage sources, configure settings, keywords and locations.
        </p>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
        {/* Sources & Scrape Control */}
        <section className="card" style={{ padding: "20px 24px" }}>
          <SectionHeader id="sources" title="Sources & Scrape Control" />
          <ScrapeControlPanel
            sources={sources}
            onSourcesChange={setSources}
            onRunFinished={() => {
              setHistoryRefreshKey((v) => v + 1);
              loadSources();
            }}
          />
        </section>

        {/* Application Settings */}
        <section className="card" style={{ padding: "20px 24px" }}>
          <SectionHeader id="settings" title="Application Settings" />
          <SettingsPanel />
        </section>

        {/* Keywords */}
        <section className="card" style={{ padding: "20px 24px" }}>
          <SectionHeader id="keywords" title="Keywords" />
          <KeywordEditor />
        </section>

        {/* Locations */}
        <section className="card" style={{ padding: "20px 24px" }}>
          <SectionHeader id="locations" title="Locations" />
          <SearchLocationEditor />
        </section>

        {/* Run History */}
        <section className="card" style={{ padding: "20px 24px" }}>
          <SectionHeader id="history" title="Run History" />
          <RunHistoryTable refreshKey={historyRefreshKey} />
        </section>
      </div>
    </div>
  );
}
