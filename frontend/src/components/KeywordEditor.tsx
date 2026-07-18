"use client";
import { useEffect, useState, useRef } from "react";
import { getKeywords, updateKeywords } from "@/lib/api";
import type { KeywordConfig } from "@/types/job";

type Section = "include" | "intern_modifiers" | "exclude";

const SECTION_META: Record<Section, { label: string; desc: string; color: string }> = {
  include: {
    label: "Include Keywords",
    desc: "Job titles matching any of these are kept.",
    color: "var(--green)",
  },
  intern_modifiers: {
    label: "Intern Modifiers",
    desc: "Combined with include keywords for intern roles.",
    color: "var(--accent)",
  },
  exclude: {
    label: "Exclude Keywords",
    desc: "Titles matching these are always discarded.",
    color: "var(--red)",
  },
};

export default function KeywordEditor() {
  const [config, setConfig] = useState<KeywordConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<Record<Section, string>>({
    include: "",
    intern_modifiers: "",
    exclude: "",
  });
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    getKeywords()
      .then((c) => setConfig(c))
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, []);

  const handleAdd = (section: Section) => {
    const value = drafts[section].trim().toLowerCase();
    if (!value || !config) return;
    if (config[section].includes(value)) return; // already exists

    const updated = { ...config, [section]: [...config[section], value] };
    setConfig(updated);
    setDrafts((d) => ({ ...d, [section]: "" }));
    save(updated);
  };

  const handleRemove = (section: Section, keyword: string) => {
    if (!config) return;
    const updated = {
      ...config,
      [section]: config[section].filter((k) => k !== keyword),
    };
    setConfig(updated);
    save(updated);
  };

  const handleKeyDown = (e: React.KeyboardEvent, section: Section) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAdd(section);
    }
  };

  const save = async (cfg: KeywordConfig) => {
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      const result = await updateKeywords(cfg);
      setConfig(result);
      setSaved(true);
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      timeoutRef.current = setTimeout(() => setSaved(false), 2000);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div
        className="card loading"
        style={{ padding: 16, color: "var(--text-muted)", fontSize: 13 }}
      >
        Loading keyword config…
      </div>
    );
  }

  if (error && !config) {
    return (
      <div
        className="card"
        style={{ padding: 16, color: "var(--red)", fontSize: 13 }}
      >
        Failed to load keywords: {error}
      </div>
    );
  }

  if (!config) return null;

  return (
    <div className="card" style={{ padding: 0, overflow: "hidden" }}>
      {/* Save indicator */}
      {(saving || saved || error) && (
        <div
          style={{
            padding: "8px 16px",
            fontSize: 12,
            borderBottom: "1px solid var(--border-subtle)",
            color: error ? "var(--red)" : saved ? "var(--green)" : "var(--text-muted)",
            background: error ? "#2d0a0a" : saved ? "#0a2d0a" : "transparent",
          }}
        >
          {saving ? "Saving…" : saved ? "✓ Saved" : error ? `Error: ${error}` : ""}
        </div>
      )}

      {(["include", "intern_modifiers", "exclude"] as Section[]).map((section, i) => {
        const meta = SECTION_META[section];
        const keywords = config[section];
        return (
          <div
            key={section}
            style={{
              padding: "14px 16px",
              borderBottom:
                i < 2 ? "1px solid var(--border-subtle)" : "none",
            }}
          >
            {/* Section header */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                marginBottom: 6,
              }}
            >
              <span
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  background: meta.color,
                  flexShrink: 0,
                }}
              />
              <span style={{ fontWeight: 600, fontSize: 13 }}>{meta.label}</span>
              <span
                style={{
                  fontSize: 11,
                  color: "var(--text-muted)",
                  marginLeft: "auto",
                }}
              >
                {keywords.length}
              </span>
            </div>
            <p
              style={{
                fontSize: 11,
                color: "var(--text-muted)",
                margin: "0 0 10px 16px",
              }}
            >
              {meta.desc}
            </p>

            {/* Tags */}
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: 6,
                marginBottom: 10,
                minHeight: 28,
              }}
            >
              {keywords.length === 0 && (
                <span
                  style={{
                    fontSize: 12,
                    color: "var(--text-muted)",
                    fontStyle: "italic",
                  }}
                >
                  No keywords configured
                </span>
              )}
              {keywords.map((kw) => (
                <span
                  key={kw}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 4,
                    background: "var(--bg-card)",
                    border: "1px solid var(--border)",
                    borderRadius: 6,
                    padding: "3px 8px",
                    fontSize: 12,
                    color: "var(--text-primary)",
                  }}
                >
                  {kw}
                  <button
                    onClick={() => handleRemove(section, kw)}
                    style={{
                      background: "none",
                      border: "none",
                      color: "var(--text-muted)",
                      cursor: "pointer",
                      padding: 0,
                      fontSize: 14,
                      lineHeight: 1,
                    }}
                    title={`Remove "${kw}"`}
                    aria-label={`Remove ${kw}`}
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>

            {/* Add input */}
            <div style={{ display: "flex", gap: 6 }}>
              <input
                type="text"
                placeholder="Add keyword…"
                value={drafts[section]}
                onChange={(e) =>
                  setDrafts((d) => ({ ...d, [section]: e.target.value }))
                }
                onKeyDown={(e) => handleKeyDown(e, section)}
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
                onClick={() => handleAdd(section)}
                style={{ fontSize: 12, padding: "6px 12px" }}
                disabled={!drafts[section].trim()}
              >
                + Add
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
