"use client";
import { useState, useEffect, useCallback } from "react";
import { getJobs, updateJobState, getSources } from "@/lib/api";
import type { Job, ApplicationState, Source } from "@/types/job";
import KanbanBoard from "@/components/KanbanBoard";
import FilterBar from "@/components/FilterBar";

export default function DashboardPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Active filters
  const [filterState, setFilterState] = useState("");
  const [filterSource, setFilterSource] = useState("");
  const [filterRole, setFilterRole] = useState("");
  const [filterQ, setFilterQ] = useState("");

  const load = useCallback(async () => {
    try {
      const [jobData, srcData] = await Promise.all([getJobs(), getSources()]);
      setJobs(jobData);
      setSources(srcData);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleStateChange = async (job: Job, newState: ApplicationState) => {
    // Optimistic update
    setJobs((prev) =>
      prev.map((j) =>
        j.id === job.id ? { ...j, application_state: newState } : j
      )
    );
    try {
      await updateJobState(job.id, newState);
    } catch {
      // Revert on failure
      setJobs((prev) =>
        prev.map((j) =>
          j.id === job.id ? { ...j, application_state: job.application_state } : j
        )
      );
    }
  };

  // Client-side filtering
  const filteredJobs = jobs.filter((j) => {
    if (filterState && j.application_state !== filterState) return false;
    if (filterSource && !j.sources.some((s) => s.platform === filterSource)) return false;
    if (filterRole && j.role_match !== filterRole) return false;
    if (filterQ) {
      const q = filterQ.toLowerCase();
      if (!j.job_title.toLowerCase().includes(q) && !j.company_name.toLowerCase().includes(q))
        return false;
    }
    return true;
  });

  // Unique role matches for filter dropdown
  const roleOptions = [...new Set(jobs.map((j) => j.role_match))].sort();

  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: "calc(100vh - 56px)",
          color: "var(--text-secondary)",
        }}
      >
        <div style={{ textAlign: "center" }}>
          <div
            className="spin"
            style={{
              width: 32,
              height: 32,
              border: "3px solid var(--border)",
              borderTopColor: "var(--accent)",
              borderRadius: "50%",
              margin: "0 auto 12px",
            }}
          />
          <p>Loading jobs…</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: "calc(100vh - 56px)",
          color: "var(--red)",
        }}
      >
        <div style={{ textAlign: "center" }}>
          <p style={{ fontSize: "20px", marginBottom: 8 }}>⚠️ Failed to load</p>
          <p style={{ color: "var(--text-secondary)", fontSize: "13px" }}>{error}</p>
          <button className="btn-primary" style={{ marginTop: 16 }} onClick={load}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: "24px", maxWidth: "100%", overflow: "hidden" }}>
      {/* Header */}
      <div style={{ marginBottom: "20px" }}>
        <h1
          style={{
            fontSize: "22px",
            fontWeight: 700,
            color: "var(--text-primary)",
            margin: 0,
          }}
        >
          Job Dashboard
        </h1>
        <p style={{ color: "var(--text-secondary)", marginTop: 4, fontSize: 13 }}>
          {jobs.length} job{jobs.length !== 1 ? "s" : ""} tracked
          {filteredJobs.length !== jobs.length && ` · ${filteredJobs.length} shown`}
        </p>
      </div>

      {/* Filters */}
      <FilterBar
        sources={sources}
        roleOptions={roleOptions}
        filterState={filterState}
        filterSource={filterSource}
        filterRole={filterRole}
        filterQ={filterQ}
        onStateChange={setFilterState}
        onSourceChange={setFilterSource}
        onRoleChange={setFilterRole}
        onQChange={setFilterQ}
      />

      {/* Kanban */}
      <KanbanBoard jobs={filteredJobs} onStateChange={handleStateChange} />
    </div>
  );
}
