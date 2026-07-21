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

	const totalNew = currentRun
		? Object.entries(currentRun.site_results)
			.filter(([key]) => key !== "__classifier__")
			.reduce((s, [, r]) => s + ("new" in r ? r.new : 0), 0)
		: 0;
	const classifierResult = currentRun?.site_results["__classifier__"] as { kept: number; removed: number; skipped: number } | undefined;
	const lastFetchAt = currentRun?.finished_at ?? currentRun?.started_at ?? null;
	const lastFetchLabel = useLiveRelativeTime(lastFetchAt);

	// Progress calculations
	const progress = currentRun?.progress;
	const totalSites = progress?.total_sites ?? 0;
	const completedSites = progress?.completed_sites ?? 0;
	const currentSite = progress?.current_site ?? null;
	const isClassifying = progress?.classifying ?? false;
	const classifyingCount = progress?.classifying_count ?? 0;
	const progressPercent = totalSites > 0 ? Math.round((completedSites / totalSites) * 100) : 0;

	return (
		<div style={{ padding: 0 }}>
			{/* Action buttons */}
			<div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16, alignItems: "center" }}>
				<button
					className='btn btn-primary'
					disabled={runState === "running"}
					onClick={() => handleStart("all")}>
					{runState === "running" ? (
						<>
							<span
								className='spin'
								style={{
									display: "inline-block",
									width: 13,
									height: 13,
									border: "2px solid rgba(255,255,255,0.3)",
									borderTopColor: "#fff",
									borderRadius: "50%",
								}}
							/>
							Running
						</>
					) : (
						<>
							<svg width="14" height="14" viewBox="0 0 14 14" fill="none">
								<polygon points="2,2 12,7 2,12" fill="currentColor" />
							</svg>
							Fetch All Sources
						</>
					)}
				</button>

				{/* Stop button — only visible when running */}
				{runState === "running" && (
					<button
						className='btn btn-danger'
						disabled={cancelling}
						onClick={handleCancel}>
						<svg width="12" height="12" viewBox="0 0 12 12" fill="none">
							<rect x="2" y="2" width="8" height="8" rx="1" fill="currentColor" />
						</svg>
						{cancelling ? "Stopping..." : "Stop"}
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
							? "Stopping after current site..."
							: isClassifying
								? <><span style={{ color: "var(--accent)", fontWeight: 600 }}>Classifying {classifyingCount} jobs with AI...</span></>
								: currentSite
									? <>Fetching <span style={{ fontWeight: 700, color: "var(--text-primary)" }}>{currentSite}</span></>
									: "Starting..."}
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
							border: "1px solid var(--border)",
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
											background: isDone ? "var(--green-bg)" : isCurrent ? "var(--accent-dim)" : "var(--bg-base)",
											color: isDone ? "var(--green)" : isCurrent ? "var(--accent)" : "var(--text-muted)",
											border: `1px solid ${isDone ? "var(--green-border)" : isCurrent ? "var(--accent-border)" : "var(--border)"}`,
											...(isCurrent ? { animation: "pulse 1.5s ease-in-out infinite" } : {}),
										}}>
										{site}
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
						background: "var(--red-bg)",
						border: "1px solid var(--red-border)",
						borderRadius: "var(--radius)",
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
					<div style={{ marginBottom: 12 }}>
						<span
							style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 500 }}>
							Latest fetch results
						</span>
					</div>
					<div style={{ marginBottom: 12, fontSize: 12, color: "var(--text-secondary)" }}>
						Last fetch:{" "}
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
							marginBottom: 14,
						}}>
						<StatusDot status={currentRun?.status || "COMPLETED"} />
						<span style={{ fontSize: 13, fontWeight: 600 }}>
							{currentRun?.status === "RUNNING" ?
								"Scraping in progress..."
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

						{/* AI Classifier result row */}
						{classifierResult && (
							<div style={{
								display: "flex",
								alignItems: "center",
								gap: 8,
								padding: "10px 12px",
								borderRadius: "var(--radius)",
								background: "var(--accent-dim)",
								border: "1px solid var(--accent-border)",
								marginTop: 6,
							}}>
								<svg width="14" height="14" viewBox="0 0 14 14" fill="none" style={{ flexShrink: 0 }}>
									<circle cx="7" cy="7" r="6" stroke="var(--accent)" strokeWidth="1.25" />
									<path d="M4.5 7l2 2 3-4" stroke="var(--accent)" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round" />
								</svg>
								<span style={{ fontSize: 12, fontWeight: 600, color: "var(--accent)", flex: 1 }}>
									AI Relevance Filter
								</span>
								<span style={{ fontSize: 11, color: "var(--text-secondary)" }}>
									<span style={{ color: "var(--green)", fontWeight: 600 }}>{classifierResult.kept} kept</span>
									{" · "}
									<span style={{ color: "var(--red)", fontWeight: 600 }}>{classifierResult.removed} removed</span>
									{classifierResult.skipped > 0 && ` · ${classifierResult.skipped} unclassified`}
								</span>
							</div>
						)}
					</div>
				</div>
			)}

			{runState === "idle" && !currentRun && (
				<p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>Click Fetch All Sources to start pulling jobs from your configured platforms.</p>
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
				background: isFetching ? "var(--accent-dim)" : "var(--bg-base)",
				border: `1px solid ${isFetching ? "var(--accent-border)" : "var(--border)"}`,
				borderRadius: "var(--radius)",
				padding: "12px 14px",
				display: "flex",
				alignItems: "center",
				gap: 12,
				transition: "all 0.25s ease",
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
			<div style={{ display: "flex", alignItems: "center", gap: 10, paddingLeft: 12, borderLeft: "1px solid var(--border)" }}>
				<button
					className='btn btn-ghost btn-icon btn-sm'
					disabled={runState === "running" || !source.enabled}
					onClick={onRun}
					title={`Fetch ${source.name}`}>
					<svg width="13" height="13" viewBox="0 0 13 13" fill="none">
						<path d="M11 6.5A4.5 4.5 0 1 1 6.5 2" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" />
						<path d="M6.5 2l2-2M6.5 2l2 2" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round" />
					</svg>
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
