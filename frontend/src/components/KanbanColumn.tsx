import type { Job, ApplicationState } from "@/types/job";
import JobCard from "./JobCard";

interface KanbanColumnProps {
  state: ApplicationState;
  label: string;
  color: string;
  jobs: Job[];
  onStateChange: (job: Job, newState: ApplicationState) => void;
}

export default function KanbanColumn({ state, label, color, jobs, onStateChange }: KanbanColumnProps) {
  return (
    <div
      style={{
        background: "var(--bg-surface)",
        border: "1px solid var(--border-subtle)",
        borderRadius: 12,
        display: "flex",
        flexDirection: "column",
        minHeight: 300,
        overflow: "hidden",
      }}
    >
      {/* Column header */}
      <div
        style={{
          padding: "12px 14px",
          borderBottom: "1px solid var(--border-subtle)",
          display: "flex",
          alignItems: "center",
          gap: 8,
        }}
      >
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: "50%",
            background: color,
            flexShrink: 0,
          }}
        />
        <span style={{ fontWeight: 600, fontSize: 13, color: "var(--text-primary)" }}>
          {label}
        </span>
        <span
          style={{
            marginLeft: "auto",
            background: "var(--bg-card)",
            border: "1px solid var(--border)",
            borderRadius: 999,
            fontSize: 11,
            fontWeight: 700,
            color: "var(--text-secondary)",
            padding: "1px 7px",
          }}
        >
          {jobs.length}
        </span>
      </div>

      {/* Cards */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "10px 10px 10px",
          display: "flex",
          flexDirection: "column",
          gap: 8,
        }}
      >
        {jobs.length === 0 ? (
          <p
            style={{
              color: "var(--text-muted)",
              fontSize: 12,
              textAlign: "center",
              padding: "24px 0",
            }}
          >
            Empty
          </p>
        ) : (
          jobs.map((job) => (
            <JobCard
              key={job.id}
              job={job}
              onStateChange={onStateChange}
            />
          ))
        )}
      </div>
    </div>
  );
}
