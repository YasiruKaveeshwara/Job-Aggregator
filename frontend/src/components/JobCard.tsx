"use client";
import { useState } from "react";
import type { Job, ApplicationState } from "@/types/job";
import { useLiveRelativeTime, formatLocalDateTimeFull } from "@/lib/datetime";

interface JobCardProps {
  job: Job;
  onStateChange: (job: Job, newState: ApplicationState) => void;
  onRemove: (job: Job) => void;
}

function RelativeTime({ iso }: { iso: string | null }) {
  const label = useLiveRelativeTime(iso);
  return (
    <span
      title={iso ? `Posted: ${formatLocalDateTimeFull(iso)}` : undefined}
      style={{ fontSize: 12, color: "var(--text-muted)", whiteSpace: "nowrap" }}
    >
      {label}
    </span>
  );
}

const PLATFORM_BADGE: Record<string, string> = {
  "itpro.lk":         "badge-indigo",
  "anyjobok.com":     "badge-green",
  "governmentjob.lk": "badge-amber",
  "jobenvoy.com":     "badge-purple",
  "rooster.jobs":     "badge-cyan",
  "topjobs.lk":       "badge-red",
  "xpress.jobs":      "badge-neutral",
  "findmyjob.lk":     "badge-blue",
  "hire.lk":          "badge-indigo",
};

function CompanyAvatar({ name, imageUrl }: { name: string; imageUrl?: string | null }) {
  const [imgError, setImgError] = useState(false);
  const initials = name
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("");

  const hue = name.split("").reduce((acc, c) => acc + c.charCodeAt(0), 0) % 360;

  return (
    <div
      style={{
        width: 52,
        height: 52,
        flexShrink: 0,
        borderRadius: "var(--radius)",
        border: "1px solid var(--border)",
        background: `hsl(${hue}, 60%, 96%)`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        overflow: "hidden",
        position: "relative",
      }}
    >
      {imageUrl && !imgError ? (
        <img
          src={imageUrl}
          alt={name}
          onError={() => setImgError(true)}
          style={{ width: "100%", height: "100%", objectFit: "contain", padding: 4 }}
        />
      ) : (
        <span
          style={{
            fontSize: 15,
            fontWeight: 700,
            color: `hsl(${hue}, 50%, 40%)`,
            letterSpacing: "-0.02em",
          }}
        >
          {initials || "J"}
        </span>
      )}
    </div>
  );
}

export default function JobCard({ job, onStateChange, onRemove }: JobCardProps) {
  const [expanded, setExpanded] = useState(false);
  const isRemoved = job.application_state === "REMOVED";
  const isApplied = job.application_state === "APPLIED";

  return (
    <article
      className="card card-interactive fade-in"
      style={{
        padding: "18px 20px",
        display: "flex",
        gap: 16,
        alignItems: "flex-start",
        opacity: isRemoved ? 0.55 : 1,
        transition: "opacity 0.2s ease, box-shadow 0.18s ease, border-color 0.18s ease, transform 0.18s ease",
      }}
    >
      {/* Avatar */}
      <CompanyAvatar name={job.company_name} imageUrl={job.image_url} />

      {/* Main Content */}
      <div style={{ flex: 1, minWidth: 0 }}>

        {/* Title row */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            gap: 12,
            marginBottom: 4,
          }}
        >
          <h3
            style={{
              fontSize: 15,
              fontWeight: 600,
              color: "var(--text-primary)",
              lineHeight: 1.35,
              letterSpacing: "-0.01em",
            }}
          >
            {job.job_title}
          </h3>
          <RelativeTime iso={job.posted_date ?? null} />
        </div>

        {/* Company & location */}
        <p
          style={{
            fontSize: 13,
            color: "var(--text-secondary)",
            marginBottom: 10,
            display: "flex",
            alignItems: "center",
            gap: 6,
            flexWrap: "wrap",
          }}
        >
          <span style={{ fontWeight: 500 }}>{job.company_name}</span>
          {job.location_normalized && (
            <>
              <span style={{ color: "var(--border-strong)" }}>·</span>
              <span style={{ color: "var(--text-muted)" }}>
                {job.location_normalized}
              </span>
            </>
          )}
        </p>

        {/* Badges */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 12 }}>
          {/* Role match */}
          <span className="badge badge-indigo">{job.role_match}</span>

          {/* Salary */}
          {job.salary_disclosed && job.salary_min != null && (
            <span className="badge badge-green">
              LKR {job.salary_min.toLocaleString()}
              {job.salary_max && job.salary_max !== job.salary_min
                ? ` – ${job.salary_max.toLocaleString()}`
                : ""}
            </span>
          )}

          {/* Source links */}
          {job.sources.map((s) => (
            <a
              key={s.id}
              href={s.url}
              target="_blank"
              rel="noopener noreferrer"
              className={`badge ${PLATFORM_BADGE[s.platform] ?? "badge-neutral"}`}
              style={{ textDecoration: "none", cursor: "pointer" }}
            >
              {s.platform}
            </a>
          ))}

          {/* Application state indicator */}
          {isApplied && (
            <span className="badge badge-state-applied">Applied</span>
          )}
          {isRemoved && (
            <span className="badge badge-state-removed">Removed</span>
          )}
        </div>

        {/* Description toggle */}
        {job.description_clean && (
          <div>
            <button
              className="btn btn-ghost btn-sm"
              style={{ marginBottom: expanded ? 10 : 0 }}
              onClick={() => setExpanded(!expanded)}
            >
              {expanded ? "Hide description" : "View description"}
              <svg
                width="12"
                height="12"
                viewBox="0 0 12 12"
                fill="none"
                style={{
                  transition: "transform 0.2s",
                  transform: expanded ? "rotate(180deg)" : "rotate(0deg)",
                }}
              >
                <path d="M2 4l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>

            {expanded && (
              <div
                style={{
                  fontSize: 13,
                  color: "var(--text-secondary)",
                  lineHeight: 1.7,
                  maxHeight: 220,
                  overflowY: "auto",
                  padding: "12px 14px",
                  background: "var(--bg-base)",
                  borderRadius: "var(--radius)",
                  border: "1px solid var(--border)",
                }}
              >
                {job.description_clean}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Action buttons */}
      <div
        style={{
          flexShrink: 0,
          display: "flex",
          flexDirection: "column",
          gap: 8,
          alignItems: "stretch",
          minWidth: 108,
        }}
      >
        {isRemoved ? (
          <button
            className="btn btn-ghost btn-sm"
            onClick={() => onStateChange(job, "NEW")}
            style={{ width: "100%", justifyContent: "center" }}
          >
            Restore
          </button>
        ) : (
          <button
            className={`btn btn-sm ${isApplied ? "btn-success" : "btn-primary"}`}
            onClick={() => onStateChange(job, isApplied ? "NEW" : "APPLIED")}
            style={{ width: "100%", justifyContent: "center" }}
          >
            {isApplied ? "Applied" : "Mark Applied"}
          </button>
        )}

        {!isRemoved && (
          <button
            className="btn btn-danger btn-sm"
            onClick={() => onRemove(job)}
            style={{ width: "100%", justifyContent: "center" }}
          >
            Remove
          </button>
        )}
      </div>
    </article>
  );
}
