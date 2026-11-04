"use client";

import { useEffect, useState } from "react";
import { getScrapeRuns, getScrapeStatus } from "@/lib/api";
import type { ClassifierResult, ScrapeRun, SiteResult } from "@/types/job";

function isClassifierResult(result: SiteResult | ClassifierResult): result is ClassifierResult {
	return "kept" in result;
}

function getClassifierResult(run: ScrapeRun): ClassifierResult | undefined {
	const result = run.site_results["__classifier__"];
	return result && isClassifierResult(result) ? result : undefined;
}

function isRunActive(run: ScrapeRun | null | undefined): boolean {
	return !!run && (run.status === "RUNNING" || getClassifierResult(run)?.status === "running");
}

function Metric({ label, value, accent }: { label: string; value: number; accent?: string }) {
	return (
		<div
			style={{
				border: "1px solid var(--border)",
				borderRadius: "var(--radius)",
				background: "var(--bg-surface)",
				padding: "14px 16px",
				minWidth: 0,
			}}>
			<div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 6 }}>{label}</div>
			<div style={{ fontSize: 22, lineHeight: 1.2, fontWeight: 800, color: accent ?? "var(--text-primary)" }}>
				{value.toLocaleString()}
			</div>
		</div>
	);
}

export default function LastFetchSummary() {
	const [latestRun, setLatestRun] = useState<ScrapeRun | null>(null);
	const [loadError, setLoadError] = useState<string | null>(null);

	useEffect(() => {
		let mounted = true;
		let pollingRunId: number | null = null;
		let latestRunId: number | null = null;
		let pollTimer: ReturnType<typeof setInterval> | null = null;

		const stopPolling = () => {
			if (pollTimer) clearInterval(pollTimer);
			pollTimer = null;
			pollingRunId = null;
		};

		const syncRun = async (runId: number) => {
			try {
				const run = await getScrapeStatus(runId);
				if (!mounted) return;
				if (latestRunId !== null && runId < latestRunId) return;
				latestRunId = runId;
				setLatestRun(run);
				setLoadError(null);
				if (isRunActive(run)) {
					if (pollingRunId !== runId) {
						stopPolling();
						pollingRunId = runId;
						pollTimer = setInterval(() => void syncRun(runId), 1500);
					}
				} else if (pollingRunId === runId) {
					stopPolling();
				}
			} catch (error) {
				if (!mounted) return;
				console.error("Could not load the latest scrape summary", error);
				setLoadError("Unable to refresh the latest fetch summary.");
			}
		};

		const loadLatestRun = async () => {
			try {
				const runs = await getScrapeRuns();
				if (!mounted) return;
				const latest = runs[0] ?? null;
				if (latestRunId !== null && (!latest || latest.id < latestRunId)) return;
				latestRunId = latest?.id ?? latestRunId;
				setLatestRun(latest);
				setLoadError(null);
				if (latest && isRunActive(latest)) void syncRun(latest.id);
			} catch (error) {
				if (!mounted) return;
				console.error("Could not load scrape history for the latest summary", error);
				setLoadError("Unable to load the latest fetch summary.");
			}
		};

		const handleRunEvent = (event: Event) => {
			const runId = (event as CustomEvent<{ runId: number }>).detail?.runId;
			if (typeof runId === "number") void syncRun(runId);
		};

		window.addEventListener("job-aggregation:started", handleRunEvent);
		window.addEventListener("job-aggregation:refilter-started", handleRunEvent);
		void loadLatestRun();

		return () => {
			mounted = false;
			stopPolling();
			window.removeEventListener("job-aggregation:started", handleRunEvent);
			window.removeEventListener("job-aggregation:refilter-started", handleRunEvent);
		};
	}, []);

	const sourceResults =
		latestRun ?
			Object.values(latestRun.site_results).filter((result): result is SiteResult => !isClassifierResult(result))
		:	[];
	const found = sourceResults.reduce((total, result) => total + result.found, 0);
	const newJobs = sourceResults.reduce((total, result) => total + result.new, 0);
	const duplicates = sourceResults.reduce((total, result) => total + result.duplicates, 0);
	const sourceErrors = sourceResults.filter((result) => Boolean(result.error && result.error !== "disabled")).length;
	const classifierResult = latestRun ? getClassifierResult(latestRun) : undefined;
	const pending = classifierResult?.pending_job_ids?.length ?? 0;
	const statusLabel =
		latestRun?.status === "FAILED" ? "Fetch failed"
		: latestRun?.status === "CANCELLED" ? "Cancelled"
		: classifierResult?.status === "failed" ? "AI filtering failed"
		: isRunActive(latestRun) ?
			classifierResult?.status === "running" ?
				"AI filtering"
			:	"Fetching"
		: latestRun ? "Complete"
		: "No fetches yet";
	const statusColor =
		latestRun?.status === "FAILED" || classifierResult?.status === "failed" ? "var(--red)"
		: isRunActive(latestRun) ? "var(--accent)"
		: latestRun?.status === "CANCELLED" ? "var(--text-muted)"
		: "var(--green)";

	return (
		<section
			aria-label='Last fetch summary'
			style={{
				background: "var(--bg-surface)",
				border: "1px solid var(--border)",
				borderRadius: "var(--radius-lg)",
				padding: "24px",
				boxShadow: "var(--shadow-sm)",
			}}>
			<div
				style={{
					display: "flex",
					alignItems: "flex-start",
					justifyContent: "space-between",
					gap: 16,
					marginBottom: 18,
				}}>
				<div>
					<h2 style={{ fontSize: 16, fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>Last Fetch Summary</h2>
					<p style={{ fontSize: 12, color: "var(--text-muted)", margin: "4px 0 0" }}>
						Persisted results from the most recent fetch, separate from the per-source result list.
					</p>
				</div>
				<span
					style={{
						fontSize: 11,
						fontWeight: 700,
						color: statusColor,
						background: "var(--bg-base)",
						border: "1px solid var(--border)",
						borderRadius: "9999px",
						padding: "5px 10px",
						whiteSpace: "nowrap",
					}}>
					{statusLabel}
				</span>
			</div>

			{loadError && (
				<p role='alert' style={{ color: "var(--red)", fontSize: 12, margin: "0 0 14px" }}>
					{loadError}
				</p>
			)}

			{latestRun ?
				<>
					<div
						style={{
							display: "grid",
							gridTemplateColumns: "repeat(auto-fit, minmax(125px, 1fr))",
							gap: 10,
						}}>
						<Metric label='Listings found' value={found} />
						<Metric label='New jobs' value={newJobs} accent='var(--green)' />
						<Metric label='Duplicates' value={duplicates} />
						<Metric label='AI kept' value={classifierResult?.kept ?? 0} accent='var(--green)' />
						<Metric label='AI filtered out' value={classifierResult?.removed ?? 0} accent='var(--red)' />
						<Metric label='Source errors' value={sourceErrors} accent={sourceErrors ? "var(--red)" : undefined} />
						<Metric label='Awaiting AI retry' value={pending} accent={pending ? "var(--accent)" : undefined} />
					</div>
					<div
						style={{
							display: "flex",
							flexWrap: "wrap",
							gap: "6px 16px",
							marginTop: 14,
							fontSize: 11,
							color: "var(--text-muted)",
						}}>
						<span>
							Run #{latestRun.id} · {new Date(latestRun.finished_at ?? latestRun.started_at).toLocaleString()}
						</span>
						{classifierResult?.error && (
							<span style={{ color: "var(--red)" }}>AI filtering: {classifierResult.error}</span>
						)}
					</div>
				</>
			:	<p style={{ fontSize: 13, color: "var(--text-muted)", margin: 0 }}>
					No fetch results are available yet. Run a fetch to see the summary here.
				</p>
			}
		</section>
	);
}
