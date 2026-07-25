"use client";

import { useEffect, useState } from "react";
import { getSettingsStatus, updateSetting } from "@/lib/api";

export default function SettingsPanel() {
  const [geminiConfigured, setGeminiConfigured] = useState<boolean | null>(null);
  const [inputValue, setInputValue] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [saving, setSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function refreshStatus() {
    try {
      const status = await getSettingsStatus();
      setGeminiConfigured(status["GEMINI_API_KEY"] ?? false);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  useEffect(() => {
    let active = true;

    void getSettingsStatus()
      .then((status) => {
        if (active) setGeminiConfigured(status["GEMINI_API_KEY"] ?? false);
      })
      .catch((e) => {
        if (active) setError(e instanceof Error ? e.message : String(e));
      });

    return () => {
      active = false;
    };
  }, []);

  async function handleSave() {
    if (!inputValue.trim()) return;
    setSaving(true);
    setError(null);
    setSuccessMessage(null);
    try {
      await updateSetting("GEMINI_API_KEY", inputValue.trim());
      setInputValue("");
      setSuccessMessage("Gemini API Key saved and encrypted successfully.");
      await refreshStatus();
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      style={{
        background: "var(--bg-surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-lg)",
        padding: "24px",
        boxShadow: "var(--shadow-sm)",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          paddingBottom: "16px",
          marginBottom: "20px",
          borderBottom: "1px solid var(--border)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
          <div
            style={{
              width: "42px",
              height: "42px",
              borderRadius: "12px",
              background: "linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 4px 12px rgba(168, 85, 247, 0.25)",
              flexShrink: 0,
            }}
          >
            {/* Gemini Sparkle SVG */}
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
              <path
                d="M12 2C12 7.52285 7.52285 12 2 12C7.52285 12 12 16.4771 12 22C12 16.4771 16.4771 12 22 12C16.4771 12 12 7.52285 12 2Z"
                fill="white"
              />
            </svg>
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <h2 style={{ fontSize: "16px", fontWeight: "700", color: "var(--text-primary)", letterSpacing: "-0.02em" }}>
                Google Gemini AI Integration
              </h2>
            </div>
            <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "2px" }}>
              Powers automated job relevance classification and LLM candidate filtering.
            </p>
          </div>
        </div>

        {/* Status Pill */}
        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
            fontSize: "12px",
            fontWeight: "600",
            padding: "5px 14px",
            borderRadius: "9999px",
            background:
              geminiConfigured === null
                ? "var(--slate-bg)"
                : geminiConfigured
                ? "var(--green-bg)"
                : "var(--amber-bg)",
            color:
              geminiConfigured === null
                ? "var(--text-muted)"
                : geminiConfigured
                ? "var(--green)"
                : "var(--amber)",
            border: `1px solid ${
              geminiConfigured === null
                ? "var(--border)"
                : geminiConfigured
                ? "var(--green-border)"
                : "var(--amber-border)"
            }`,
          }}
        >
          <span
            style={{
              width: "7px",
              height: "7px",
              borderRadius: "50%",
              background:
                geminiConfigured === null
                  ? "var(--text-muted)"
                  : geminiConfigured
                  ? "var(--green)"
                  : "var(--amber)",
              ...(geminiConfigured ? { boxShadow: "0 0 8px var(--green)" } : {}),
            }}
          />
          {geminiConfigured === null
            ? "Checking..."
            : geminiConfigured
            ? "Active & Connected"
            : "Key Required"}
        </span>
      </div>

      {/* Success Banner */}
      {successMessage && (
        <div
          style={{
            marginBottom: "16px",
            padding: "12px 16px",
            borderRadius: "var(--radius)",
            background: "var(--green-bg)",
            border: "1px solid var(--green-border)",
            color: "var(--green)",
            fontSize: "13px",
            fontWeight: "500",
            display: "flex",
            alignItems: "center",
            gap: "8px",
          }}
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M4 8l3 3 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          {successMessage}
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div
          style={{
            marginBottom: "16px",
            padding: "12px 16px",
            borderRadius: "var(--radius)",
            background: "var(--red-bg)",
            border: "1px solid var(--red-border)",
            color: "var(--red)",
            fontSize: "13px",
            fontWeight: "500",
          }}
        >
          {error}
        </div>
      )}

      {/* Form Input Container */}
      <div style={{ maxWidth: "640px" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          <label htmlFor="gemini-key" style={{ fontSize: "13px", fontWeight: "600", color: "var(--text-primary)" }}>
            Gemini API Key
          </label>

          <div style={{ display: "flex", gap: "8px", position: "relative" }}>
            <div style={{ position: "relative", flex: 1 }}>
              <input
                id="gemini-key"
                type={showKey ? "text" : "password"}
                placeholder="Paste API key (AIzaSy...)"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                style={{
                  width: "100%",
                  height: "42px",
                  borderRadius: "var(--radius)",
                  border: "1px solid var(--border-strong)",
                  padding: "0 40px 0 14px",
                  fontSize: "13px",
                  fontFamily: inputValue ? "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" : "inherit",
                  background: "var(--bg-base)",
                  color: "var(--text-primary)",
                  outline: "none",
                  transition: "border 0.15s ease",
                }}
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                title={showKey ? "Hide API key" : "Show API key"}
                style={{
                  position: "absolute",
                  right: "12px",
                  top: "50%",
                  transform: "translateY(-50%)",
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  color: "var(--text-muted)",
                  padding: "4px",
                  display: "flex",
                  alignItems: "center",
                }}
              >
                {showKey ? (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                    <line x1="1" y1="1" x2="23" y2="23" />
                  </svg>
                ) : (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                )}
              </button>
            </div>

            <button
              type="button"
              onClick={handleSave}
              disabled={saving || !inputValue.trim()}
              style={{
                height: "42px",
                padding: "0 22px",
                borderRadius: "var(--radius)",
                background: "var(--accent)",
                color: "#ffffff",
                fontSize: "13px",
                fontWeight: "600",
                border: "none",
                cursor: saving || !inputValue.trim() ? "not-allowed" : "pointer",
                opacity: saving || !inputValue.trim() ? 0.6 : 1,
                display: "flex",
                alignItems: "center",
                gap: "8px",
                boxShadow: "0 2px 6px rgba(79, 70, 229, 0.2)",
                transition: "all 0.15s ease",
              }}
            >
              {saving ? (
                <>
                  <span
                    className="spin"
                    style={{
                      width: "14px",
                      height: "14px",
                      border: "2px solid rgba(255,255,255,0.3)",
                      borderTopColor: "#fff",
                      borderRadius: "50%",
                    }}
                  />
                  Saving...
                </>
              ) : (
                "Save API Key"
              )}
            </button>
          </div>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginTop: "4px",
            }}
          >
            <p style={{ fontSize: "11px", color: "var(--text-muted)" }}>
              Stored locally in database (<code style={{ color: "var(--text-secondary)", background: "var(--bg-hover)", padding: "2px 4px", borderRadius: "4px" }}>jobs.db</code>).
            </p>
            <a
              href="https://aistudio.google.com/app/apikey"
              target="_blank"
              rel="noreferrer"
              style={{
                fontSize: "11px",
                fontWeight: "600",
                color: "var(--accent)",
                textDecoration: "none",
                display: "inline-flex",
                alignItems: "center",
                gap: "4px",
              }}
            >
              Get Gemini API Key
              <svg width="10" height="10" viewBox="0 0 12 12" fill="none">
                <path d="M3.5 2.5h5v5M8.5 2.5L3.5 7.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </a>
          </div>
        </div>
      </div>

      {/* Developer & System Metadata Card */}
      <div
        style={{
          marginTop: "20px",
          padding: "16px 20px",
          background: "rgba(15, 23, 42, 0.03)",
          borderRadius: "var(--radius-lg)",
          border: "1px solid var(--border)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "12px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div
            style={{
              width: "40px",
              height: "40px",
              borderRadius: "10px",
              background: "linear-gradient(135deg, #4f46e5 0%, #06b6d4 100%)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#fff",
              fontWeight: 800,
              fontSize: "14px",
            }}
          >
            YK
          </div>
          <div>
            <div style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-primary)" }}>
              Created & Developed by Yasiru Kaveeshwara
            </div>
            <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "2px" }}>
              Sri Lanka Tech Jobs Aggregation Engine • Contact: <a href="mailto:kaveeshwaray@gmail.com" style={{ color: "var(--accent)", textDecoration: "none", fontWeight: 600 }}>kaveeshwaray@gmail.com</a>
            </div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span style={{ fontSize: "11px", fontWeight: 600, color: "var(--text-secondary)", background: "var(--bg-surface)", padding: "4px 10px", borderRadius: "20px", border: "1px solid var(--border)" }}>
            Version 1.0.1
          </span>
          <a
            href="https://github.com/YasiruKaveeshwara/Job-Aggregator"
            target="_blank"
            rel="noreferrer"
            style={{
              fontSize: "12px",
              fontWeight: 600,
              color: "var(--accent)",
              textDecoration: "none",
              background: "var(--bg-surface)",
              padding: "4px 12px",
              borderRadius: "20px",
              border: "1px solid var(--border)",
            }}
          >
            GitHub Repository ↗
          </a>
        </div>
      </div>
    </div>
  );
}
