"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import { startScrape, getScrapeStatus, getScrapeRuns, toggleSource } from "@/lib/api";
import { useLiveRelativeTime } from "@/lib/datetime";
import type { Source, ScrapeRun, SiteResult } from "@/types/job";

interface Props {
	sources: Source[];
	onSourcesChange?: (sources: Source[]) => void;
	onRunFinished?: () => void;
}

type RunState = "idle" | "running" | "done" | "failed";

const PLATFORM_COLORS: Record<string, string> = {
	"itpro.lk": "#6366f1",
	"anyjobok.com": "#22c55e",
	"governmentjob.lk": "#f59e0b",
	"jobenvoy.com": "#a855f7",
	"rooster.jobs": "#06b6d4",
	"topjobs.lk": "#ef4444",
	"xpress.jobs": "#64748b",
	"findmyjob.lk": "#10b981",
	"hire.lk": "#3b82f6",
};

export default function ScrapeControlPanel({ sources, onSourcesChange, onRunFinished }: Props) {
	const [runState, setRunState] = useState<RunState>("idle");
	const [currentRun, setCurrentRun] = useState<ScrapeRun | null>(null);
	const [mergedResults, setMergedResults] = useState<Record<string, SiteResult>>({});
	const [error, setError] = useState<string | null>(null);
	const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

	const stopPolling = useCallback(() => {
		if (pollRef.current) {
			clearInterval(pollRef.current);
			pollRef.current = null;
		}
	}, []);

	useEffect(() => () => stopPolling(), [stopPolling]);

	const startPolling = useCallback(
		(runId: number) => {
			stopPolling();
			pollRef.current = setInterval(async () => {
				try {
					const run = await getScrapeStatus(runId);
					setCurrentRun(run);
					if (run.site_results) {
						setMergedResults((prev) => ({ ...prev, ...run.site_results }));
					}
					if (run.status === "COMPLETED") {
						setRunState("done");
						stopPolling();
						onRunFinished?.();
					} else if (run.status === "FAILED") {
						setRunState("failed");
						stopPolling();
						onRunFinished?.();
					}
				} catch {
					setError("Lost connection to backend");
					stopPolling();
				}
			}, 2000);
		},
		[onRunFinished, stopPolling],
	);

	useEffect(() => {
		let cancelled = false;

		getScrapeRuns()
			.then((runs) => {
				if (cancelled) return;

				const merged: Record<string, SiteResult> = {};
				// Runs are newest-first. Iterate oldest-first to overwrite with newer results.
				for (let i = runs.length - 1; i >= 0; i--) {
					Object.assign(merged, runs[i].site_results);
				}
				setMergedResults(merged);

				const latest = runs[0] ?? null;
				setCurrentRun(latest);

				if (latest?.status === "RUNNING") {
					setRunState("running");
					startPolling(latest.id);
				} else if (latest?.status === "COMPLETED") {
					setRunState("done");
				} else if (latest?.status === "FAILED") {
					setRunState("failed");
				}
			})
			.catch(() => {
				if (!cancelled) {
					setCurrentRun(null);
				}
			});

		return () => {
			cancelled = true;
		};
	}, [startPolling]);

	const handleStart = async (sites: string[] | "all") => {
		setError(null);
		setRunState("running");
		try {
			const { run_id } = await startScrape(sites);
			startPolling(run_id);
		} catch (e) {
			setError(e instanceof Error ? e.message : String(e));
			setRunState("failed");
		}
	};

	const totalNew = currentRun ? Object.values(currentRun.site_results).reduce((s, r) => s + r.new, 0) : 0;
	const lastFetchAt = currentRun?.finished_at ?? currentRun?.started_at ?? null;
	const lastFetchLabel = useLiveRelativeTime(lastFetchAt);

	return (
		<div className='card' style={{ padding: 20 }}>
			{/* Action buttons */}
			<div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 20 }}>
				<button
					className='btn-primary'
					disabled={runState === "running"}
					onClick={() => handleStart("all")}
					style={{ display: "flex", alignItems: "center", gap: 6 }}>
					{runState === "running" ?
						<>
							<span
								className='spin'
								style={{
									display: "inline-block",
									width: 12,
									height: 12,
									border: "2px solid rgba(255,255,255,0.3)",
									borderTopColor: "#fff",
									borderRadius: "50%",
								}}
							/>
							Running…
						</>
					:	"⚡ Start Fetching (All Sources)"}
				</button>
			</div>

			{/* Error */}
			{error && (
				<div
					style={{
						background: "#2d0a0a",
						border: "1px solid var(--red)",
						borderRadius: 8,
						padding: "10px 14px",
						fontSize: 13,
						color: "var(--red)",
						marginBottom: 12,
					}}>
					{error}
				</div>
			)}

			{/* Status */}
			{(currentRun || Object.keys(mergedResults).length > 0) && (
				<div>
					<div style={{ marginBottom: 10 }}>
						<span
							style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
							Latest fetch results
						</span>
					</div>
					<div style={{ marginBottom: 10, fontSize: 12, color: "var(--text-secondary)" }}>
						Last all fetch:{" "}
						<span style={{ fontWeight: 600, color: "var(--text-primary)" }}>{lastFetchLabel || "—"}</span>
					</div>
					<div
						style={{
							display: "flex",
							alignItems: "center",
							gap: 8,
							marginBottom: 12,
						}}>
						<StatusDot status={currentRun?.status || "COMPLETED"} />
						<span style={{ fontSize: 13, fontWeight: 600 }}>
							{currentRun?.status === "RUNNING" ?
								"Scraping in progress…"
							: currentRun?.status === "FAILED" ?
								"Run failed"
							:	`Done — ${totalNew} new job${totalNew !== 1 ? "s" : ""} added`}
						</span>
					</div>

					{/* Per-site breakdown */}
					<div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
						{sources.map((src) => {
							const result = mergedResults[src.name];
							// If a run is running and doesn't have a result for this site yet,
							// but the site is part of the requested ones, we want to show it as "waiting".
							// Since we don't have the explicit site list for the run, we use the fact that
							// if it's running, we consider all enabled sites as running unless we want to be precise.
							// But actually, just showing the last merged result is fine.
							const siteResults = currentRun?.site_results || {};
							const isThisRunActive = currentRun?.status === "RUNNING" && (!result || Object.keys(siteResults).includes(src.name) || Object.keys(siteResults).length === 0);
							
							return (
								<SiteRow
									key={src.name}
									source={src}
									result={result}
									color={PLATFORM_COLORS[src.name] ?? "#6b7280"}
									running={currentRun?.status === "RUNNING" && isThisRunActive}
									onToggle={async () => {
										const updated = await toggleSource(src.name, !src.enabled);
										onSourcesChange?.(sources.map((s) => (s.id === updated.id ? updated : s)));
									}}
									onRun={() => handleStart([src.name])}
									runState={runState}
								/>
							);
						})}
					</div>
				</div>
			)}

			{runState === "idle" && (
				<p style={{ fontSize: 12, color: "var(--text-muted)" }}>Click a button above to start fetching jobs.</p>
			)}
		</div>
	);
}

function StatusDot({ status }: { status: string }) {
	const color =
		status === "COMPLETED" ? "var(--green)"
		: status === "FAILED" ? "var(--red)"
		: "var(--accent-light)";
	return (
		<span
			style={{
				width: 8,
				height: 8,
				borderRadius: "50%",
				background: color,
				display: "inline-block",
				flexShrink: 0,
				...(status === "RUNNING" ? { animation: "pulse 1s ease-in-out infinite" } : {}),
			}}
		/>
	);
}

function SiteRow({
	source,
	result,
	color,
	running,
	onToggle,
	onRun,
	runState,
}: {
	source: Source;
	result: SiteResult | undefined;
	color: string;
	running: boolean;
	onToggle: () => void;
	onRun: () => void;
	runState: string;
}) {
	const done = !!result;
	const relativeTime = useLiveRelativeTime(source.last_scraped_at);

	return (
		<div
			style={{
				background: "var(--bg-surface)",
				border: "1px solid var(--border-subtle)",
				borderRadius: 8,
				padding: "12px 14px",
				display: "flex",
				alignItems: "center",
				gap: 12,
			}}>
			{/* Dot */}
			<span
				style={{
					width: 8,
					height: 8,
					borderRadius: "50%",
					background: !source.enabled ? "var(--text-muted)" : (done ? (result?.error ? "var(--red)" : "var(--green)") : color),
					flexShrink: 0,
					opacity: (done || !source.enabled) ? 1 : 0.5,
				}}
			/>

			{/* Name & Last Scraped */}
			<div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
				<span style={{ fontSize: 13, fontWeight: 600 }}>
					{source.name}
				</span>
				<span style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>
					{source.last_scraped_at ? `Last fetched ${new Date(source.last_scraped_at).toLocaleDateString()} (${relativeTime})` : "Never fetched"}
				</span>
			</div>

			{/* Counts / Status */}
			<div style={{ minWidth: 140, display: "flex", justifyContent: "flex-end" }}>
				{done && !result?.error ?
					<div style={{ display: "flex", gap: 10, fontSize: 12 }}>
						<Stat label='found' value={result!.found} />
						<Stat label='new' value={result!.new} highlight />
						<Stat label='dup' value={result!.duplicates} />
					</div>
				: done && result?.error ?
					<span style={{ fontSize: 12, color: "var(--red)" }}>{result.error}</span>
				: running ?
					<span style={{ fontSize: 12, color: "var(--text-muted)" }} className='loading'>
						Waiting…
					</span>
				:	null}
			</div>

			{/* Actions (Toggle & Run) */}
			<div style={{ display: "flex", alignItems: "center", gap: 12, paddingLeft: 12, borderLeft: "1px solid var(--border-subtle)" }}>
				<button
					className='btn-ghost'
					disabled={runState === "running" || !source.enabled}
					onClick={onRun}
					style={{ fontSize: 12, padding: "4px 8px" }}>
					↻
				</button>
				<label className='toggle'>
					<input type='checkbox' checked={source.enabled} onChange={onToggle} disabled={runState === "running"} />
					<span className='toggle-slider' />
				</label>
			</div>
		</div>
	);
}

function Stat({ label, value, highlight }: { label: string; value: number; highlight?: boolean }) {
	return (
		<span>
			<span style={{ color: "var(--text-muted)" }}>{label} </span>
			<span
				style={{
					fontWeight: 700,
					color: highlight && value > 0 ? "var(--green)" : "var(--text-primary)",
				}}>
				{value}
			</span>
		</span>
	);
}
