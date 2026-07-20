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
    flashRef.current = setTimeout(() => setFlash(null), 2000);
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

  // ── Keyword (include) handlers ───────────────────────────────────
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

  // ── Exclude handlers ──────────────────────────────────────────────
  const handleAddExclude = async () => {
    const kw = excludeDraft.trim().toLowerCase();
    if (!kw || excludes.includes(kw)) return;
    const next = [...excludes, kw];
    setExcludes(next);
    setExcludeDraft("");
    try {
      await updateExcludeKeywords(next);
      showFlash("✓ Saved");
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
      <div className="card loading" style={{ padding: 16, color: "var(--text-muted)", fontSize: 13 }}>
        Loading keywords…
      </div>
    );
  }

  const enabled = keywords.filter((k) => k.enabled).length;

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

      {/* ── Include keywords ── */}
      <div style={{ padding: "14px 16px", borderBottom: "1px solid var(--border-subtle)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
          <span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--green)", flexShrink: 0 }} />
          <span style={{ fontWeight: 600, fontSize: 13 }}>Keywords</span>
          <span style={{ fontSize: 11, color: "var(--text-muted)", marginLeft: "auto" }}>
            {enabled} active / {keywords.length} total
          </span>
        </div>
        <p style={{ fontSize: 11, color: "var(--text-muted)", margin: "0 0 10px 16px" }}>
          Used for both <strong>scraping</strong> (search terms sent to job boards) and <strong>filtering</strong> (job titles must match one of these).
          Toggle to disable without deleting.
        </p>

        {/* Keyword list */}
        <div style={{ maxHeight: 260, overflowY: "auto", display: "flex", flexDirection: "column", gap: 4, marginBottom: 10 }}>
          {keywords.length === 0 && (
            <span style={{ fontSize: 12, color: "var(--text-muted)", fontStyle: "italic" }}>No keywords yet.</span>
          )}
          {keywords.map((kw) => (
            <div key={kw.id} style={{
              display: "flex", alignItems: "center", gap: 8,
              padding: "5px 10px", borderRadius: 6,
              background: kw.enabled ? "var(--bg-surface)" : "var(--bg-base)",
              border: "1px solid var(--border-subtle)",
              opacity: kw.enabled ? 1 : 0.5, transition: "all 0.15s",
            }}>
              <span style={{
                width: 6, height: 6, borderRadius: "50%", flexShrink: 0,
                background: kw.enabled ? "var(--green)" : "var(--text-muted)",
              }} />
              <span style={{ flex: 1, fontSize: 12, color: kw.enabled ? "var(--text-primary)" : "var(--text-muted)" }}>
                {kw.keyword}
              </span>
              <label className="toggle" style={{ transform: "scale(0.78)", transformOrigin: "right" }}>
                <input type="checkbox" checked={kw.enabled} onChange={() => handleToggle(kw)} />
                <span className="toggle-slider" />
              </label>
              <button onClick={() => handleDelete(kw)}
                style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", fontSize: 15, lineHeight: 1, padding: "0 2px" }}
                title={`Delete "${kw.keyword}"`}>×</button>
            </div>
          ))}
        </div>

        {/* Add input */}
        <div style={{ display: "flex", gap: 6 }}>
          <input type="text" placeholder="Add keyword…" value={draft}
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

      {/* ── Exclude keywords ── */}
      <div style={{ padding: "14px 16px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
          <span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--red)", flexShrink: 0 }} />
          <span style={{ fontWeight: 600, fontSize: 13 }}>Exclude Keywords</span>
          <span style={{ fontSize: 11, color: "var(--text-muted)", marginLeft: "auto" }}>{excludes.length}</span>
        </div>
        <p style={{ fontSize: 11, color: "var(--text-muted)", margin: "0 0 10px 16px" }}>
          Titles matching these are always discarded, even if they match a keyword above.
        </p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 10, minHeight: 28 }}>
          {excludes.length === 0 && (
            <span style={{ fontSize: 12, color: "var(--text-muted)", fontStyle: "italic" }}>No exclusions configured</span>
          )}
          {excludes.map((kw) => (
            <span key={kw} style={{
              display: "inline-flex", alignItems: "center", gap: 4,
              background: "#2d0a0a", border: "1px solid #5a1a1a", borderRadius: 6,
              padding: "3px 8px", fontSize: 12, color: "var(--red)",
            }}>
              {kw}
              <button onClick={() => handleRemoveExclude(kw)}
                style={{ background: "none", border: "none", color: "inherit", cursor: "pointer", padding: 0, fontSize: 14, lineHeight: 1 }}
                title={`Remove "${kw}"`}>×</button>
            </span>
          ))}
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          <input type="text" placeholder="Add exclude keyword…" value={excludeDraft}
            onChange={(e) => setExcludeDraft(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); handleAddExclude(); } }}
            style={{ flex: 1, background: "var(--bg-base)", border: "1px solid var(--border)", borderRadius: 6, padding: "6px 10px", fontSize: 12, color: "var(--text-primary)", outline: "none" }}
          />
          <button className="btn-ghost" onClick={handleAddExclude} disabled={!excludeDraft.trim()}
            style={{ fontSize: 12, padding: "6px 12px" }}>
            + Add
          </button>
        </div>
      </div>
    </div>
  );
}
