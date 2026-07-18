import type { Job, ApplicationState, Source } from "@/types/job";

interface FilterBarProps {
  sources: Source[];
  roleOptions: string[];
  filterState: string;
  filterSource: string;
  filterRole: string;
  filterQ: string;
  onStateChange: (v: string) => void;
  onSourceChange: (v: string) => void;
  onRoleChange: (v: string) => void;
  onQChange: (v: string) => void;
}

const STATES = ["DISCOVERED", "REVIEWING", "APPLIED", "INTERVIEWING", "ARCHIVED"];

export default function FilterBar({
  sources, roleOptions,
  filterState, filterSource, filterRole, filterQ,
  onStateChange, onSourceChange, onRoleChange, onQChange,
}: FilterBarProps) {
  const selectStyle: React.CSSProperties = {
    background: "var(--bg-surface)",
    border: "1px solid var(--border)",
    borderRadius: 8,
    color: "var(--text-primary)",
    padding: "7px 10px",
    fontSize: 13,
    outline: "none",
    cursor: "pointer",
  };

  const hasFilter = filterState || filterSource || filterRole || filterQ;

  return (
    <div
      style={{
        display: "flex",
        gap: 8,
        flexWrap: "wrap",
        marginBottom: 20,
        alignItems: "center",
      }}
    >
      {/* Search */}
      <input
        className="input"
        style={{ maxWidth: 220 }}
        placeholder="🔍  Search title or company…"
        value={filterQ}
        onChange={(e) => onQChange(e.target.value)}
      />

      {/* State */}
      <select style={selectStyle} value={filterState} onChange={(e) => onStateChange(e.target.value)}>
        <option value="">All states</option>
        {STATES.map((s) => (
          <option key={s} value={s}>{s}</option>
        ))}
      </select>

      {/* Source */}
      <select style={selectStyle} value={filterSource} onChange={(e) => onSourceChange(e.target.value)}>
        <option value="">All sources</option>
        {sources.map((s) => (
          <option key={s.name} value={s.name}>{s.name}</option>
        ))}
      </select>

      {/* Role */}
      <select style={selectStyle} value={filterRole} onChange={(e) => onRoleChange(e.target.value)}>
        <option value="">All roles</option>
        {roleOptions.map((r) => (
          <option key={r} value={r}>{r}</option>
        ))}
      </select>

      {/* Clear */}
      {hasFilter && (
        <button
          className="btn-ghost"
          style={{ fontSize: 12 }}
          onClick={() => {
            onStateChange("");
            onSourceChange("");
            onRoleChange("");
            onQChange("");
          }}
        >
          ✕ Clear
        </button>
      )}
    </div>
  );
}
