"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import { startScrape, getScrapeStatus, getScrapeRuns, toggleSource, cancelScrape } from "@/lib/api";
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
	const [cancelling, setCancelling] = useState(false);
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
					if (run.status === "COMPLETED" || run.status === "CANCELLED") {
						setRunState("done");
						stopPolling();
						setCancelling(false);
						onRunFinished?.();
					} else if (run.status === "FAILED") {
						setRunState("failed");
						stopPolling();
						setCancelling(false);
						onRunFinished?.();
					}
				} catch {
					setError("Lost connection to backend");
					stopPolling();
				}
			}, 1500);
		},
		[onRunFinished, stopPolling],
	);

	useEffect(() => {
		let cancelled = false;

		getScrapeRuns()
			.then((runs) => {
				if (cancelled) return;

				const merged: Record<string, SiteResult> = {};
				for (let i = runs.length - 1; i >= 0; i--) {
					Object.assign(merged, runs[i].site_results);
				}
				setMergedResults(merged);

				const latest = runs[0] ?? null;
				setCurrentRun(latest);

				if (latest?.status === "RUNNING") {
					setRunState("running");
					startPolling(latest.id);
				} else if (latest?.status === "COMPLETED" || latest?.status === "CANCELLED") {
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
		setCancelling(false);
		try {
			const { run_id } = await startScrape(sites);
			startPolling(run_id);
		} catch (e) {
			setError(e instanceof Error ? e.message : String(e));
			setRunState("failed");
		}
	};

	const handleCancel = async () => {
		if (!currentRun) return;
		setCancelling(true);
		try {
			await cancelScrape(currentRun.id);
		} catch (e) {
			setError(e instanceof Error ? e.message : String(e));
			setCancelling(false);
		}
	};

	const totalNew = currentRun ? Object.values(currentRun.site_results).reduce((s, r) => s + r.new, 0) : 0;
	const lastFetchAt = currentRun?.finished_at ?? currentRun?.started_at ?? null;
	const lastFetchLabel = useLiveRelativeTime(lastFetchAt);

	// Progress calculations
	const progress = currentRun?.progress;
	const totalSites = progress?.total_sites ?? 0;
	const completedSites = progress?.completed_sites ?? 0;
	const currentSite = progress?.current_site ?? null;
	const progressPercent = totalSites > 0 ? Math.round((completedSites / totalSites) * 100) : 0;

	return (
		<div className='card' style={{ padding: 20 }}>
			{/* Action buttons */}
			<div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16, alignItems: "center" }}>
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
					:	"⚡ Fetch All Sources"}
				</button>

				{/* Stop button — only visible when running */}
				{runState === "running" && (
					<button
						className='btn-ghost'
						disabled={cancelling}
						onClick={handleCancel}
						style={{
							fontSize: 12,
							color: "var(--red)",
							borderColor: "var(--red)",
							display: "flex",
							alignItems: "center",
							gap: 5,
						}}>
						{cancelling ? "Stopping…" : "⏹ Stop"}
					</button>
				)}
			</div>

			{/* Progress bar — only visible when running */}
			{runState === "running" && totalSites > 0 && (
				<div style={{ marginBottom: 16 }}>
					{/* Label */}
					<div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6, fontSize: 12 }}>
						<span style={{ color: "var(--text-secondary)" }}>
							{cancelling
								? "Stopping after current site…"
								: currentSite
									? <>Fetching <span style={{ fontWeight: 700, color: "var(--text-primary)" }}>{currentSite}</span></>
									: "Starting…"}
						</span>
						<span style={{ color: "var(--text-muted)" }}>
							{completedSites}/{totalSites} sites ({progressPercent}%)
						</span>
					</div>

					{/* Bar track */}
					<div
						style={{
							width: "100%",
							height: 8,
							borderRadius: 4,
							background: "var(--bg-surface)",
							border: "1px solid var(--border-subtle)",
							overflow: "hidden",
						}}>
						<div
							style={{
								width: `${progressPercent}%`,
								height: "100%",
								borderRadius: 4,
								background: cancelling
									? "var(--red)"
									: "linear-gradient(90deg, var(--accent), var(--accent-light))",
								transition: "width 0.5s ease-out",
							}}
						/>
					</div>

					{/* Completed sites chips */}
					{completedSites > 0 && (
						<div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginTop: 8 }}>
							{(progress?.requested_sites ?? []).map((site) => {
								const isDone = !!currentRun?.site_results[site];
								const isCurrent = site === currentSite;
								return (
									<span
										key={site}
										style={{
											fontSize: 10,
											padding: "2px 8px",
											borderRadius: 10,
											fontWeight: 600,
											background: isDone ? "rgba(34,197,94,0.15)" : isCurrent ? "rgba(99,102,241,0.15)" : "var(--bg-surface)",
											color: isDone ? "var(--green)" : isCurrent ? "var(--accent)" : "var(--text-muted)",
											border: `1px solid ${isDone ? "rgba(34,197,94,0.3)" : isCurrent ? "rgba(99,102,241,0.3)" : "var(--border-subtle)"}`,
											...(isCurrent ? { animation: "pulse 1.5s ease-in-out infinite" } : {}),
										}}>
										{isDone ? "✓ " : isCurrent ? "● " : ""}{site}
									</span>
								);
							})}
						</div>
					)}
				</div>
			)}

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
						{currentRun?.status === "CANCELLED" && (
							<span style={{ marginLeft: 8, fontSize: 11, color: "var(--text-muted)", fontStyle: "italic" }}>
								(stopped early)
							</span>
						)}
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
							: currentRun?.status === "CANCELLED" ?
								`Stopped — ${totalNew} new job${totalNew !== 1 ? "s" : ""} saved`
							:	`Done — ${totalNew} new job${totalNew !== 1 ? "s" : ""} added`}
						</span>
					</div>

					{/* Per-site breakdown */}
					<div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
						{sources.map((src) => {
							const result = mergedResults[src.name];
							const siteResults = currentRun?.site_results || {};
							const isThisRunActive = currentRun?.status === "RUNNING" && (!result || Object.keys(siteResults).includes(src.name) || Object.keys(siteResults).length === 0);
							const isFetchingThisSite = currentRun?.status === "RUNNING" && currentSite === src.name;

							return (
								<SiteRow
									key={src.name}
									source={src}
									result={result}
									color={PLATFORM_COLORS[src.name] ?? "#6b7280"}
									running={currentRun?.status === "RUNNING" && isThisRunActive}
									isFetching={isFetchingThisSite}
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
		: status === "CANCELLED" ? "var(--text-muted)"
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
	isFetching,
	onToggle,
	onRun,
	runState,
}: {
	source: Source;
	result: SiteResult | undefined;
	color: string;
	running: boolean;
	isFetching: boolean;
	onToggle: () => void;
	onRun: () => void;
	runState: string;
}) {
	const done = !!result;
	const relativeTime = useLiveRelativeTime(source.last_scraped_at);

	return (
		<div
			style={{
				background: isFetching ? "rgba(99,102,241,0.04)" : "var(--bg-surface)",
				border: `1px solid ${isFetching ? "rgba(99,102,241,0.3)" : "var(--border-subtle)"}`,
				borderRadius: 8,
				padding: "12px 14px",
				display: "flex",
				alignItems: "center",
				gap: 12,
				transition: "all 0.3s ease",
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
					...(isFetching ? { animation: "pulse 1s ease-in-out infinite" } : {}),
				}}
			/>

			{/* Name & Last Scraped */}
			<div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
				<span style={{ fontSize: 13, fontWeight: 600 }}>
					{source.name}
					{isFetching && (
						<span style={{ marginLeft: 6, fontSize: 10, color: "var(--accent)", fontWeight: 500 }}>
							fetching…
						</span>
					)}
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
