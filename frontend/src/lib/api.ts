/**
 * Typed API client for the FastAPI backend.
 * All components call through this file — keeps the base URL and
 * error handling in one place.
 */

import type { Job, ApplicationState, Source, ScrapeRun, SearchKeyword, SearchLocation, JobsPage } from "@/types/job";

function getApiBaseUrl(): string {
	if (process.env.NEXT_PUBLIC_API_BASE_URL) {
		return process.env.NEXT_PUBLIC_API_BASE_URL;
	}
	if (typeof window !== "undefined" && window.location) {
		// When running Next.js dev server on port 3000/3001, route API calls to FastAPI on port 8000
		if (window.location.port === "3000" || window.location.port === "3001") {
			return "http://localhost:8000";
		}
		if (window.location.origin) {
			return window.location.origin;
		}
	}
	return "http://localhost:8000";
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
	const baseUrl = getApiBaseUrl();
	const fullUrl = `${baseUrl}${path}`;
	console.log(`[apiFetch] ${init?.method ?? "GET"} ${fullUrl}`);
	try {
		const res = await fetch(fullUrl, {
			headers: { "Content-Type": "application/json", ...init?.headers },
			...init,
		});
		if (!res.ok) {
			const text = await res.text().catch(() => res.statusText);
			console.error(`[apiFetch Error] ${fullUrl} returned ${res.status}: ${text}`);
			throw new Error(`API ${init?.method ?? "GET"} ${path} failed (${res.status}): ${text}`);
		}
		return res.json() as Promise<T>;
	} catch (err) {
		console.error(`[apiFetch Network Error] ${fullUrl}:`, err);
		throw err;
	}
}

// ── Jobs ─────────────────────────────────────────────────────────────

export interface GetJobsParams {
	state?: string;
	source?: string;
	role_match?: string;
	q?: string;
	date_from?: string;
	date_to?: string;
	page?: number;
	page_size?: number;
}

export function getJobs(params?: GetJobsParams): Promise<JobsPage> {
	const qs = new URLSearchParams();
	if (params?.state) qs.set("state", params.state);
	if (params?.source) qs.set("source", params.source);
	if (params?.role_match) qs.set("role_match", params.role_match);
	if (params?.q) qs.set("q", params.q);
	if (params?.date_from) qs.set("date_from", params.date_from);
	if (params?.date_to) qs.set("date_to", params.date_to);
	if (params?.page) qs.set("page", String(params.page));
	if (params?.page_size) qs.set("page_size", String(params.page_size));
	const query = qs.toString() ? `?${qs}` : "";
	return apiFetch<JobsPage>(`/api/jobs${query}`);
}

export function updateJobState(id: number, state: ApplicationState): Promise<Job> {
	return apiFetch<Job>(`/api/jobs/${id}`, {
		method: "PATCH",
		body: JSON.stringify({ application_state: state }),
	});
}

export function removeJob(id: number): Promise<Job> {
	return apiFetch<Job>(`/api/jobs/${id}`, {
		method: "PATCH",
		body: JSON.stringify({ application_state: "REMOVED" }),
	});
}

// ── Sources ───────────────────────────────────────────────────────────

export function getSources(): Promise<Source[]> {
	return apiFetch<Source[]>("/api/sources");
}

export function toggleSource(name: string, enabled: boolean): Promise<Source> {
	return apiFetch<Source>(`/api/sources/${encodeURIComponent(name)}`, {
		method: "PATCH",
		body: JSON.stringify({ enabled }),
	});
}

// ── Scrape ────────────────────────────────────────────────────────────

export function startScrape(sites: string[] | "all"): Promise<{ run_id: number }> {
	return apiFetch<{ run_id: number }>("/api/scrape/run", {
		method: "POST",
		body: JSON.stringify({ sites }),
	}).then((result) => {
		if (typeof window !== "undefined") {
			window.dispatchEvent(new CustomEvent("job-aggregation:started", { detail: { runId: result.run_id } }));
		}
		return result;
	});
}

export function getScrapeStatus(runId: number): Promise<ScrapeRun> {
	return apiFetch<ScrapeRun>(`/api/scrape/status/${runId}`);
}

export function getScrapeRuns(): Promise<ScrapeRun[]> {
	return apiFetch<ScrapeRun[]>("/api/scrape/runs");
}

export function cancelScrape(runId: number): Promise<{ detail: string }> {
	return apiFetch<{ detail: string }>(`/api/scrape/cancel/${runId}`, {
		method: "POST",
	});
}

// ── Keywords (unified — scraping + filtering from one DB table) ────────

export function getSearchKeywords(): Promise<SearchKeyword[]> {
	return apiFetch<SearchKeyword[]>("/api/keywords/search");
}

export function addSearchKeyword(keyword: string): Promise<SearchKeyword> {
	return apiFetch<SearchKeyword>("/api/keywords/search", {
		method: "POST",
		body: JSON.stringify({ keyword }),
	});
}

export function patchSearchKeyword(id: number, patch: { enabled?: boolean; keyword?: string }): Promise<SearchKeyword> {
	return apiFetch<SearchKeyword>(`/api/keywords/search/${id}`, {
		method: "PATCH",
		body: JSON.stringify(patch),
	});
}

export function deleteSearchKeyword(id: number): Promise<{ detail: string }> {
	return apiFetch<{ detail: string }>(`/api/keywords/search/${id}`, {
		method: "DELETE",
	});
}

export function getExcludeKeywords(): Promise<{ exclude: string[] }> {
	return apiFetch<{ exclude: string[] }>("/api/keywords/exclude");
}

export function updateExcludeKeywords(exclude: string[]): Promise<{ exclude: string[] }> {
	return apiFetch<{ exclude: string[] }>("/api/keywords/exclude", {
		method: "PUT",
		body: JSON.stringify({ exclude }),
	});
}

// ── Locations (editable from admin portal) ────────────────────────────

export function getSearchLocations(): Promise<SearchLocation[]> {
	return apiFetch<SearchLocation[]>("/api/keywords/locations");
}

export function addSearchLocation(location: string): Promise<SearchLocation> {
	return apiFetch<SearchLocation>("/api/keywords/locations", {
		method: "POST",
		body: JSON.stringify({ location }),
	});
}

export function patchSearchLocation(
	id: number,
	patch: { enabled?: boolean; location?: string },
): Promise<SearchLocation> {
	return apiFetch<SearchLocation>(`/api/keywords/locations/${id}`, {
		method: "PATCH",
		body: JSON.stringify(patch),
	});
}

export function deleteSearchLocation(id: number): Promise<{ detail: string }> {
	return apiFetch<{ detail: string }>(`/api/keywords/locations/${id}`, {
		method: "DELETE",
	});
}

// ── Settings ─────────────────────────────────────────────────────────

export function getSettingsStatus(): Promise<Record<string, boolean | string>> {
	return apiFetch<Record<string, boolean | string>>("/api/settings/status");
}

export function updateSetting(key: string, value: string): Promise<void> {
	return apiFetch<void>("/api/settings", {
		method: "POST",
		body: JSON.stringify({ key, value }),
	});
}

export interface GeminiModel {
	id: string;
	display_name: string;
}

export function getGeminiModels(apiKey?: string): Promise<GeminiModel[]> {
	return apiFetch<GeminiModel[]>("/api/settings/models", {
		method: "POST",
		body: JSON.stringify({ api_key: apiKey || null }),
	});
}

// ── AI Prompts ───────────────────────────────────────────────────────

export interface AIPrompt {
	key: string;
	name: string;
	description: string;
	default_prompt: string;
	prompt: string;
	is_customized: boolean;
}

export function getAIPrompts(): Promise<AIPrompt[]> {
	return apiFetch<AIPrompt[]>("/api/prompts");
}

export function updateAIPrompt(key: string, prompt: string): Promise<AIPrompt> {
	return apiFetch<AIPrompt>(`/api/prompts/${encodeURIComponent(key)}`, {
		method: "PUT",
		body: JSON.stringify({ prompt }),
	});
}

export function resetAIPrompt(key: string): Promise<AIPrompt> {
	return apiFetch<AIPrompt>(`/api/prompts/${encodeURIComponent(key)}/reset`, {
		method: "POST",
	});
}
