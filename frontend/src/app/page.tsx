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
        width: 28,
        height: 28,
        border: "2.5px solid var(--border)",
        borderTopColor: "var(--accent)",
        borderRadius: "50%",
      }}
    />
  );
}

function StatPill({ value, label, color }: { value: number; label: string; color: string }) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        padding: "10px 20px",
        background: "var(--bg-surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-md)",
        boxShadow: "var(--shadow-xs)",
        minWidth: 90,
      }}
    >
      <span style={{ fontSize: 22, fontWeight: 800, color, letterSpacing: "-0.04em", lineHeight: 1 }}>
        {value.toLocaleString()}
      </span>
      <span style={{ fontSize: 11, fontWeight: 500, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginTop: 3 }}>
        {label}
      </span>
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

  const loadJobs = useCallback(async (pg: number) => {
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
  }, [filterState, filterSource, filterRole, debouncedQ, filterDateFrom, filterDateTo]);

  useEffect(() => { setPage(1); }, [filterState, filterSource, filterRole, debouncedQ, filterDateFrom, filterDateTo]);
  useEffect(() => { void loadJobs(page); }, [loadJobs, page]);

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

  // Error state
  if (error) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "60vh" }}>
        <div style={{ textAlign: "center", maxWidth: 400 }}>
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: "var(--radius-lg)",
              background: "var(--red-bg)",
              border: "1px solid var(--red-border)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              margin: "0 auto 16px",
            }}
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="9" stroke="var(--red)" strokeWidth="1.5" />
              <path d="M12 8v4M12 16h.01" stroke="var(--red)" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </div>
          <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8, color: "var(--text-primary)" }}>
            Failed to load
          </h2>
          <p style={{ color: "var(--text-secondary)", fontSize: 13, marginBottom: 20 }}>{error}</p>
          <button className="btn btn-primary" onClick={() => loadJobs(page)}>
            Try again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="container" style={{ paddingTop: 28, paddingBottom: 40 }}>

      {/* Page header */}
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: 16,
          marginBottom: 24,
          flexWrap: "wrap",
        }}
      >
        <div>
          <h1 style={{ marginBottom: 6 }}>Job Dashboard</h1>
          <p style={{ fontSize: 13, color: "var(--text-muted)" }}>
            {isFiltered
              ? `${total} result${total !== 1 ? "s" : ""} matching your filters`
              : `${total.toLocaleString()} tech job${total !== 1 ? "s" : ""} aggregated`}
            {latestSource?.last_scraped_at && (
              <> &middot; Last fetched <span style={{ color: "var(--text-secondary)" }}>{latestFetchedLabel}</span></>
            )}
          </p>
        </div>

        {/* Stat pills */}
        {!isFiltered && total > 0 && (
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <StatPill value={total} label="Total" color="var(--accent)" />
            {totalPages > 1 && (
              <StatPill value={page} label={`of ${totalPages} pages`} color="var(--text-secondary)" />
            )}
          </div>
        )}
      </div>

      {/* Filters */}
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

      {/* Content */}
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
          <p style={{ fontSize: 13, color: "var(--text-muted)" }}>Loading jobs...</p>
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
            }}
          >
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
              <rect x="4" y="6" width="24" height="3" rx="1.5" fill="var(--accent)" opacity="0.8" />
              <rect x="4" y="13" width="18" height="3" rx="1.5" fill="var(--accent)" opacity="0.5" />
              <rect x="4" y="20" width="21" height="3" rx="1.5" fill="var(--accent)" opacity="0.8" />
            </svg>
          </div>
          <h2 style={{ marginBottom: 10, color: "var(--text-primary)" }}>No jobs yet</h2>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", maxWidth: 380, lineHeight: 1.7, marginBottom: 24 }}>
            Head to the{" "}
            <a href="/admin" style={{ color: "var(--accent)", textDecoration: "underline", textUnderlineOffset: 2 }}>
              Admin Portal
            </a>{" "}
            and run a fetch to pull jobs from your configured sources.
          </p>
        </div>

      ) : jobs.length === 0 ? (
        /* No results for current filter */
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            padding: "60px 20px",
            textAlign: "center",
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
            }}
          >
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
              <circle cx="12" cy="12" r="8.5" stroke="var(--text-muted)" strokeWidth="1.5" />
              <path d="M18 18l5 5" stroke="var(--text-muted)" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </div>
          <h2 style={{ marginBottom: 8, color: "var(--text-primary)" }}>No results found</h2>
          <p style={{ fontSize: 13, color: "var(--text-muted)", maxWidth: 340 }}>
            Try adjusting your filters, or clear them to see all jobs.
          </p>
        </div>

      ) : (
        <>
          {/* Job list */}
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {jobs.map((job) => (
              <JobCard
                key={job.id}
                job={job}
                onStateChange={handleStateChange}
                onRemove={handleRemove}
              />
            ))}
          </div>

          {/* Pagination */}
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
                    <span
                      key={`ellipsis-${idx}`}
                      style={{ color: "var(--text-muted)", fontSize: 13, padding: "0 4px" }}
                    >
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

              <span style={{ fontSize: 12, color: "var(--text-muted)", marginLeft: 6 }}>
                {((page - 1) * PAGE_SIZE) + 1}–{Math.min(page * PAGE_SIZE, total)} of {total.toLocaleString()}
              </span>
            </div>
          )}
        </>
      )}
    </div>
  );
}
