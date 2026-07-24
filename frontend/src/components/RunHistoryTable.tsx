"use client";
import { useEffect, useState } from "react";
import { getScrapeRuns } from "@/lib/api";
import { useLiveRelativeTime } from "@/lib/datetime";
import type { ScrapeRun } from "@/types/job";

function RelativeDateCell({ iso }: { iso: string }) {
  const value = useLiveRelativeTime(iso);
  return <>{value}</>;
}

function parseUtc(iso: string | null | undefined): number | null {
  if (!iso) return null;
  const formatted = (iso.endsWith("Z") || iso.includes("+") || iso.includes("-", 10)) ? iso : `${iso}Z`;
  const ms = new Date(formatted).getTime();
  return isNaN(ms) ? null : ms;
}

function formatDuration(run: ScrapeRun): string {
  if (run.duration_seconds != null && run.duration_seconds > 0) {
    const s = Math.round(run.duration_seconds);
    return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${s % 60}s`;
  }
  if (!run.finished_at) return "—";
  const startMs = parseUtc(run.started_at);
  const endMs = parseUtc(run.finished_at);
  if (!startMs || !endMs) return "—";
  const s = Math.round((endMs - startMs) / 1000);
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${s % 60}s`;
}

interface Props {
  refreshKey?: number;
}

const STATUS_BADGE: Record<string, string> = {
  COMPLETED: "badge-green",
  FAILED:    "badge-red",
  CANCELLED: "badge-amber",
  RUNNING:   "badge-indigo",
};

export default function RunHistoryTable({ refreshKey = 0 }: Props) {
  const [runs, setRuns] = useState<ScrapeRun[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getScrapeRuns()
      .then(setRuns)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [refreshKey]);

  if (loading) {
    return (
      <div style={{ padding: "20px 0", color: "var(--text-muted)", fontSize: 13 }}>
        Loading run history...
      </div>
    );
  }

  if (runs.length === 0) {
    return (
      <div style={{ padding: "16px 0", color: "var(--text-muted)", fontSize: 13 }}>
        No runs yet. Click <strong>Fetch All Sources</strong> to start.
      </div>
    );
  }

  return (
    <div style={{ overflowX: "auto", margin: "0 -4px" }}>
      <table
        style={{
          width: "100%",
          borderCollapse: "collapse",
          fontSize: 13,
        }}
      >
        <thead>
          <tr>
            {["#", "Started", "Duration", "Status", "Sites"].map((h) => (
              <th
                key={h}
                style={{
                  padding: "8px 12px",
                  textAlign: "left",
                  fontWeight: 600,
                  fontSize: 11,
                  letterSpacing: "0.05em",
                  textTransform: "uppercase",
                  color: "var(--text-muted)",
                  borderBottom: "1px solid var(--border)",
                  whiteSpace: "nowrap",
                }}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {runs.map((run, i) => (
            <tr
              key={run.id}
              style={{
                borderBottom: i < runs.length - 1 ? "1px solid var(--border)" : "none",
                transition: "background 0.1s",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-hover)")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "")}
            >
              {/* ID */}
              <td style={{ padding: "10px 12px", color: "var(--text-muted)", fontVariantNumeric: "tabular-nums" }}>
                #{run.id}
              </td>

              {/* Started */}
              <td style={{ padding: "10px 12px", whiteSpace: "nowrap" }}>
                <RelativeDateCell iso={run.started_at} />
              </td>

              {/* Duration */}
              <td style={{ padding: "10px 12px", color: "var(--text-secondary)", whiteSpace: "nowrap" }}>
                {formatDuration(run)}
              </td>

              {/* Status */}
              <td style={{ padding: "10px 12px" }}>
                <span className={`badge ${STATUS_BADGE[run.status] ?? "badge-neutral"}`}>
                  {run.status === "RUNNING" && (
                    <span
                      style={{
                        display: "inline-block",
                        width: 6,
                        height: 6,
                        borderRadius: "50%",
                        background: "currentColor",
                        animation: "pulse 1s ease-in-out infinite",
                      }}
                    />
                  )}
                  {run.status}
                </span>
              </td>

              {/* Site results */}
              <td style={{ padding: "10px 12px" }}>
                {Object.keys(run.site_results).length === 0 ? (
                  <span style={{ color: "var(--text-muted)" }}>—</span>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                    {Object.entries(run.site_results).map(([site, r]) => (
                      <div
                        key={site}
                        style={{ display: "flex", gap: 8, fontSize: 12, alignItems: "center" }}
                      >
                        <span style={{ color: "var(--text-secondary)", minWidth: 130 }}>{site}</span>
                        {r.error ? (
                          <span style={{ color: "var(--red)" }}>Error: {r.error}</span>
                        ) : (
                          <>
                            <span style={{ color: "var(--text-muted)" }}>{r.found} found</span>
                            <span
                              style={{
                                color: r.new > 0 ? "var(--green)" : "var(--text-muted)",
                                fontWeight: r.new > 0 ? 700 : 400,
                              }}
                            >
                              +{r.new} new
                            </span>
                            <span style={{ color: "var(--text-muted)" }}>{r.duplicates} dup</span>
                          </>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
