"use client";

import { useEffect, useState } from "react";
import { getAIPrompts, resetAIPrompt, updateAIPrompt, type AIPrompt } from "@/lib/api";

export default function PromptsPage() {
	const [prompts, setPrompts] = useState<AIPrompt[]>([]);
	const [drafts, setDrafts] = useState<Record<string, string>>({});
	const [loading, setLoading] = useState(true);
	const [savingKey, setSavingKey] = useState<string | null>(null);
	const [resettingKey, setResettingKey] = useState<string | null>(null);
	const [error, setError] = useState<string | null>(null);
	const [notice, setNotice] = useState<string | null>(null);

	useEffect(() => {
		let active = true;

		void getAIPrompts()
			.then((items) => {
				if (active) setPrompts(items);
			})
			.catch((reason: unknown) => {
				if (active) setError(reason instanceof Error ? reason.message : String(reason));
			})
			.finally(() => {
				if (active) setLoading(false);
			});

		return () => {
			active = false;
		};
	}, []);

	function updateDraft(key: string, prompt: string) {
		setDrafts((current) => ({ ...current, [key]: prompt }));
		setNotice(null);
	}

	async function savePrompt(item: AIPrompt) {
		setSavingKey(item.key);
		setError(null);
		setNotice(null);
		try {
			const saved = await updateAIPrompt(item.key, drafts[item.key] ?? item.prompt);
			setPrompts((current) => current.map((prompt) => (prompt.key === item.key ? saved : prompt)));
			setDrafts((current) => {
				const next = { ...current };
				delete next[item.key];
				return next;
			});
			setNotice(`${item.name} saved.`);
		} catch (reason) {
			setError(reason instanceof Error ? reason.message : String(reason));
		} finally {
			setSavingKey(null);
		}
	}

	async function resetPrompt(item: AIPrompt) {
		setResettingKey(item.key);
		setError(null);
		setNotice(null);
		try {
			const reset = await resetAIPrompt(item.key);
			setPrompts((current) => current.map((prompt) => (prompt.key === item.key ? reset : prompt)));
			setDrafts((current) => {
				const next = { ...current };
				delete next[item.key];
				return next;
			});
			setNotice(`${item.name} restored to its default.`);
		} catch (reason) {
			setError(reason instanceof Error ? reason.message : String(reason));
		} finally {
			setResettingKey(null);
		}
	}

	return (
		<div className='container' style={{ maxWidth: 1000, paddingTop: 36, paddingBottom: 64 }}>
			<header
				style={{
					marginBottom: 28,
					padding: "24px 28px",
					border: "1px solid var(--accent-border)",
					borderRadius: "var(--radius-lg)",
					background: "linear-gradient(135deg, rgba(79, 70, 229, 0.06), rgba(168, 85, 247, 0.05))",
				}}>
				<span className='badge badge-indigo' style={{ marginBottom: 10 }}>
					AI Configuration
				</span>
				<h1 style={{ marginBottom: 6 }}>AI Prompts</h1>
				<p style={{ color: "var(--text-secondary)", maxWidth: 680 }}>
					Edit the prompts used for job relevance classification. Each prompt is saved independently to the local
					database; you can restore its original text at any time.
				</p>
			</header>

			{error && (
				<div
					role='alert'
					style={{
						marginBottom: 16,
						padding: "12px 16px",
						borderRadius: "var(--radius)",
						background: "var(--red-bg)",
						border: "1px solid var(--red-border)",
						color: "var(--red)",
					}}>
					{error}
				</div>
			)}
			{notice && (
				<div
					role='status'
					style={{
						marginBottom: 16,
						padding: "12px 16px",
						borderRadius: "var(--radius)",
						background: "var(--green-bg)",
						border: "1px solid var(--green-border)",
						color: "var(--green)",
					}}>
					{notice}
				</div>
			)}

			{loading ?
				<p role='status' style={{ color: "var(--text-secondary)" }}>
					Loading AI prompts...
				</p>
			: prompts.length === 0 ?
				<p style={{ color: "var(--text-secondary)" }}>No AI prompts are configured.</p>
			:	<div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
					{prompts.map((item) => {
						const promptText = drafts[item.key] ?? item.prompt;
						const dirty = promptText !== item.prompt;
						const busy = savingKey === item.key || resettingKey === item.key;
						const changed = item.is_customized;
						return (
							<section
								key={item.key}
								style={{
									padding: 24,
									background: "var(--bg-surface)",
									border: "1px solid var(--border)",
									borderRadius: "var(--radius-lg)",
									boxShadow: "var(--shadow-sm)",
								}}>
								<div
									style={{
										display: "flex",
										alignItems: "flex-start",
										justifyContent: "space-between",
										gap: 16,
										marginBottom: 16,
									}}>
									<div>
										<h2 style={{ marginBottom: 4 }}>{item.name}</h2>
										<p style={{ color: "var(--text-secondary)", fontSize: 13 }}>{item.description}</p>
									</div>
									<span className={`badge ${changed ? "badge-amber" : "badge-green"}`}>
										{changed ? "Customized" : "Default"}
									</span>
								</div>

								<label
									htmlFor={`prompt-${item.key}`}
									style={{ display: "block", marginBottom: 8, fontSize: 13, fontWeight: 600 }}>
									Prompt text
								</label>
								<textarea
									id={`prompt-${item.key}`}
									value={promptText}
									onChange={(event) => updateDraft(item.key, event.target.value)}
									spellCheck={false}
									style={{
										display: "block",
										width: "100%",
										minHeight: 300,
										padding: 14,
										border: "1px solid var(--border-strong)",
										borderRadius: "var(--radius)",
										background: "var(--bg-base)",
										color: "var(--text-primary)",
										fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
										fontSize: 13,
										lineHeight: 1.6,
										resize: "vertical",
									}}
								/>
								{item.key === "job_relevance_user" && (
									<p style={{ marginTop: 8, color: "var(--text-muted)", fontSize: 12 }}>
										Keep <code>{"{jobs_json}"}</code> in the template. It is replaced with the jobs being classified.
									</p>
								)}

								<details style={{ marginTop: 14, color: "var(--text-secondary)" }}>
									<summary style={{ cursor: "pointer", fontSize: 12, fontWeight: 600 }}>View original default</summary>
									<pre
										style={{
											marginTop: 10,
											padding: 12,
											overflowX: "auto",
											whiteSpace: "pre-wrap",
											border: "1px solid var(--border)",
											borderRadius: "var(--radius)",
											background: "var(--bg-base)",
											fontSize: 12,
											fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
										}}>
										{item.default_prompt}
									</pre>
								</details>

								<div
									style={{
										display: "flex",
										justifyContent: "flex-end",
										gap: 10,
										marginTop: 18,
									}}>
									<button
										type='button'
										className='btn btn-ghost'
										onClick={() => void resetPrompt(item)}
										disabled={busy || (!changed && !dirty)}>
										{resettingKey === item.key ? "Restoring..." : "Revert to default"}
									</button>
									<button
										type='button'
										className='btn btn-primary'
										onClick={() => void savePrompt(item)}
										disabled={busy || !promptText.trim() || !dirty}>
										{savingKey === item.key ? "Saving..." : "Save prompt"}
									</button>
								</div>
							</section>
						);
					})}
				</div>
			}
		</div>
	);
}
