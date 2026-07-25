"use client";

import { useEffect, useState } from "react";
import { getSettingsStatus, updateSetting } from "@/lib/api";

export default function SettingsPanel() {
  const [geminiConfigured, setGeminiConfigured] = useState<boolean | null>(null);
  const [inputValue, setInputValue] = useState("");
  const [saving, setSaving] = useState(false);
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
    try {
      await updateSetting("GEMINI_API_KEY", inputValue.trim());
      setInputValue(""); // never leave the typed value sitting in the input after saving
      await refreshStatus();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-6 shadow-sm">
      <div className="mb-4 flex items-center justify-between border-b border-slate-100 pb-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Application Settings</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Configure runtime credentials and local secrets.
          </p>
        </div>
      </div>

      {error && (
        <div className="mb-4 rounded-md bg-red-50 p-3 text-xs text-red-700 border border-red-200">
          {error}
        </div>
      )}

      <div className="space-y-4 max-w-xl">
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between">
            <label htmlFor="gemini-key" className="text-sm font-medium text-slate-700">
              Gemini API Key
            </label>
            <span
              className={`text-xs font-semibold px-2 py-0.5 rounded ${
                geminiConfigured === null
                  ? "bg-slate-100 text-slate-600"
                  : geminiConfigured
                  ? "bg-emerald-100 text-emerald-700"
                  : "bg-amber-100 text-amber-700"
              }`}
            >
              {geminiConfigured === null
                ? "Checking..."
                : geminiConfigured
                ? "✓ Configured"
                : "Not set"}
            </span>
          </div>

          <div className="flex gap-2">
            <input
              id="gemini-key"
              type="password"
              placeholder="Paste your Gemini API key"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-900 focus:outline-none"
            />
            <button
              onClick={handleSave}
              disabled={saving || !inputValue.trim()}
              className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50 transition-colors"
            >
              {saving ? "Saving..." : "Save"}
            </button>
          </div>
          <p className="text-xs text-slate-500">
            Used by Gemini AI for job filtering. Overrides environment variables when saved.
          </p>
        </div>
      </div>
    </div>
  );
}
