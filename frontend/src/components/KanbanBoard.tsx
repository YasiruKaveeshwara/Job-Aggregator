import type { Job, ApplicationState } from "@/types/job";
import KanbanColumn from "./KanbanColumn";

const COLUMNS: { state: ApplicationState; label: string; color: string }[] = [
  { state: "DISCOVERED",   label: "Discovered",   color: "#6366f1" },
  { state: "REVIEWING",    label: "Reviewing",    color: "#f59e0b" },
  { state: "APPLIED",      label: "Applied",      color: "#06b6d4" },
  { state: "INTERVIEWING", label: "Interviewing", color: "#a855f7" },
  { state: "ARCHIVED",     label: "Archived",     color: "#6b7280" },
];

interface KanbanBoardProps {
  jobs: Job[];
  onStateChange: (job: Job, newState: ApplicationState) => void;
}

export default function KanbanBoard({ jobs, onStateChange }: KanbanBoardProps) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(5, minmax(240px, 1fr))",
        gap: 12,
        overflowX: "auto",
        paddingBottom: 16,
      }}
    >
      {COLUMNS.map(({ state, label, color }) => (
        <KanbanColumn
          key={state}
          state={state}
          label={label}
          color={color}
          jobs={jobs.filter((j) => j.application_state === state)}
          onStateChange={onStateChange}
        />
      ))}
    </div>
  );
}
