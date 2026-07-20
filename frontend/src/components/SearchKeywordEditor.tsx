"use client";
import { useEffect, useState, useRef } from "react";
import {
  getSearchKeywords,
  addSearchKeyword,
  patchSearchKeyword,
  deleteSearchKeyword,
} from "@/lib/api";
import type { SearchKeyword } from "@/types/job";

export default function SearchKeywordEditor() {
  const [keywords, setKeywords] = useState<SearchKeyword[]>([]);
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
    getSearchKeywords()
      .then(setKeywords)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, []);

  const handleAdd = async () => {
    const kw = draft.trim().toLowerCase();
    if (!kw) return;
    if (keywords.some((k) => k.keyword === kw)) {
      setError(`"${kw}" already exists`);
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const newKw = await addSearchKeyword(kw);
      setKeywords((prev) => [...prev, newKw].sort((a, b) => a.keyword.localeCompare(b.keyword)));
      setDraft("");
      showFlash("✓ Added");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  const handleToggle = async (kw: SearchKeyword) => {
    try {
      const updated = await patchSearchKeyword(kw.id, { enabled: !kw.enabled });
      setKeywords((prev) => prev.map((k) => (k.id === updated.id ? updated : k)));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const handleDelete = async (kw: SearchKeyword) => {
    try {
      await deleteSearchKeyword(kw.id);
      setKeywords((prev) => prev.filter((k) => k.id !== kw.id));
      showFlash("Deleted");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAdd();
    }
  };

  if (loading) {
    return (
      <div className="card loading" style={{ padding: 16, color: "var(--text-muted)", fontSize: 13 }}>
        Loading search keywords…
      </div>
    );
  }

  const enabled = keywords.filter((k) => k.enabled);
  const disabled = keywords.filter((k) => !k.enabled);

  return (
    <div className="card" style={{ padding: 0, overflow: "hidden" }}>
      {/* Header */}
      <div style={{ padding: "14px 16px", borderBottom: "1px solid var(--border-subtle)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
          <span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--accent)", flexShrink: 0 }} />
          <span style={{ fontWeight: 600, fontSize: 13 }}>Search Keywords</span>
          <span style={{ fontSize: 11, color: "var(--text-muted)", marginLeft: "auto" }}>
            {enabled.length} active / {keywords.length} total
          </span>
        </div>
        <p style={{ fontSize: 11, color: "var(--text-muted)", margin: "0 0 0 16px" }}>
          Terms sent to each job board during scraping. Toggle to disable without deleting.
        </p>
      </div>

      {/* Status bar */}
      {(flash || error) && (
        <div style={{
          padding: "7px 16px",
          fontSize: 12,
          borderBottom: "1px solid var(--border-subtle)",
          color: error ? "var(--red)" : "var(--green)",
          background: error ? "#2d0a0a" : "#0a2d0a",
        }}>
          {error ?? flash}
          {error && (
            <button
              onClick={() => setError(null)}
              style={{ marginLeft: 8, background: "none", border: "none", color: "inherit", cursor: "pointer", fontSize: 13 }}
            >
              ×
            </button>
          )}
        </div>
      )}

      {/* Keyword list */}
      <div style={{ padding: "12px 16px", maxHeight: 280, overflowY: "auto" }}>
        {keywords.length === 0 && (
          <span style={{ fontSize: 12, color: "var(--text-muted)", fontStyle: "italic" }}>
            No search keywords yet. Add some below.
          </span>
        )}
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          {keywords.map((kw) => (
            <div
              key={kw.id}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "6px 10px",
                borderRadius: 6,
                background: kw.enabled ? "var(--bg-surface)" : "var(--bg-base)",
                border: "1px solid var(--border-subtle)",
                opacity: kw.enabled ? 1 : 0.5,
                transition: "all 0.2s",
              }}
            >
              {/* Enabled dot */}
              <span style={{
                width: 6, height: 6, borderRadius: "50%", flexShrink: 0,
                background: kw.enabled ? "var(--green)" : "var(--text-muted)",
              }} />

              {/* Keyword text */}
              <span style={{ flex: 1, fontSize: 12, color: kw.enabled ? "var(--text-primary)" : "var(--text-muted)" }}>
                {kw.keyword}
              </span>

              {/* Toggle */}
              <label className="toggle" style={{ transform: "scale(0.8)", transformOrigin: "right" }}>
                <input type="checkbox" checked={kw.enabled} onChange={() => handleToggle(kw)} />
                <span className="toggle-slider" />
              </label>

              {/* Delete */}
              <button
                onClick={() => handleDelete(kw)}
                style={{
                  background: "none", border: "none", color: "var(--text-muted)",
                  cursor: "pointer", fontSize: 15, lineHeight: 1, padding: "0 2px",
                }}
                title={`Delete "${kw.keyword}"`}
                aria-label={`Delete ${kw.keyword}`}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Add input */}
      <div style={{ padding: "12px 16px", borderTop: "1px solid var(--border-subtle)", display: "flex", gap: 6 }}>
        <input
          type="text"
          placeholder="Add search keyword…"
          value={draft}
          onChange={(e) => { setDraft(e.target.value); setError(null); }}
          onKeyDown={handleKeyDown}
          style={{
            flex: 1,
            background: "var(--bg-base)",
            border: "1px solid var(--border)",
            borderRadius: 6,
            padding: "6px 10px",
            fontSize: 12,
            color: "var(--text-primary)",
            outline: "none",
          }}
        />
        <button
          className="btn-ghost"
          onClick={handleAdd}
          disabled={!draft.trim() || saving}
          style={{ fontSize: 12, padding: "6px 12px" }}
        >
          {saving ? "…" : "+ Add"}
        </button>
      </div>
    </div>
  );
}
