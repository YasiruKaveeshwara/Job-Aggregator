"use client";
import { useState, useEffect, useCallback, useRef } from "react";
import { getJobs, updateJobState, removeJob, getSources } from "@/lib/api";
import { useLiveRelativeTime } from "@/lib/datetime";
import type { Job, ApplicationState, Source } from "@/types/job";
import JobCard from "@/components/JobCard";
import FilterBar from "@/components/FilterBar";

const PAGE_SIZE = 30;

export default function DashboardPage() {
	const [jobs, setJobs] = useState<Job[]>([]);
	const [sources, setSources] = useState<Source[]>([]);
	const [total, setTotal] = useState(0);
	const [totalPages, setTotalPages] = useState(1);
	const [page, setPage] = useState(1);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	const [filterState, setFilterState] = useState("");
	const [filterSource, setFilterSource] = useState("");
	const [filterRole, setFilterRole] = useState("");
	const [filterQ, setFilterQ] = useState("");
	const [filterDateFrom, setFilterDateFrom] = useState("");
	const [filterDateTo, setFilterDateTo] = useState("");

	// Debounce search to avoid hammering the API on every keystroke
	const [debouncedQ, setDebouncedQ] = useState("");
	const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
	const handleQChange = (v: string) => {
		setFilterQ(v);
		if (debounceRef.current) clearTimeout(debounceRef.current);
		debounceRef.current = setTimeout(() => setDebouncedQ(v), 300);
	};

	// Unique role matches for the filter dropdown — comes from loaded jobs
	const [roleOptions, setRoleOptions] = useState<string[]>([]);

	const loadJobs = useCallback(async (pg: number) => {
		setLoading(true);
		setError(null);
		try {
			const [pageData, srcData] = await Promise.all([
				getJobs({
					state: filterState || undefined,
					source: filterSource || undefined,
					role_match: filterRole || undefined,
					q: debouncedQ || undefined,
					date_from: filterDateFrom || undefined,
					date_to: filterDateTo || undefined,
					page: pg,
					page_size: PAGE_SIZE,
				}),
				getSources(),
			]);
			setJobs(pageData.jobs);
			setTotal(pageData.total);
			setTotalPages(pageData.total_pages);
			setSources(srcData);

			// Build role options from the full result set (first page only, good enough)
			if (pg === 1) {
				const roles = [...new Set(pageData.jobs.map((j) => j.role_match))].sort();
				setRoleOptions(roles);
			}
		} catch (e) {
			setError(e instanceof Error ? e.message : String(e));
		} finally {
			setLoading(false);
		}
	}, [filterState, filterSource, filterRole, debouncedQ, filterDateFrom, filterDateTo]);

	// Reset to page 1 whenever any filter changes
	useEffect(() => {
		setPage(1);
	}, [filterState, filterSource, filterRole, debouncedQ, filterDateFrom, filterDateTo]);

	// Load when page or filters change
	useEffect(() => {
		void loadJobs(page);
	}, [loadJobs, page]);

	const latestSource = sources
		.filter((s) => s.last_scraped_at)
		.sort((a, b) => new Date(b.last_scraped_at!).getTime() - new Date(a.last_scraped_at!).getTime())[0];
	const latestFetchedLabel = useLiveRelativeTime(latestSource?.last_scraped_at ?? null);

	const handleStateChange = async (job: Job, newState: ApplicationState) => {
		// Optimistic update
		setJobs((prev) => prev.map((j) => (j.id === job.id ? { ...j, application_state: newState } : j)));
		try {
			await updateJobState(job.id, newState);
		} catch {
			// Revert on failure
			setJobs((prev) => prev.map((j) => (j.id === job.id ? { ...j, application_state: job.application_state } : j)));
		}
	};

	const handleRemove = async (job: Job) => {
		// Optimistic: visually remove from the list immediately (unless viewing REMOVED)
		if (!filterState || filterState !== "REMOVED") {
			setJobs((prev) => prev.filter((j) => j.id !== job.id));
			setTotal((t) => t - 1);
		} else {
			setJobs((prev) => prev.map((j) => (j.id === job.id ? { ...j, application_state: "REMOVED" as ApplicationState } : j)));
		}
		try {
			await removeJob(job.id);
		} catch {
			// Revert by reloading
			void loadJobs(page);
		}
	};

	const handlePageChange = (newPage: number) => {
		setPage(newPage);
		window.scrollTo({ top: 0, behavior: "smooth" });
	};

	const handleFilterStateChange = (v: string) => { setFilterState(v); };
	const handleFilterSourceChange = (v: string) => { setFilterSource(v); };
	const handleFilterRoleChange = (v: string) => { setFilterRole(v); };
	const handleFilterDateFromChange = (v: string) => { setFilterDateFrom(v); };
	const handleFilterDateToChange = (v: string) => { setFilterDateTo(v); };

	if (error) {
		return (
			<div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "calc(100vh - 56px)", color: "var(--red)" }}>
				<div style={{ textAlign: "center" }}>
					<p style={{ fontSize: "20px", marginBottom: 8 }}>⚠️ Failed to load</p>
					<p style={{ color: "var(--text-secondary)", fontSize: "13px" }}>{error}</p>
					<button className='btn-primary' style={{ marginTop: 16 }} onClick={() => loadJobs(page)}>Retry</button>
				</div>
			</div>
		);
	}

	return (
		<div style={{ padding: "24px", maxWidth: "100%", overflow: "hidden" }}>
			{/* Header */}
			<div style={{ marginBottom: "20px" }}>
				<h1 style={{ fontSize: "22px", fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
					Job Dashboard
				</h1>
				<p style={{ color: "var(--text-secondary)", marginTop: 4, fontSize: 13 }}>
					{total} job{total !== 1 ? "s" : ""} found
					{totalPages > 1 && ` · page ${page} of ${totalPages}`}
					{latestSource?.last_scraped_at ? ` · last fetched ${latestFetchedLabel}` : null}
				</p>
			</div>

			{/* Filters */}
			<FilterBar
				sources={sources}
				roleOptions={roleOptions}
				filterState={filterState}
				filterSource={filterSource}
				filterRole={filterRole}
				filterQ={filterQ}
				filterDateFrom={filterDateFrom}
				filterDateTo={filterDateTo}
				onStateChange={handleFilterStateChange}
				onSourceChange={handleFilterSourceChange}
				onRoleChange={handleFilterRoleChange}
				onQChange={handleQChange}
				onDateFromChange={handleFilterDateFromChange}
				onDateToChange={handleFilterDateToChange}
			/>

			{/* Content */}
			{loading ? (
				<div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "80px 0" }}>
					<div style={{ textAlign: "center", color: "var(--text-secondary)" }}>
						<div
							className='spin'
							style={{
								width: 32, height: 32,
								border: "3px solid var(--border)",
								borderTopColor: "var(--accent)",
								borderRadius: "50%",
								margin: "0 auto 12px",
							}}
						/>
						<p>Loading jobs…</p>
					</div>
				</div>
			) : jobs.length === 0 && total === 0 && !filterState && !filterSource && !filterRole && !debouncedQ && !filterDateFrom && !filterDateTo ? (
				/* Truly empty (no jobs at all) */
				<div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "80px 20px", color: "var(--text-secondary)", textAlign: "center" }}>
					<div style={{ fontSize: 48, marginBottom: 16, opacity: 0.4 }}>📭</div>
					<h2 style={{ fontSize: 18, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 8px" }}>No jobs yet</h2>
					<p style={{ fontSize: 13, maxWidth: 360, margin: "0 0 20px" }}>
						Head to the{" "}
						<a href='/admin' style={{ color: "var(--accent)", textDecoration: "underline" }}>Admin Portal</a>{" "}
						and click <strong>Start Fetching</strong> to pull jobs from your configured sources.
					</p>
				</div>
			) : jobs.length === 0 ? (
				/* Filter returned nothing */
				<div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "80px 20px", color: "var(--text-secondary)", textAlign: "center" }}>
					<div style={{ fontSize: 48, marginBottom: 16, opacity: 0.4 }}>🔍</div>
					<h2 style={{ fontSize: 18, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 8px" }}>No matching jobs</h2>
					<p style={{ fontSize: 13, maxWidth: 360, margin: 0 }}>Try adjusting your filters, or clear them to see all jobs.</p>
				</div>
			) : (
				<>
					{/* Job list */}
					<div style={{ display: "flex", flexDirection: "column" }}>
						{jobs.map((job) => (
							<JobCard key={job.id} job={job} onStateChange={handleStateChange} onRemove={handleRemove} />
						))}
					</div>

					{/* Pagination */}
					{totalPages > 1 && (
						<div style={{
							display: "flex",
							alignItems: "center",
							justifyContent: "center",
							gap: 8,
							marginTop: 32,
							paddingBottom: 24,
						}}>
							<button
								id="pagination-prev"
								className="btn-ghost"
								style={{ fontSize: 13, padding: "7px 16px", opacity: page === 1 ? 0.4 : 1 }}
								disabled={page === 1}
								onClick={() => handlePageChange(page - 1)}>
								← Prev
							</button>

							{/* Page number buttons — show up to 7 around current page */}
							{Array.from({ length: totalPages }, (_, i) => i + 1)
								.filter((p) => p === 1 || p === totalPages || Math.abs(p - page) <= 2)
								.reduce<(number | "…")[]>((acc, p, idx, arr) => {
									if (idx > 0 && (p as number) - (arr[idx - 1] as number) > 1) acc.push("…");
									acc.push(p);
									return acc;
								}, [])
								.map((item, idx) =>
									item === "…" ? (
										<span key={`ellipsis-${idx}`} style={{ color: "var(--text-muted)", fontSize: 13, padding: "0 4px" }}>…</span>
									) : (
										<button
											key={item}
											id={`pagination-page-${item}`}
											className={item === page ? "btn-primary" : "btn-ghost"}
											style={{ fontSize: 13, padding: "7px 14px", minWidth: 38 }}
											onClick={() => handlePageChange(item as number)}>
											{item}
										</button>
									)
								)}

							<button
								id="pagination-next"
								className="btn-ghost"
								style={{ fontSize: 13, padding: "7px 16px", opacity: page === totalPages ? 0.4 : 1 }}
								disabled={page === totalPages}
								onClick={() => handlePageChange(page + 1)}>
								Next →
							</button>

							<span style={{ fontSize: 12, color: "var(--text-muted)", marginLeft: 8 }}>
								{((page - 1) * PAGE_SIZE) + 1}–{Math.min(page * PAGE_SIZE, total)} of {total}
							</span>
						</div>
					)}
				</>
			)}
		</div>
	);
}
