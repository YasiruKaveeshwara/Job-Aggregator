"use client";

import { useEffect, useRef } from "react";
import { getScrapeRuns, getScrapeStatus } from "@/lib/api";
import { notifyAggregationComplete } from "@/lib/notifications";
import type { ScrapeRun } from "@/types/job";

export default function ScrapeCompletionNotifications() {
	const activeRunIds = useRef(new Set<number>());
	const locallyStartedRunIds = useRef(new Set<number>());
	const initialized = useRef(false);
	const polling = useRef(false);

	useEffect(() => {
		let mounted = true;

		const handleRunStarted = (event: Event) => {
			const runId = (event as CustomEvent<{ runId: number }>).detail?.runId;
			if (typeof runId === "number") {
				activeRunIds.current.add(runId);
				locallyStartedRunIds.current.add(runId);
			}
		};

		const poll = async () => {
			if (polling.current) return;
			polling.current = true;
			try {
				const handleRun = (run: ScrapeRun) => {
					const wasActive = activeRunIds.current.has(run.id);
					if (run.status === "RUNNING") {
						activeRunIds.current.add(run.id);
					} else if (wasActive) {
						activeRunIds.current.delete(run.id);
						const startedLocally = locallyStartedRunIds.current.delete(run.id);
						if ((initialized.current || startedLocally) && run.status === "COMPLETED") {
							void notifyAggregationComplete(run).catch((error: unknown) => {
								console.error("Could not show aggregation completion notification", error);
							});
						}
					}
				};

				if (!initialized.current) {
					const runs = await getScrapeRuns();
					if (!mounted) return;
					for (const run of runs) handleRun(run);
					initialized.current = true;
				}

				const activeIds = Array.from(activeRunIds.current);
				const activeRuns = await Promise.all(activeIds.map((runId) => getScrapeStatus(runId)));
				if (!mounted) return;
				for (const run of activeRuns) handleRun(run);
			} catch (error) {
				if (mounted) console.error("Could not check aggregation status for notifications", error);
			} finally {
				polling.current = false;
			}
		};

		window.addEventListener("job-aggregation:started", handleRunStarted);
		void poll();
		const intervalId = window.setInterval(() => void poll(), 2500);

		return () => {
			mounted = false;
			window.removeEventListener("job-aggregation:started", handleRunStarted);
			window.clearInterval(intervalId);
		};
	}, []);

	return null;
}
