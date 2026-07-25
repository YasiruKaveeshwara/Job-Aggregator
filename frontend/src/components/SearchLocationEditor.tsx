"use client";

import { useEffect, useState, useRef } from "react";
import {
  getSearchLocations,
  addSearchLocation,
  patchSearchLocation,
  deleteSearchLocation,
} from "@/lib/api";
import type { SearchLocation } from "@/types/job";

export default function SearchLocationEditor() {
  const [locations, setLocations] = useState<SearchLocation[]>([]);
  const [loading, setLoading] = useState(true);
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [flash, setFlash] = useState<string | null>(null);
  const flashRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const showFlash = (msg: string) => {
    setFlash(msg);
    if (flashRef.current) clearTimeout(flashRef.current);
    flashRef.current = setTimeout(() => setFlash(null), 2500);
  };

  useEffect(() => {
    getSearchLocations()
      .then(setLocations)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, []);

  const handleAdd = async () => {
    const loc = draft.trim().toLowerCase();
    if (!loc) return;
    if (locations.some((l) => l.location === loc)) {
      setError(`"${loc}" already exists`);
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const newLoc = await addSearchLocation(loc);
      setLocations((prev) =>
        [...prev, newLoc].sort((a, b) => a.location.localeCompare(b.location))
      );
      setDraft("");
      showFlash("✓ Location added");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  const handleToggle = async (loc: SearchLocation) => {
    try {
      const updated = await patchSearchLocation(loc.id, { enabled: !loc.enabled });
      setLocations((prev) => prev.map((l) => (l.id === updated.id ? updated : l)));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const handleDelete = async (loc: SearchLocation) => {
    try {
      await deleteSearchLocation(loc.id);
      setLocations((prev) => prev.filter((l) => l.id !== loc.id));
      showFlash("Location removed");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  if (loading) {
    return (
      <div style={{ padding: "24px", color: "var(--text-muted)", fontSize: 13 }} className="loading">
        Loading target locations…
      </div>
    );
  }

  const enabledCount = locations.filter((l) => l.enabled).length;

  return (
    <div
      style={{
        background: "var(--bg-surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-md)",
        padding: "20px",
        boxShadow: "var(--shadow-xs)",
      }}
    >
      {/* Toast Feedback */}
      {(flash || error) && (
        <div
          style={{
            marginBottom: "16px",
            padding: "10px 14px",
            fontSize: "13px",
            borderRadius: "var(--radius)",
            color: error ? "var(--red)" : "var(--green)",
            background: error ? "var(--red-bg)" : "var(--green-bg)",
            border: `1px solid ${error ? "var(--red-border)" : "var(--green-border)"}`,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <span>{error ?? flash}</span>
          {error && (
            <button
              onClick={() => setError(null)}
              style={{ background: "none", border: "none", color: "inherit", cursor: "pointer", fontSize: "16px" }}
            >
              ×
            </button>
          )}
        </div>
      )}

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
        <div>
          <h3 style={{ fontSize: "14px", fontWeight: "700", color: "var(--text-primary)" }}>
            Target Geographic Locations
          </h3>
          <p style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px" }}>
            Used for location filtering across Sri Lankan districts and work types (remote/hybrid).
          </p>
        </div>
        <span
          style={{
            fontSize: "11px",
            fontWeight: "600",
            color: "var(--blue)",
            background: "var(--blue-bg)",
            border: "1px solid var(--blue-border)",
            padding: "4px 10px",
            borderRadius: "9999px",
          }}
        >
          {enabledCount} Active / {locations.length} Total
        </span>
      </div>

      {/* Add Input */}
      <div style={{ display: "flex", gap: "8px", marginBottom: "14px" }}>
        <input
          type="text"
          placeholder="Add location (e.g. colombo, kandy, remote...)"
          value={draft}
          onChange={(e) => {
            setDraft(e.target.value);
            setError(null);
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              handleAdd();
            }
          }}
          style={{
            flex: 1,
            height: "38px",
            background: "var(--bg-base)",
            border: "1px solid var(--border-strong)",
            borderRadius: "var(--radius)",
            padding: "0 12px",
            fontSize: "13px",
            color: "var(--text-primary)",
            outline: "none",
          }}
        />
        <button
          onClick={handleAdd}
          disabled={!draft.trim() || saving}
          style={{
            height: "38px",
            padding: "0 16px",
            borderRadius: "var(--radius)",
            background: "var(--blue)",
            color: "#ffffff",
            fontSize: "13px",
            fontWeight: "600",
            border: "none",
            cursor: !draft.trim() || saving ? "not-allowed" : "pointer",
            opacity: !draft.trim() || saving ? 0.6 : 1,
          }}
        >
          {saving ? "..." : "+ Add Location"}
        </button>
      </div>

      {/* Locations Grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
          gap: "8px",
          maxHeight: "300px",
          overflowY: "auto",
          paddingRight: "4px",
        }}
      >
        {locations.length === 0 && (
          <span style={{ fontSize: 12, color: "var(--text-muted)", fontStyle: "italic" }}>No locations configured.</span>
        )}
        {locations.map((loc) => (
          <div
            key={loc.id}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "8px 12px",
              borderRadius: "var(--radius)",
              background: loc.enabled ? "var(--bg-hover)" : "var(--bg-base)",
              border: `1px solid ${loc.enabled ? "var(--border)" : "var(--border-strong)"}`,
              opacity: loc.enabled ? 1 : 0.5,
              transition: "all 0.15s ease",
            }}
          >
            <span
              style={{
                width: 7,
                height: 7,
                borderRadius: "50%",
                flexShrink: 0,
                background: loc.enabled ? "var(--blue)" : "var(--text-muted)",
              }}
            />
            <span
              style={{
                flex: 1,
                fontSize: 12,
                fontWeight: "600",
                color: loc.enabled ? "var(--text-primary)" : "var(--text-muted)",
                textTransform: "capitalize",
              }}
            >
              {loc.location}
            </span>
            <label className="toggle" style={{ transform: "scale(0.75)", transformOrigin: "right" }}>
              <input type="checkbox" checked={loc.enabled} onChange={() => handleToggle(loc)} />
              <span className="toggle-slider" />
            </label>
            <button
              onClick={() => handleDelete(loc)}
              style={{
                background: "none",
                border: "none",
                color: "var(--text-muted)",
                cursor: "pointer",
                fontSize: 16,
                padding: "0 4px",
              }}
              title={`Delete "${loc.location}"`}
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
