"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { getJobs, updateJobState, removeJob, getSources } from "@/lib/api";
import { useLiveRelativeTime } from "@/lib/datetime";
import type { Job, ApplicationState, Source } from "@/types/job";
import JobCard from "@/components/JobCard";
import FilterBar from "@/components/FilterBar";

const PAGE_SIZE = 30;

function Spinner() {
  return (
    <div
      className="spin"
      style={{
        width: 32,
        height: 32,
        border: "3px solid var(--border)",
        borderTopColor: "var(--accent)",
        borderRadius: "50%",
      }}
    />
  );
}

function StatCard({
  value,
  label,
  icon,
  gradient,
}: {
  value: string | number;
  label: string;
  icon: React.ReactNode;
  gradient: string;
}) {
  return (
    <div
      style={{
        background: "var(--bg-surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-md)",
        padding: "14px 18px",
        display: "flex",
        alignItems: "center",
        gap: "14px",
        boxShadow: "var(--shadow-xs)",
        minWidth: "160px",
      }}
    >
      <div
        style={{
          width: "40px",
          height: "40px",
          borderRadius: "10px",
          background: gradient,
          color: "#ffffff",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
          boxShadow: "0 2px 8px rgba(79, 70, 229, 0.2)",
        }}
      >
        {icon}
      </div>
      <div>
        <div style={{ fontSize: "20px", fontWeight: "800", color: "var(--text-primary)", letterSpacing: "-0.04em", lineHeight: 1.1 }}>
          {typeof value === "number" ? value.toLocaleString() : value}
        </div>
        <span style={{ fontSize: "11px", fontWeight: "600", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginTop: "3px", display: "block" }}>
          {label}
        </span>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [filterState, setFilterState] = useState("");
  const [filterSource, setFilterSource] = useState("");
  const [filterRole, setFilterRole] = useState("");
  const [filterQ, setFilterQ] = useState("");
  const [filterDateFrom, setFilterDateFrom] = useState("");
  const [filterDateTo, setFilterDateTo] = useState("");

  const [debouncedQ, setDebouncedQ] = useState("");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const handleQChange = (v: string) => {
    setFilterQ(v);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => setDebouncedQ(v), 300);
  };

  const [roleOptions, setRoleOptions] = useState<string[]>([]);

  const loadJobs = useCallback(
    async (pg: number) => {
      setLoading(true);
      setError(null);
      try {
        const [pageData, srcData] = await Promise.all([
          getJobs({
            state: filterState || undefined,
            source: filterSource || undefined,
            role_match: filterRole || undefined,
            q: debouncedQ || undefined,
            date_from: filterDateFrom || undefined,
            date_to: filterDateTo || undefined,
            page: pg,
            page_size: PAGE_SIZE,
          }),
          getSources(),
        ]);
        setJobs(pageData.jobs);
        setTotal(pageData.total);
        setTotalPages(pageData.total_pages);
        setSources(srcData);
        if (pg === 1) {
          const roles = [...new Set(pageData.jobs.map((j) => j.role_match))].sort();
          setRoleOptions(roles);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setLoading(false);
      }
    },
    [filterState, filterSource, filterRole, debouncedQ, filterDateFrom, filterDateTo]
  );

  useEffect(() => {
    setPage(1);
  }, [filterState, filterSource, filterRole, debouncedQ, filterDateFrom, filterDateTo]);

  useEffect(() => {
    void loadJobs(page);
  }, [loadJobs, page]);

  const latestSource = sources
    .filter((s) => s.last_scraped_at)
    .sort((a, b) => new Date(b.last_scraped_at!).getTime() - new Date(a.last_scraped_at!).getTime())[0];
  const latestFetchedLabel = useLiveRelativeTime(latestSource?.last_scraped_at ?? null);

  const handleStateChange = async (job: Job, newState: ApplicationState) => {
    setJobs((prev) => prev.map((j) => (j.id === job.id ? { ...j, application_state: newState } : j)));
    try {
      await updateJobState(job.id, newState);
    } catch {
      setJobs((prev) => prev.map((j) => (j.id === job.id ? { ...j, application_state: job.application_state } : j)));
    }
  };

  const handleRemove = async (job: Job) => {
    if (!filterState || filterState !== "REMOVED") {
      setJobs((prev) => prev.filter((j) => j.id !== job.id));
      setTotal((t) => t - 1);
    } else {
      setJobs((prev) => prev.map((j) => (j.id === job.id ? { ...j, application_state: "REMOVED" as ApplicationState } : j)));
    }
    try {
      await removeJob(job.id);
    } catch {
      void loadJobs(page);
    }
  };

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const isFiltered = !!(filterState || filterSource || filterRole || debouncedQ || filterDateFrom || filterDateTo);

  if (error) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "60vh" }}>
        <div style={{ textAlign: "center", maxWidth: 420, padding: "32px", background: "var(--bg-surface)", border: "1px solid var(--red-border)", borderRadius: "var(--radius-lg)", boxShadow: "var(--shadow-md)" }}>
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: "var(--radius-md)",
              background: "var(--red-bg)",
              color: "var(--red)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              margin: "0 auto 16px",
            }}
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          </div>
          <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8, color: "var(--text-primary)" }}>
            Unable to fetch listings
          </h2>
          <p style={{ color: "var(--text-secondary)", fontSize: 13, marginBottom: 20 }}>{error}</p>
          <button className="btn btn-primary" onClick={() => loadJobs(page)}>
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="container" style={{ paddingTop: 32, paddingBottom: 64, maxWidth: "1200px" }}>
      {/* Executive Dashboard Hero Banner */}
      <div
        style={{
          marginBottom: 28,
          background: "linear-gradient(135deg, rgba(79, 70, 229, 0.06) 0%, rgba(59, 130, 246, 0.06) 100%)",
          border: "1px solid var(--accent-border)",
          borderRadius: "var(--radius-lg)",
          padding: "24px 28px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 20,
          flexWrap: "wrap",
          boxShadow: "var(--shadow-xs)",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
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
              Sri Lanka Tech Jobs
            </span>
          </div>
          <h1 style={{ fontSize: 24, fontWeight: 800, color: "var(--text-primary)", letterSpacing: "-0.03em", margin: 0 }}>
            Software Job Aggregator
          </h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 4, maxWidth: "580px" }}>
            Real-time software engineering job listings collected across top Sri Lankan job boards with AI classification & application tracking.
          </p>
        </div>

        {/* Live Metrics HUD Cards */}
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <StatCard
            value={total}
            label={isFiltered ? "Filtered Results" : "Aggregated Jobs"}
            gradient="linear-gradient(135deg, #4f46e5 0%, #6366f1 100%)"
            icon={
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
                <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
              </svg>
            }
          />
          <StatCard
            value={latestFetchedLabel || "Never"}
            label="Latest Sync"
            gradient="linear-gradient(135deg, #10b981 0%, #059669 100%)"
            icon={
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <polyline points="12 6 12 12 16 14" />
              </svg>
            }
          />
        </div>
      </div>

      {/* Filter Bar */}
      <FilterBar
        sources={sources}
        roleOptions={roleOptions}
        filterState={filterState}
        filterSource={filterSource}
        filterRole={filterRole}
        filterQ={filterQ}
        filterDateFrom={filterDateFrom}
        filterDateTo={filterDateTo}
        onStateChange={setFilterState}
        onSourceChange={setFilterSource}
        onRoleChange={setFilterRole}
        onQChange={handleQChange}
        onDateFromChange={setFilterDateFrom}
        onDateToChange={setFilterDateTo}
      />

      {/* Main Content Area */}
      {loading ? (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            padding: "80px 0",
            gap: 16,
          }}
        >
          <Spinner />
          <p style={{ fontSize: 13, color: "var(--text-muted)", fontWeight: "500" }}>Loading job listings...</p>
        </div>
      ) : jobs.length === 0 && !isFiltered ? (
        /* Empty state — no jobs in DB */
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            padding: "80px 20px",
            textAlign: "center",
            background: "var(--bg-surface)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-lg)",
            marginTop: 20,
          }}
        >
          <div
            style={{
              width: 72,
              height: 72,
              borderRadius: "var(--radius-xl)",
              background: "var(--accent-dim)",
              border: "1px solid var(--accent-border)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              marginBottom: 20,
              color: "var(--accent)",
            }}
          >
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
              <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
              <line x1="12" y1="22.08" x2="12" y2="12" />
            </svg>
          </div>
          <h2 style={{ marginBottom: 10, color: "var(--text-primary)", fontSize: "18px", fontWeight: "700" }}>
            No Job Listings Found
          </h2>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", maxWidth: 420, lineHeight: 1.7, marginBottom: 24 }}>
            Your local database has no jobs yet. Open the{" "}
            <a href="/admin" style={{ color: "var(--accent)", fontWeight: "600", textDecoration: "underline" }}>
              Admin Portal
            </a>{" "}
            to trigger your first job fetch across Sri Lankan platforms.
          </p>
          <a href="/admin" className="btn btn-primary" style={{ padding: "10px 24px", fontSize: "13px" }}>
            Go to Admin Portal
          </a>
        </div>
      ) : jobs.length === 0 ? (
        /* No results for current filter */
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            padding: "70px 20px",
            textAlign: "center",
            background: "var(--bg-surface)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-lg)",
            marginTop: 20,
          }}
        >
          <div
            style={{
              width: 64,
              height: 64,
              borderRadius: "var(--radius-xl)",
              background: "var(--bg-overlay)",
              border: "1px solid var(--border)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              marginBottom: 16,
              color: "var(--text-muted)",
            }}
          >
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
          </div>
          <h2 style={{ marginBottom: 8, color: "var(--text-primary)", fontSize: "16px", fontWeight: "700" }}>
            No matching jobs found
          </h2>
          <p style={{ fontSize: 13, color: "var(--text-muted)", maxWidth: 360 }}>
            Try broadening your search term or clearing location and role filters.
          </p>
        </div>
      ) : (
        <>
          {/* Job List Container */}
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {jobs.map((job) => (
              <JobCard key={job.id} job={job} onStateChange={handleStateChange} onRemove={handleRemove} />
            ))}
          </div>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 6,
                marginTop: 36,
                paddingBottom: 8,
                flexWrap: "wrap",
              }}
            >
              <button
                id="pagination-prev"
                className="btn btn-ghost btn-sm"
                disabled={page === 1}
                onClick={() => handlePageChange(page - 1)}
                style={{ gap: 4 }}
              >
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <path d="M9 11L5 7l4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                Prev
              </button>

              {Array.from({ length: totalPages }, (_, i) => i + 1)
                .filter((p) => p === 1 || p === totalPages || Math.abs(p - page) <= 2)
                .reduce<(number | "…")[]>((acc, p, idx, arr) => {
                  if (idx > 0 && (p as number) - (arr[idx - 1] as number) > 1) acc.push("…");
                  acc.push(p);
                  return acc;
                }, [])
                .map((item, idx) =>
                  item === "…" ? (
                    <span key={`ellipsis-${idx}`} style={{ color: "var(--text-muted)", fontSize: 13, padding: "0 4px" }}>
                      &hellip;
                    </span>
                  ) : (
                    <button
                      key={item}
                      id={`pagination-page-${item}`}
                      className={item === page ? "btn btn-primary btn-sm" : "btn btn-ghost btn-sm"}
                      style={{ minWidth: 36 }}
                      onClick={() => handlePageChange(item as number)}
                    >
                      {item}
                    </button>
                  )
                )}

              <button
                id="pagination-next"
                className="btn btn-ghost btn-sm"
                disabled={page === totalPages}
                onClick={() => handlePageChange(page + 1)}
                style={{ gap: 4 }}
              >
                Next
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <path d="M5 3l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>

              <span style={{ fontSize: 12, color: "var(--text-muted)", marginLeft: 8 }}>
                {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, total)} of {total.toLocaleString()}
              </span>
            </div>
          )}
        </>
      )}
    </div>
  );
}
