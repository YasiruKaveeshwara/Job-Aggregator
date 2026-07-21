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
    flashRef.current = setTimeout(() => setFlash(null), 2000);
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
      showFlash("✓ Added");
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
      showFlash("Deleted");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  if (loading) {
    return (
      <div className="card loading" style={{ padding: 16, color: "var(--text-muted)", fontSize: 13 }}>
        Loading locations…
      </div>
    );
  }

  const enabled = locations.filter((l) => l.enabled).length;

  return (
    <div className="card" style={{ padding: 0, overflow: "hidden" }}>
      {/* Status bar */}
      {(flash || error) && (
        <div style={{
          padding: "7px 16px", fontSize: 12,
          borderBottom: "1px solid var(--border-subtle)",
          color: error ? "var(--red)" : "var(--green)",
          background: error ? "#2d0a0a" : "#0a2d0a",
          display: "flex", alignItems: "center", gap: 8,
        }}>
          <span style={{ flex: 1 }}>{error ?? flash}</span>
          {error && (
            <button onClick={() => setError(null)}
              style={{ background: "none", border: "none", color: "inherit", cursor: "pointer", fontSize: 15 }}>
              ×
            </button>
          )}
        </div>
      )}

      <div style={{ padding: "14px 16px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
          <span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--blue)", flexShrink: 0 }} />
          <span style={{ fontWeight: 600, fontSize: 13 }}>Locations</span>
          <span style={{ fontSize: 11, color: "var(--text-muted)", marginLeft: "auto" }}>
            {enabled} active / {locations.length} total
          </span>
        </div>
        <p style={{ fontSize: 11, color: "var(--text-muted)", margin: "0 0 10px 16px" }}>
          Used by <strong>rooster.jobs</strong> for location filtering.
          Includes all 25 Sri Lankan districts + work-type modifiers.
          Toggle to disable without deleting.
        </p>

        {/* Location list */}
        <div style={{ maxHeight: 300, overflowY: "auto", display: "flex", flexDirection: "column", gap: 4, marginBottom: 10 }}>
          {locations.length === 0 && (
            <span style={{ fontSize: 12, color: "var(--text-muted)", fontStyle: "italic" }}>No locations configured.</span>
          )}
          {locations.map((loc) => (
            <div key={loc.id} style={{
              display: "flex", alignItems: "center", gap: 8,
              padding: "5px 10px", borderRadius: 6,
              background: loc.enabled ? "var(--bg-surface)" : "var(--bg-base)",
              border: "1px solid var(--border-subtle)",
              opacity: loc.enabled ? 1 : 0.5, transition: "all 0.15s",
            }}>
              <span style={{
                width: 6, height: 6, borderRadius: "50%", flexShrink: 0,
                background: loc.enabled ? "var(--blue)" : "var(--text-muted)",
              }} />
              <span style={{ flex: 1, fontSize: 12, color: loc.enabled ? "var(--text-primary)" : "var(--text-muted)", textTransform: "capitalize" }}>
                {loc.location}
              </span>
              <label className="toggle" style={{ transform: "scale(0.78)", transformOrigin: "right" }}>
                <input type="checkbox" checked={loc.enabled} onChange={() => handleToggle(loc)} />
                <span className="toggle-slider" />
              </label>
              <button onClick={() => handleDelete(loc)}
                style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", fontSize: 15, lineHeight: 1, padding: "0 2px" }}
                title={`Delete "${loc.location}"`}>×</button>
            </div>
          ))}
        </div>

        {/* Add input */}
        <div style={{ display: "flex", gap: 6 }}>
          <input type="text" placeholder="Add location…" value={draft}
            onChange={(e) => { setDraft(e.target.value); setError(null); }}
            onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); handleAdd(); } }}
            style={{ flex: 1, background: "var(--bg-base)", border: "1px solid var(--border)", borderRadius: 6, padding: "6px 10px", fontSize: 12, color: "var(--text-primary)", outline: "none" }}
          />
          <button className="btn-ghost" onClick={handleAdd} disabled={!draft.trim() || saving}
            style={{ fontSize: 12, padding: "6px 12px" }}>
            {saving ? "…" : "+ Add"}
          </button>
        </div>
      </div>
    </div>
  );
}
