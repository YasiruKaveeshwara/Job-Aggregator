"use client";
import type { Source } from "@/types/job";

interface FilterBarProps {
  sources: Source[];
  roleOptions: string[];
  filterState: string;
  filterSource: string;
  filterRole: string;
  filterQ: string;
  filterDateFrom: string;
  filterDateTo: string;
  onStateChange: (v: string) => void;
  onSourceChange: (v: string) => void;
  onRoleChange: (v: string) => void;
  onQChange: (v: string) => void;
  onDateFromChange: (v: string) => void;
  onDateToChange: (v: string) => void;
}

const STATES = [
  { value: "",        label: "All statuses" },
  { value: "NEW",     label: "New" },
  { value: "APPLIED", label: "Applied" },
  { value: "REMOVED", label: "Removed" },
];

function SearchIcon() {
  return (
    <svg
      width="15"
      height="15"
      viewBox="0 0 15 15"
      fill="none"
      style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", pointerEvents: "none" }}
    >
      <circle cx="6.5" cy="6.5" r="4.5" stroke="var(--text-muted)" strokeWidth="1.25" />
      <path d="M10 10l3 3" stroke="var(--text-muted)" strokeWidth="1.25" strokeLinecap="round" />
    </svg>
  );
}

export default function FilterBar({
  sources, roleOptions,
  filterState, filterSource, filterRole, filterQ, filterDateFrom, filterDateTo,
  onStateChange, onSourceChange, onRoleChange, onQChange, onDateFromChange, onDateToChange,
}: FilterBarProps) {
  const hasFilter = filterState || filterSource || filterRole || filterQ || filterDateFrom || filterDateTo;

  const selectStyle: React.CSSProperties = {
    background: "var(--bg-surface)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius)",
    color: "var(--text-primary)",
    padding: "8px 10px",
    fontSize: 13,
    fontFamily: "inherit",
    outline: "none",
    cursor: "pointer",
    boxShadow: "var(--shadow-xs)",
    height: 36,
    transition: "border-color 0.15s, box-shadow 0.15s",
  };

  return (
    <div
      style={{
        background: "var(--bg-surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-md)",
        padding: "14px 16px",
        marginBottom: 20,
        boxShadow: "var(--shadow-sm)",
      }}
    >
      <div
        style={{
          display: "flex",
          gap: 10,
          flexWrap: "wrap",
          alignItems: "center",
        }}
      >
        {/* Search */}
        <div style={{ position: "relative", flex: "1 1 200px", minWidth: 180, maxWidth: 280 }}>
          <SearchIcon />
          <input
            className="input"
            style={{ paddingLeft: 32, height: 36, fontSize: 13 }}
            placeholder="Search title or company..."
            value={filterQ}
            onChange={(e) => onQChange(e.target.value)}
          />
        </div>

        {/* Status */}
        <select
          style={{ ...selectStyle, minWidth: 140 }}
          value={filterState}
          onChange={(e) => onStateChange(e.target.value)}
          onFocus={(e) => { (e.target as HTMLSelectElement).style.borderColor = "var(--border-focus)"; (e.target as HTMLSelectElement).style.boxShadow = "0 0 0 3px rgba(79,70,229,0.08)"; }}
          onBlur={(e) => { (e.target as HTMLSelectElement).style.borderColor = "var(--border)"; (e.target as HTMLSelectElement).style.boxShadow = "var(--shadow-xs)"; }}
        >
          {STATES.map((s) => (
            <option key={s.value} value={s.value}>{s.label}</option>
          ))}
        </select>

        {/* Source */}
        <select
          style={{ ...selectStyle, minWidth: 140 }}
          value={filterSource}
          onChange={(e) => onSourceChange(e.target.value)}
          onFocus={(e) => { (e.target as HTMLSelectElement).style.borderColor = "var(--border-focus)"; (e.target as HTMLSelectElement).style.boxShadow = "0 0 0 3px rgba(79,70,229,0.08)"; }}
          onBlur={(e) => { (e.target as HTMLSelectElement).style.borderColor = "var(--border)"; (e.target as HTMLSelectElement).style.boxShadow = "var(--shadow-xs)"; }}
        >
          <option value="">All sources</option>
          {sources.map((s) => (
            <option key={s.name} value={s.name}>{s.name}</option>
          ))}
        </select>

        {/* Role */}
        {roleOptions.length > 0 && (
          <select
            style={{ ...selectStyle, minWidth: 150 }}
            value={filterRole}
            onChange={(e) => onRoleChange(e.target.value)}
            onFocus={(e) => { (e.target as HTMLSelectElement).style.borderColor = "var(--border-focus)"; (e.target as HTMLSelectElement).style.boxShadow = "0 0 0 3px rgba(79,70,229,0.08)"; }}
            onBlur={(e) => { (e.target as HTMLSelectElement).style.borderColor = "var(--border)"; (e.target as HTMLSelectElement).style.boxShadow = "var(--shadow-xs)"; }}
          >
            <option value="">All roles</option>
            {roleOptions.map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
        )}

        {/* Date From */}
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ fontSize: 12, color: "var(--text-muted)", fontWeight: 500, whiteSpace: "nowrap" }}>
            From
          </span>
          <input
            type="date"
            style={{ ...selectStyle, width: "auto" }}
            value={filterDateFrom}
            onChange={(e) => onDateFromChange(e.target.value)}
          />
        </div>

        {/* Date To */}
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ fontSize: 12, color: "var(--text-muted)", fontWeight: 500, whiteSpace: "nowrap" }}>
            To
          </span>
          <input
            type="date"
            style={{ ...selectStyle, width: "auto" }}
            value={filterDateTo}
            onChange={(e) => onDateToChange(e.target.value)}
          />
        </div>

        {/* Clear filters */}
        {hasFilter && (
          <button
            className="btn btn-ghost btn-sm"
            onClick={() => {
              onStateChange("");
              onSourceChange("");
              onRoleChange("");
              onQChange("");
              onDateFromChange("");
              onDateToChange("");
            }}
          >
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <path d="M1 1l10 10M11 1L1 11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
            Clear filters
          </button>
        )}
      </div>
    </div>
  );
}
