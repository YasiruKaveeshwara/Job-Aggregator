"use client";

import type { ScrapeRun } from "@/types/job";

interface DesktopNotificationAPI {
	notify_aggregation_complete(newJobs: number, sourceCount: number): Promise<void>;
	send_test_notification(): Promise<void>;
}

declare global {
	interface Window {
		pywebview?: {
			api?: DesktopNotificationAPI;
		};
	}
}

export function getDesktopNotificationAPI(): DesktopNotificationAPI | undefined {
	return typeof window === "undefined" ? undefined : window.pywebview?.api;
}

export async function notifyAggregationComplete(run: ScrapeRun): Promise<void> {
	const sourceResults = Object.entries(run.site_results).filter(([key]) => key !== "__classifier__");
	const newJobs = sourceResults.reduce((total, [, result]) => {
		return total + ("new" in result && typeof result.new === "number" ? result.new : 0);
	}, 0);
	const desktopAPI = getDesktopNotificationAPI();

	if (desktopAPI) {
		await desktopAPI.notify_aggregation_complete(newJobs, sourceResults.length);
		return;
	}

	if (
		typeof window !== "undefined" &&
		window.isSecureContext &&
		"Notification" in window &&
		Notification.permission === "granted"
	) {
		const jobLabel = newJobs === 1 ? "job" : "jobs";
		const sourceLabel = sourceResults.length === 1 ? "source" : "sources";
		new Notification("Job aggregation complete", {
			body: `Found ${newJobs} new ${jobLabel} from ${sourceResults.length} ${sourceLabel}.`,
		});
	}
}
