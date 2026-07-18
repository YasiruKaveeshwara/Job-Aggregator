"use client";
import { useEffect, useState } from "react";
import { getSources } from "@/lib/api";
import type { Source } from "@/types/job";
import ScrapeControlPanel from "@/components/ScrapeControlPanel";
import SourceToggleList from "@/components/SourceToggleList";
import RunHistoryTable from "@/components/RunHistoryTable";

export default function AdminPage() {
  const [sources, setSources] = useState<Source[]>([]);

  useEffect(() => {
    getSources().then(setSources).catch(console.error);
  }, []);

  return (
    <div style={{ padding: "24px", maxWidth: 900, margin: "0 auto" }}>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>Admin Portal</h1>
        <p style={{ color: "var(--text-secondary)", fontSize: 13, marginTop: 4 }}>
          Manually trigger scrape runs and manage sources.
        </p>
      </div>

      {/* Scrape control */}
      <section style={{ marginBottom: 28 }}>
        <SectionLabel icon="🚀" title="Scrape Control" />
        <ScrapeControlPanel sources={sources} />
      </section>

      {/* Source toggles */}
      <section style={{ marginBottom: 28 }}>
        <SectionLabel icon="🔌" title="Sources" />
        <SourceToggleList
          sources={sources}
          onSourcesChange={setSources}
        />
      </section>

      {/* Run history */}
      <section>
        <SectionLabel icon="📋" title="Run History" />
        <RunHistoryTable />
      </section>
    </div>
  );
}

function SectionLabel({ icon, title }: { icon: string; title: string }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        marginBottom: 12,
      }}
    >
      <span style={{ fontSize: 16 }}>{icon}</span>
      <h2 style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>{title}</h2>
    </div>
  );
}
