"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { startScrape, getScrapeStatus, getScrapeRuns, toggleSource, cancelScrape } from "@/lib/api";
import { useLiveRelativeTime } from "@/lib/datetime";
import type { Source, ScrapeRun, SiteResult } from "@/types/job";

interface Props {
  sources: Source[];
  onSourcesChange?: (sources: Source[]) => void;
  onRunFinished?: () => void;
}

type RunState = "idle" | "running" | "done" | "failed";

const PLATFORM_COLORS: Record<string, string> = {
  "itpro.lk": "#6366f1",
  "anyjobok.com": "#22c55e",
  "governmentjob.lk": "#f59e0b",
  "jobenvoy.com": "#a855f7",
  "rooster.jobs": "#06b6d4",
  "topjobs.lk": "#ef4444",
  "xpress.jobs": "#64748b",
  "findmyjob.lk": "#10b981",
  "hire.lk": "#3b82f6",
};

function formatDurationSec(sec: number): string {
  if (isNaN(sec) || sec <= 0) return "0s";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  if (m === 0) return `${s}s`;
  return `${m}m ${s}s`;
}

function parseUtcDate(iso: string | null | undefined): number | null {
  if (!iso) return null;
  const formatted = iso.endsWith("Z") || iso.includes("+") || iso.includes("-", 10) ? iso : `${iso}Z`;
  const ms = new Date(formatted).getTime();
  return isNaN(ms) ? null : ms;
}

export default function ScrapeControlPanel({ sources, onSourcesChange, onRunFinished }: Props) {
  const [runState, setRunState] = useState<RunState>("idle");
  const [currentRun, setCurrentRun] = useState<ScrapeRun | null>(null);
  const [mergedResults, setMergedResults] = useState<Record<string, SiteResult>>({});
  const [error, setError] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const [now, setNow] = useState<number>(Date.now());
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Live tick timer every 1s when scraping
  useEffect(() => {
    if (currentRun?.status !== "RUNNING") return;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [currentRun?.status]);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  useEffect(() => () => stopPolling(), [stopPolling]);

  const startPolling = useCallback(
    (runId: number) => {
      stopPolling();
      pollRef.current = setInterval(async () => {
        try {
          const run = await getScrapeStatus(runId);
          setCurrentRun(run);
          if (run.site_results) {
            setMergedResults((prev) => ({ ...prev, ...run.site_results }));
          }
          if (run.status === "COMPLETED" || run.status === "CANCELLED") {
            setRunState("done");
            stopPolling();
            setCancelling(false);
            onRunFinished?.();
          } else if (run.status === "FAILED") {
            setRunState("failed");
            stopPolling();
            setCancelling(false);
            onRunFinished?.();
          }
        } catch {
          setError("Lost connection to backend");
          stopPolling();
        }
      }, 1500);
    },
    [onRunFinished, stopPolling]
  );

  useEffect(() => {
    let cancelled = false;

    getScrapeRuns()
      .then((runs) => {
        if (cancelled) return;

        const merged: Record<string, SiteResult> = {};
        for (let i = runs.length - 1; i >= 0; i--) {
          Object.assign(merged, runs[i].site_results);
        }
        setMergedResults(merged);

        const latest = runs[0] ?? null;
        setCurrentRun(latest);

        if (latest?.status === "RUNNING") {
          setRunState("running");
          startPolling(latest.id);
        } else if (latest?.status === "COMPLETED" || latest?.status === "CANCELLED") {
          setRunState("done");
        } else if (latest?.status === "FAILED") {
          setRunState("failed");
        }
      })
      .catch(() => {
        if (!cancelled) {
          setCurrentRun(null);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [startPolling]);

  const handleStart = async (sites: string[] | "all") => {
    setError(null);
    setRunState("running");
    setCancelling(false);
    try {
      const { run_id } = await startScrape(sites);
      startPolling(run_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setRunState("failed");
    }
  };

  const handleCancel = async () => {
    if (!currentRun) return;
    setCancelling(true);
    try {
      await cancelScrape(currentRun.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setCancelling(false);
    }
  };

  const totalNew = currentRun
    ? Object.entries(currentRun.site_results)
        .filter(([key]) => key !== "__classifier__")
        .reduce((s, [, r]) => s + ("new" in r ? r.new : 0), 0)
    : 0;
  const classifierResult = currentRun?.site_results["__classifier__"] as
    | { kept: number; removed: number; skipped: number }
    | undefined;
  const lastFetchAt = currentRun?.finished_at ?? currentRun?.started_at ?? null;
  const lastFetchLabel = useLiveRelativeTime(lastFetchAt);

  // Progress calculations
  const progress = currentRun?.progress;
  const totalSites = progress?.total_sites ?? 0;
  const completedSites = progress?.completed_sites ?? 0;
  const currentSite = progress?.current_site ?? null;
  const isClassifying = progress?.classifying ?? false;
  const classifyingCount = progress?.classifying_count ?? 0;
  const progressPercent = totalSites > 0 ? Math.round((completedSites / totalSites) * 100) : 0;

  // Duration & Estimated Remaining Time calculations
  const startedAtMs = parseUtcDate(currentRun?.started_at);
  const finishedAtMs = parseUtcDate(currentRun?.finished_at);

  const elapsedSec =
    currentRun?.status === "RUNNING" && startedAtMs
      ? Math.max(0, Math.floor((now - startedAtMs) / 1000))
      : currentRun?.duration_seconds != null
      ? Math.round(currentRun.duration_seconds)
      : startedAtMs && finishedAtMs
      ? Math.max(0, Math.floor((finishedAtMs - startedAtMs) / 1000))
      : 0;

  const backendEta = progress?.estimated_remaining_seconds;
  let estRemainingText = "Calculating...";
  if (backendEta != null && backendEta > 0) {
    estRemainingText = formatDurationSec(Math.round(backendEta));
  } else if (currentRun?.status === "RUNNING" && completedSites > 0 && totalSites > completedSites && elapsedSec > 0) {
    const avgSecPerSite = elapsedSec / completedSites;
    const remainingSites = totalSites - completedSites;
    let remSec = Math.round(remainingSites * avgSecPerSite);
    if (isClassifying) remSec += 3;
    estRemainingText = formatDurationSec(remSec);
  } else if (isClassifying) {
    estRemainingText = "~3s (AI filtering)";
  }

  return (
    <div style={{ padding: 0 }}>
      {/* Action buttons bar */}
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 20, alignItems: "center" }}>
        <button
          className="btn btn-primary"
          disabled={runState === "running"}
          onClick={() => handleStart("all")}
          style={{
            padding: "9px 20px",
            fontSize: "13px",
            fontWeight: "600",
            borderRadius: "var(--radius)",
            display: "inline-flex",
            alignItems: "center",
            gap: "8px",
            boxShadow: "0 2px 8px rgba(79, 70, 229, 0.25)",
          }}
        >
          {runState === "running" ? (
            <>
              <span
                className="spin"
                style={{
                  display: "inline-block",
                  width: 14,
                  height: 14,
                  border: "2px solid rgba(255,255,255,0.3)",
                  borderTopColor: "#fff",
                  borderRadius: "50%",
                }}
              />
              Fetching Active Sources...
            </>
          ) : (
            <>
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M7 1v12M1 7h12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
              Fetch All Sources
            </>
          )}
        </button>

        {/* Stop button — only visible when running */}
        {runState === "running" && (
          <button
            className="btn btn-danger"
            disabled={cancelling}
            onClick={handleCancel}
            style={{
              padding: "9px 18px",
              fontSize: "13px",
              fontWeight: "600",
              borderRadius: "var(--radius)",
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <rect x="2" y="2" width="8" height="8" rx="1.5" fill="currentColor" />
            </svg>
            {cancelling ? "Stopping..." : "Stop Fetching"}
          </button>
        )}
      </div>

      {/* Real-Time Live Fetching HUD & Progress — Visible when running */}
      {runState === "running" && (
        <div
          style={{
            marginBottom: 24,
            background: "var(--bg-surface)",
            border: "1px solid var(--accent-border)",
            borderRadius: "var(--radius-lg)",
            padding: "20px",
            boxShadow: "0 4px 20px rgba(79, 70, 229, 0.08)",
          }}
        >
          {/* Dual Metric Cards Grid */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
              gap: "12px",
              marginBottom: "16px",
            }}
          >
            {/* Elapsed Time Card */}
            <div
              style={{
                background: "var(--bg-hover)",
                border: "1px solid var(--border)",
                borderRadius: "var(--radius-md)",
                padding: "12px 16px",
                display: "flex",
                alignItems: "center",
                gap: "12px",
              }}
            >
              <div
                style={{
                  width: "36px",
                  height: "36px",
                  borderRadius: "10px",
                  background: "var(--accent-dim)",
                  color: "var(--accent)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                }}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <polyline points="12 6 12 12 16 14" />
                </svg>
              </div>
              <div>
                <span style={{ fontSize: "11px", fontWeight: "600", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                  Time Elapsed
                </span>
                <div style={{ fontSize: "18px", fontWeight: "800", color: "var(--text-primary)", letterSpacing: "-0.03em", lineHeight: 1.2 }}>
                  {formatDurationSec(elapsedSec)}
                </div>
              </div>
            </div>

            {/* Est. Remaining Time Card */}
            <div
              style={{
                background: "linear-gradient(135deg, rgba(79,70,229,0.04) 0%, rgba(168,85,247,0.04) 100%)",
                border: "1px solid var(--accent-border)",
                borderRadius: "var(--radius-md)",
                padding: "12px 16px",
                display: "flex",
                alignItems: "center",
                gap: "12px",
              }}
            >
              <div
                style={{
                  width: "36px",
                  height: "36px",
                  borderRadius: "10px",
                  background: "linear-gradient(135deg, #6366f1 0%, #a855f7 100%)",
                  color: "#ffffff",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                  boxShadow: "0 2px 6px rgba(99, 102, 241, 0.3)",
                }}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
                </svg>
              </div>
              <div>
                <span style={{ fontSize: "11px", fontWeight: "600", color: "var(--accent)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                  Est. Remaining
                </span>
                <div style={{ fontSize: "18px", fontWeight: "800", color: "var(--text-primary)", letterSpacing: "-0.03em", lineHeight: 1.2 }}>
                  {estRemainingText}
                </div>
              </div>
            </div>

            {/* Sites Progress Card */}
            <div
              style={{
                background: "var(--bg-hover)",
                border: "1px solid var(--border)",
                borderRadius: "var(--radius-md)",
                padding: "12px 16px",
                display: "flex",
                alignItems: "center",
                gap: "12px",
              }}
            >
              <div
                style={{
                  width: "36px",
                  height: "36px",
                  borderRadius: "10px",
                  background: "var(--green-bg)",
                  color: "var(--green)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                }}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                  <polyline points="22 4 12 14.01 9 11.01" />
                </svg>
              </div>
              <div>
                <span style={{ fontSize: "11px", fontWeight: "600", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                  Sites Completed
                </span>
                <div style={{ fontSize: "18px", fontWeight: "800", color: "var(--text-primary)", letterSpacing: "-0.03em", lineHeight: 1.2 }}>
                  {completedSites} <span style={{ fontSize: "13px", color: "var(--text-muted)", fontWeight: "500" }}>/ {totalSites}</span> ({progressPercent}%)
                </div>
              </div>
            </div>
          </div>

          {/* Current Operation Description Header */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <span style={{ fontSize: "13px", fontWeight: "600", color: "var(--text-primary)", display: "flex", alignItems: "center", gap: "6px" }}>
              {cancelling ? (
                <span style={{ color: "var(--red)" }}>Stopping active fetch operations...</span>
              ) : isClassifying ? (
                <span style={{ color: "var(--purple)", display: "inline-flex", alignItems: "center", gap: "6px" }}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
                  </svg>
                  Gemini AI Filtering {classifyingCount} scraped jobs...
                </span>
              ) : currentSite ? (
                <>
                  <span
                    className="spin"
                    style={{
                      width: 12,
                      height: 12,
                      border: "2px solid var(--accent)",
                      borderTopColor: "transparent",
                      borderRadius: "50%",
                    }}
                  />
                  Fetching listing data from <strong style={{ color: "var(--accent)" }}>{currentSite}</strong>
                </>
              ) : (
                "Initializing scraper processes..."
              )}
            </span>
            <span style={{ fontSize: "12px", fontWeight: "700", color: "var(--accent)" }}>
              {progressPercent}%
            </span>
          </div>

          {/* High-Tech Gradient Progress Bar */}
          <div
            style={{
              width: "100%",
              height: "10px",
              borderRadius: "9999px",
              background: "var(--bg-base)",
              border: "1px solid var(--border)",
              overflow: "hidden",
              position: "relative",
            }}
          >
            <div
              style={{
                width: `${progressPercent}%`,
                height: "100%",
                borderRadius: "9999px",
                background: cancelling
                  ? "var(--red)"
                  : "linear-gradient(90deg, #6366f1 0%, #a855f7 50%, #10b981 100%)",
                boxShadow: "0 0 12px rgba(99, 102, 241, 0.4)",
                transition: "width 0.4s ease-out",
              }}
            />
          </div>

          {/* Site Execution Chips Grid */}
          {completedSites > 0 && (
            <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginTop: "12px" }}>
              {(progress?.requested_sites ?? []).map((site) => {
                const isDone = !!currentRun?.site_results[site];
                const isCurrent = site === currentSite;
                return (
                  <span
                    key={site}
                    style={{
                      fontSize: "11px",
                      padding: "4px 10px",
                      borderRadius: "9999px",
                      fontWeight: "600",
                      background: isDone ? "var(--green-bg)" : isCurrent ? "var(--accent-dim)" : "var(--bg-base)",
                      color: isDone ? "var(--green)" : isCurrent ? "var(--accent)" : "var(--text-muted)",
                      border: `1px solid ${isDone ? "var(--green-border)" : isCurrent ? "var(--accent-border)" : "var(--border)"}`,
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "4px",
                      ...(isCurrent ? { animation: "pulse 1.2s ease-in-out infinite" } : {}),
                    }}
                  >
                    {isDone ? "✓ " : isCurrent ? "⚡ " : "• "}
                    {site}
                  </span>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div
          style={{
            background: "var(--red-bg)",
            border: "1px solid var(--red-border)",
            borderRadius: "var(--radius)",
            padding: "12px 16px",
            fontSize: "13px",
            color: "var(--red)",
            marginBottom: 16,
          }}
        >
          {error}
        </div>
      )}

      {/* Latest Run Results Status Box */}
      {(currentRun || Object.keys(mergedResults).length > 0) && (
        <div>
          <div style={{ marginBottom: 12, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span
              style={{
                fontSize: "11px",
                color: "var(--text-muted)",
                textTransform: "uppercase",
                letterSpacing: "0.06em",
                fontWeight: "700",
              }}
            >
              Platform Sources Breakdown
            </span>
            <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
              Last fetched: <strong style={{ color: "var(--text-primary)" }}>{lastFetchLabel || "—"}</strong>
              {elapsedSec > 0 && runState !== "running" && (
                <span style={{ marginLeft: 12, color: "var(--text-muted)" }}>
                  Duration: <strong style={{ color: "var(--text-primary)" }}>{formatDurationSec(elapsedSec)}</strong>
                </span>
              )}
            </span>
          </div>

          {/* Per-site breakdown rows */}
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {sources.map((src) => {
              const result = mergedResults[src.name];
              const siteResults = currentRun?.site_results || {};
              const isThisRunActive =
                currentRun?.status === "RUNNING" &&
                (!result || Object.keys(siteResults).includes(src.name) || Object.keys(siteResults).length === 0);
              const isFetchingThisSite = currentRun?.status === "RUNNING" && currentSite === src.name;

              return (
                <SiteRow
                  key={src.name}
                  source={src}
                  result={result}
                  color={PLATFORM_COLORS[src.name] ?? "#6b7280"}
                  running={currentRun?.status === "RUNNING" && isThisRunActive}
                  isFetching={isFetchingThisSite}
                  onToggle={async () => {
                    const updated = await toggleSource(src.name, !src.enabled);
                    onSourcesChange?.(sources.map((s) => (s.id === updated.id ? updated : s)));
                  }}
                  onRun={() => handleStart([src.name])}
                  runState={runState}
                />
              );
            })}

            {/* AI Classifier Summary Banner */}
            {classifierResult && (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "12px 16px",
                  borderRadius: "var(--radius-md)",
                  background: "linear-gradient(135deg, rgba(99,102,241,0.06) 0%, rgba(168,85,247,0.06) 100%)",
                  border: "1px solid var(--purple-border)",
                  marginTop: 6,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <div
                    style={{
                      width: "28px",
                      height: "28px",
                      borderRadius: "8px",
                      background: "var(--purple)",
                      color: "#fff",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
                    </svg>
                  </div>
                  <div>
                    <span style={{ fontSize: "13px", fontWeight: "700", color: "var(--purple)" }}>
                      Gemini AI Relevance Classifier
                    </span>
                    <p style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "1px" }}>
                      Filtered non-relevant software jobs automatically.
                    </p>
                  </div>
                </div>

                <div style={{ display: "flex", gap: "12px", fontSize: "12px" }}>
                  <span style={{ color: "var(--green)", fontWeight: "700", background: "var(--green-bg)", padding: "4px 10px", borderRadius: "9999px", border: "1px solid var(--green-border)" }}>
                    ✓ {classifierResult.kept} Kept
                  </span>
                  <span style={{ color: "var(--red)", fontWeight: "700", background: "var(--red-bg)", padding: "4px 10px", borderRadius: "9999px", border: "1px solid var(--red-border)" }}>
                    ✕ {classifierResult.removed} Filtered
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {runState === "idle" && !currentRun && (
        <p style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: 8 }}>
          Click Fetch All Sources to start pulling jobs from your configured platforms.
        </p>
      )}
    </div>
  );
}

function SiteRow({
  source,
  result,
  color,
  running,
  isFetching,
  onToggle,
  onRun,
  runState,
}: {
  source: Source;
  result: SiteResult | undefined;
  color: string;
  running: boolean;
  isFetching: boolean;
  onToggle: () => void;
  onRun: () => void;
  runState: string;
}) {
  const done = !!result;
  const relativeTime = useLiveRelativeTime(source.last_scraped_at);

  return (
    <div
      style={{
        background: isFetching ? "var(--accent-dim)" : "var(--bg-surface)",
        border: `1px solid ${isFetching ? "var(--accent-border)" : "var(--border)"}`,
        borderRadius: "var(--radius-md)",
        padding: "14px 16px",
        display: "flex",
        alignItems: "center",
        gap: 14,
        boxShadow: isFetching ? "0 2px 10px rgba(79, 70, 229, 0.12)" : "var(--shadow-xs)",
        transition: "all 0.25s ease",
      }}
    >
      {/* Dot */}
      <span
        style={{
          width: 9,
          height: 9,
          borderRadius: "50%",
          background: !source.enabled ? "var(--text-muted)" : done ? (result?.error ? "var(--red)" : "var(--green)") : color,
          flexShrink: 0,
          opacity: done || !source.enabled ? 1 : 0.6,
          ...(isFetching ? { animation: "pulse 1s ease-in-out infinite", boxShadow: `0 0 8px ${color}` } : {}),
        }}
      />

      {/* Name & Last Scraped */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
        <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>
          {source.name}
          {isFetching && (
            <span style={{ marginLeft: 8, fontSize: 11, color: "var(--accent)", fontWeight: 600 }}>
              fetching…
            </span>
          )}
        </span>
        <span style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>
          {source.last_scraped_at ? `Last fetched ${new Date(source.last_scraped_at).toLocaleDateString()} (${relativeTime})` : "Never fetched"}
        </span>
      </div>

      {/* Counts / Status */}
      <div style={{ minWidth: 180, display: "flex", justifyContent: "flex-end", alignItems: "center" }}>
        {done && !result?.error ? (
          <div style={{ display: "flex", gap: 10, fontSize: 12, alignItems: "center" }}>
            <Stat label="found" value={result!.found} />
            <Stat label="new" value={result!.new} highlight />
            <Stat label="dup" value={result!.duplicates} />
            {result?.duration_seconds !== undefined && result.duration_seconds > 0 && (
              <span style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 500 }}>
                ({result.duration_seconds}s)
              </span>
            )}
          </div>
        ) : done && result?.error ? (
          <span style={{ fontSize: 12, color: "var(--red)", fontWeight: 500 }}>{result.error}</span>
        ) : running ? (
          <span style={{ fontSize: 12, color: "var(--text-muted)" }} className="loading">
            Waiting…
          </span>
        ) : null}
      </div>

      {/* Actions (Toggle & Run) */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, paddingLeft: 14, borderLeft: "1px solid var(--border)" }}>
        <button
          className="btn btn-ghost btn-icon btn-sm"
          disabled={runState === "running" || !source.enabled}
          onClick={onRun}
          title={`Fetch ${source.name}`}
          style={{ width: "30px", height: "30px" }}
        >
          <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
            <path d="M11 6.5A4.5 4.5 0 1 1 6.5 2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            <path d="M6.5 2l2-2M6.5 2l2 2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
        <label className="toggle">
          <input type="checkbox" checked={source.enabled} onChange={onToggle} disabled={runState === "running"} />
          <span className="toggle-slider" />
        </label>
      </div>
    </div>
  );
}

function Stat({ label, value, highlight }: { label: string; value: number; highlight?: boolean }) {
  return (
    <span>
      <span style={{ color: "var(--text-muted)", fontSize: "11px" }}>{label} </span>
      <span
        style={{
          fontWeight: 700,
          color: highlight && value > 0 ? "var(--green)" : "var(--text-primary)",
        }}
      >
        {value}
      </span>
    </span>
  );
}
