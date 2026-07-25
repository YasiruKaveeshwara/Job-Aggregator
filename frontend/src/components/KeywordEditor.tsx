"use client";

import { useEffect, useState, useRef } from "react";
import {
  getSearchKeywords,
  addSearchKeyword,
  patchSearchKeyword,
  deleteSearchKeyword,
  getExcludeKeywords,
  updateExcludeKeywords,
} from "@/lib/api";
import type { SearchKeyword } from "@/types/job";

export default function KeywordEditor() {
  const [keywords, setKeywords] = useState<SearchKeyword[]>([]);
  const [excludes, setExcludes] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [draft, setDraft] = useState("");
  const [excludeDraft, setExcludeDraft] = useState("");
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
    Promise.all([getSearchKeywords(), getExcludeKeywords()])
      .then(([kws, excl]) => {
        setKeywords(kws);
        setExcludes(excl.exclude);
      })
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
      setKeywords((prev) =>
        [...prev, newKw].sort((a, b) => a.keyword.localeCompare(b.keyword))
      );
      setDraft("");
      showFlash("✓ Keyword added successfully");
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
      showFlash("Keyword removed");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const handleAddExclude = async () => {
    const kw = excludeDraft.trim().toLowerCase();
    if (!kw || excludes.includes(kw)) return;
    const next = [...excludes, kw];
    setExcludes(next);
    setExcludeDraft("");
    try {
      await updateExcludeKeywords(next);
      showFlash("✓ Exclusion saved");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const handleRemoveExclude = async (kw: string) => {
    const next = excludes.filter((e) => e !== kw);
    setExcludes(next);
    try {
      await updateExcludeKeywords(next);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  if (loading) {
    return (
      <div style={{ padding: "24px", color: "var(--text-muted)", fontSize: 13 }} className="loading">
        Loading target keywords…
      </div>
    );
  }

  const enabledCount = keywords.filter((k) => k.enabled).length;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Toast Feedback */}
      {(flash || error) && (
        <div
          style={{
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

      {/* Target Search Keywords */}
      <div
        style={{
          background: "var(--bg-surface)",
          border: "1px solid var(--border)",
          borderRadius: "var(--radius-md)",
          padding: "20px",
          boxShadow: "var(--shadow-xs)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
          <div>
            <h3 style={{ fontSize: "14px", fontWeight: "700", color: "var(--text-primary)" }}>
              Target Job Title Keywords
            </h3>
            <p style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px" }}>
              Sent to Sri Lankan job sites during scraping and used for role matching.
            </p>
          </div>
          <span
            style={{
              fontSize: "11px",
              fontWeight: "600",
              color: "var(--green)",
              background: "var(--green-bg)",
              border: "1px solid var(--green-border)",
              padding: "4px 10px",
              borderRadius: "9999px",
            }}
          >
            {enabledCount} Active / {keywords.length} Total
          </span>
        </div>

        {/* Add Input */}
        <div style={{ display: "flex", gap: "8px", marginBottom: "14px" }}>
          <input
            type="text"
            placeholder="Add new target keyword (e.g. react developer, devops...)"
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
              background: "var(--accent)",
              color: "#ffffff",
              fontSize: "13px",
              fontWeight: "600",
              border: "none",
              cursor: !draft.trim() || saving ? "not-allowed" : "pointer",
              opacity: !draft.trim() || saving ? 0.6 : 1,
            }}
          >
            {saving ? "..." : "+ Add Keyword"}
          </button>
        </div>

        {/* Keywords Grid */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
            gap: "8px",
            maxHeight: "280px",
            overflowY: "auto",
            paddingRight: "4px",
          }}
        >
          {keywords.length === 0 && (
            <span style={{ fontSize: 12, color: "var(--text-muted)", fontStyle: "italic" }}>No keywords configured.</span>
          )}
          {keywords.map((kw) => (
            <div
              key={kw.id}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                padding: "8px 12px",
                borderRadius: "var(--radius)",
                background: kw.enabled ? "var(--bg-hover)" : "var(--bg-base)",
                border: `1px solid ${kw.enabled ? "var(--border)" : "var(--border-strong)"}`,
                opacity: kw.enabled ? 1 : 0.5,
                transition: "all 0.15s ease",
              }}
            >
              <span
                style={{
                  width: 7,
                  height: 7,
                  borderRadius: "50%",
                  flexShrink: 0,
                  background: kw.enabled ? "var(--green)" : "var(--text-muted)",
                }}
              />
              <span style={{ flex: 1, fontSize: 12, fontWeight: "600", color: kw.enabled ? "var(--text-primary)" : "var(--text-muted)" }}>
                {kw.keyword}
              </span>
              <label className="toggle" style={{ transform: "scale(0.75)", transformOrigin: "right" }}>
                <input type="checkbox" checked={kw.enabled} onChange={() => handleToggle(kw)} />
                <span className="toggle-slider" />
              </label>
              <button
                onClick={() => handleDelete(kw)}
                style={{
                  background: "none",
                  border: "none",
                  color: "var(--text-muted)",
                  cursor: "pointer",
                  fontSize: 16,
                  padding: "0 4px",
                }}
                title={`Delete "${kw.keyword}"`}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Excluded Negative Keywords */}
      <div
        style={{
          background: "var(--bg-surface)",
          border: "1px solid var(--border)",
          borderRadius: "var(--radius-md)",
          padding: "20px",
          boxShadow: "var(--shadow-xs)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
          <div>
            <h3 style={{ fontSize: "14px", fontWeight: "700", color: "var(--red)" }}>
              Excluded Negative Keywords
            </h3>
            <p style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px" }}>
              Listings matching any of these terms are automatically discarded.
            </p>
          </div>
          <span
            style={{
              fontSize: "11px",
              fontWeight: "600",
              color: "var(--red)",
              background: "var(--red-bg)",
              border: "1px solid var(--red-border)",
              padding: "4px 10px",
              borderRadius: "9999px",
            }}
          >
            {excludes.length} Exclusions
          </span>
        </div>

        {/* Add Exclude Input */}
        <div style={{ display: "flex", gap: "8px", marginBottom: "14px" }}>
          <input
            type="text"
            placeholder="Add exclusion keyword (e.g. intern, sales, marketing...)"
            value={excludeDraft}
            onChange={(e) => setExcludeDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                handleAddExclude();
              }
            }}
            style={{
              flex: 1,
              height: "38px",
              background: "var(--bg-base)",
              border: "1px solid var(--red-border)",
              borderRadius: "var(--radius)",
              padding: "0 12px",
              fontSize: "13px",
              color: "var(--text-primary)",
              outline: "none",
            }}
          />
          <button
            onClick={handleAddExclude}
            disabled={!excludeDraft.trim()}
            style={{
              height: "38px",
              padding: "0 16px",
              borderRadius: "var(--radius)",
              background: "var(--red)",
              color: "#ffffff",
              fontSize: "13px",
              fontWeight: "600",
              border: "none",
              cursor: !excludeDraft.trim() ? "not-allowed" : "pointer",
              opacity: !excludeDraft.trim() ? 0.6 : 1,
            }}
          >
            + Add Exclusion
          </button>
        </div>

        {/* Exclusion Badges */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", minHeight: "36px" }}>
          {excludes.length === 0 && (
            <span style={{ fontSize: 12, color: "var(--text-muted)", fontStyle: "italic" }}>No negative exclusions configured.</span>
          )}
          {excludes.map((kw) => (
            <span
              key={kw}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                background: "var(--red-bg)",
                border: "1px solid var(--red-border)",
                borderRadius: "9999px",
                padding: "4px 12px",
                fontSize: "12px",
                fontWeight: "600",
                color: "var(--red)",
              }}
            >
              {kw}
              <button
                onClick={() => handleRemoveExclude(kw)}
                style={{
                  background: "none",
                  border: "none",
                  color: "inherit",
                  cursor: "pointer",
                  padding: 0,
                  fontSize: 14,
                  lineHeight: 1,
                }}
                title={`Remove "${kw}"`}
              >
                ×
              </button>
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
