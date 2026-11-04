"use client";

import { useEffect, useState } from "react";

/**
 * Parse an ISO datetime string from the backend.
 *
 * If the string has no timezone suffix, it's treated as UTC (the backend
 * already converts all dates to UTC before storage).
 */
function parseBackendDateTime(iso: string): Date {
	return /([zZ]|[+-]\d{2}:?\d{2})$/.test(iso) ? new Date(iso) : new Date(`${iso}Z`);
}

function pluralize(value: number, unit: string): string {
	return `${value} ${unit}${value === 1 ? "" : "s"}`;
}

/**
 * Format an ISO datetime as a relative "X ago" string.
 *
 * Uses the browser's current time so the result updates live.
 * Future dates (e.g. from scrapers that erroneously provide expiry dates)
 * are shown as "in X …" instead of "just now".
 */
export function formatLocalDateTime(iso: string | null): string {
	if (!iso) return "";

	const date = parseBackendDateTime(iso);
	const diffMs = Date.now() - date.getTime();

	// Future dates (shouldn't normally happen after scraper fixes)
	if (diffMs < -60_000) {
		const futureSec = Math.floor(-diffMs / 1000);
		const futureMin = Math.floor(futureSec / 60);
		const futureHr = Math.floor(futureMin / 60);
		const futureDays = Math.floor(futureHr / 24);
		if (futureDays > 0) return `in ${pluralize(futureDays, "day")}`;
		if (futureHr > 0) return `in ${pluralize(futureHr, "hr")}`;
		return `in ${pluralize(futureMin, "min")}`;
	}

	if (diffMs <= 60_000) return "just now";

	const seconds = Math.floor(diffMs / 1000);
	const minutes = Math.floor(seconds / 60);
	if (minutes < 60) return `${pluralize(minutes, "min")} ago`;

	const hours = Math.floor(minutes / 60);
	if (hours < 24) return `${pluralize(hours, "hr")} ago`;

	const days = Math.floor(hours / 24);
	if (days < 7) return `${pluralize(days, "day")} ago`;

	const weeks = Math.floor(days / 7);
	if (weeks < 4) return `${pluralize(weeks, "week")} ago`;

	const months = Math.floor(days / 30);
	if (months < 12) return `${pluralize(months, "month")} ago`;

	const years = Math.floor(days / 365);
	return `${pluralize(years, "year")} ago`;
}

/**
 * React hook that returns a live-updating relative time string.
 *
 * Updates every second for recent times (< 1 hour), every minute for
 * older times, to avoid unnecessary re-renders.
 */
export function useLiveRelativeTime(iso: string | null): string {
	const [value, setValue] = useState(() => formatLocalDateTime(iso));

	useEffect(() => {
		if (!iso) {
			setValue("");
			return;
		}

		const tick = () => setValue(formatLocalDateTime(iso));
		tick();

		// Use a shorter interval for recent posts, longer for old ones
		const date = parseBackendDateTime(iso);
		const ageMs = Date.now() - date.getTime();
		const intervalMs = Math.abs(ageMs) < 3_600_000 ? 1_000 : 60_000;

		const intervalId = window.setInterval(tick, intervalMs);
		return () => window.clearInterval(intervalId);
	}, [iso]);

	return value;
}

/**
 * Format an ISO datetime as a localized date string.
 * Example: "21 Jul 2026"
 */
export function formatLocalDate(iso: string | null): string {
	if (!iso) return "";
	return parseBackendDateTime(iso).toLocaleDateString("en-GB", {
		day: "numeric",
		month: "short",
		year: "numeric",
	});
}

/**
 * Format an ISO datetime as a full localized date + time string.
 * Example: "2026/07/21 - 3:45 PM"
 */
export function formatLocalDateTimeFull(iso: string | null): string {
	if (!iso) return "";
	const date = parseBackendDateTime(iso);
	const y = date.getFullYear();
	const m = String(date.getMonth() + 1).padStart(2, "0");
	const d = String(date.getDate()).padStart(2, "0");
	const time = date.toLocaleTimeString("en-US", {
		hour: "numeric",
		minute: "2-digit",
		hour12: true,
	});
	return `${y}/${m}/${d} - ${time}`;
}

/**
 * Get a date key (YYYY-MM-DD) in the local timezone for grouping/filtering.
 */
export function getLocalDateKey(iso: string | null): string {
	if (!iso) return "";
	const date = parseBackendDateTime(iso);
	const year = String(date.getFullYear());
	const month = String(date.getMonth() + 1).padStart(2, "0");
	const day = String(date.getDate()).padStart(2, "0");
	return `${year}-${month}-${day}`;
}
