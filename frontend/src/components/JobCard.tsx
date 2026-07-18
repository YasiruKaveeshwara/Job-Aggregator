"use client";
import { useState } from "react";
import type { Job, ApplicationState } from "@/types/job";

interface JobCardProps {
  job: Job;
  onStateChange: (job: Job, newState: ApplicationState) => void;
}

const ALL_STATES: ApplicationState[] = [
  "DISCOVERED",
  "REVIEWING",
  "APPLIED",
  "INTERVIEWING",
  "ARCHIVED",
];

const PLATFORM_COLORS: Record<string, string> = {
  "itpro.lk": "badge-indigo",
  "anyjobok.com": "badge-green",
  "governmentjob.lk": "badge-amber",
  "jobenvoy.com": "badge-purple",
  "rooster.jobs": "badge-cyan",
};

function formatDate(iso: string | null): string {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleDateString("en-GB", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch {
    return "";
  }
}

export default function JobCard({ job, onStateChange }: JobCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className="card card-hover"
      style={{ padding: "12px", cursor: "default" }}
    >
      {/* Title */}
      <p
        style={{
          fontWeight: 600,
          fontSize: 13,
          color: "var(--text-primary)",
          lineHeight: 1.4,
          marginBottom: 3,
        }}
      >
        {job.job_title}
      </p>

      {/* Company + location */}
      <p
        style={{
          fontSize: 12,
          color: "var(--text-secondary)",
          marginBottom: 6,
        }}
      >
        {job.company_name}
        {job.location_normalized && (
          <span style={{ color: "var(--text-muted)" }}>
            {" · "}
            {job.location_normalized}
          </span>
        )}
      </p>

      {/* Role badge + salary */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 8 }}>
        <span className="badge badge-indigo" style={{ fontSize: 10 }}>
          {job.role_match}
        </span>
        {job.salary_disclosed && job.salary_min != null && (
          <span className="badge badge-green" style={{ fontSize: 10 }}>
            LKR {job.salary_min.toLocaleString()}
            {job.salary_max && job.salary_max !== job.salary_min
              ? `–${job.salary_max.toLocaleString()}`
              : ""}
          </span>
        )}
      </div>

      {/* Source badges */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 8 }}>
        {job.sources.map((s) => (
          <a
            key={s.id}
            href={s.url}
            target="_blank"
            rel="noopener noreferrer"
            className={`badge ${PLATFORM_COLORS[s.platform] ?? "badge-neutral"}`}
            style={{ fontSize: 10, textDecoration: "none" }}
          >
            ↗ {s.platform}
          </a>
        ))}
      </div>

      {/* Posted date */}
      {job.posted_date && (
        <p style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 8 }}>
          Posted {formatDate(job.posted_date)}
        </p>
      )}

      {/* Description toggle */}
      {job.description_clean && (
        <button
          className="btn-ghost"
          style={{ fontSize: 11, padding: "4px 8px", marginBottom: 8, width: "100%" }}
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? "Hide details ▲" : "Show details ▼"}
        </button>
      )}
      {expanded && job.description_clean && (
        <p
          style={{
            fontSize: 11,
            color: "var(--text-secondary)",
            marginBottom: 8,
            lineHeight: 1.5,
            maxHeight: 120,
            overflowY: "auto",
          }}
        >
          {job.description_clean.slice(0, 500)}
          {job.description_clean.length > 500 ? "…" : ""}
        </p>
      )}

      {/* Move to state */}
      <select
        style={{
          background: "var(--bg-base)",
          border: "1px solid var(--border)",
          borderRadius: 6,
          color: "var(--text-secondary)",
          padding: "5px 8px",
          fontSize: 11,
          width: "100%",
          cursor: "pointer",
          outline: "none",
        }}
        value={job.application_state}
        onChange={(e) => onStateChange(job, e.target.value as ApplicationState)}
      >
        {ALL_STATES.map((s) => (
          <option key={s} value={s}>{s}</option>
        ))}
      </select>
    </div>
  );
}
