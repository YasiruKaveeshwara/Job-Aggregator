"use client";
import { useState, useEffect, useCallback } from "react";
import { getJobs, updateJobState, getSources } from "@/lib/api";
import { useLiveRelativeTime, getLocalDateKey } from "@/lib/datetime";
import type { Job, ApplicationState, Source } from "@/types/job";
import JobCard from "@/components/JobCard";
import FilterBar from "@/components/FilterBar";

async function fetchDashboardData() {
	return Promise.all([getJobs(), getSources()]);
}

export default function DashboardPage() {
	const [jobs, setJobs] = useState<Job[]>([]);
	const [sources, setSources] = useState<Source[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	const [filterState, setFilterState] = useState("");
	const [filterSource, setFilterSource] = useState("");
	const [filterRole, setFilterRole] = useState("");
	const [filterQ, setFilterQ] = useState("");
	const [filterDateFrom, setFilterDateFrom] = useState("");
	const [filterDateTo, setFilterDateTo] = useState("");

	const load = useCallback(async () => {
		try {
			const [jobData, srcData] = await fetchDashboardData();
			setJobs(jobData);
			setSources(srcData);
		} catch (e) {
			setError(e instanceof Error ? e.message : String(e));
		} finally {
			setLoading(false);
		}
	}, []);

	const latestSource = sources
		.filter((s) => s.last_scraped_at)
		.sort((a, b) => new Date(b.last_scraped_at!).getTime() - new Date(a.last_scraped_at!).getTime())[0];
	const latestFetchedLabel = useLiveRelativeTime(latestSource?.last_scraped_at ?? null);

	useEffect(() => {
		let cancelled = false;

		const runLoad = async () => {
			try {
				const [jobData, srcData] = await fetchDashboardData();
				if (cancelled) return;
				setJobs(jobData);
				setSources(srcData);
			} catch (e) {
				if (!cancelled) {
					setError(e instanceof Error ? e.message : String(e));
				}
			} finally {
				if (!cancelled) {
					setLoading(false);
				}
			}
		};

		void runLoad();

		return () => {
			cancelled = true;
		};
	}, []);

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

	// Client-side filtering
	const filteredJobs = jobs.filter((j) => {
		if (filterState && j.application_state !== filterState) return false;
		if (filterSource && !j.sources.some((s) => s.platform === filterSource)) return false;
		if (filterRole && j.role_match !== filterRole) return false;
		if (filterQ) {
			const q = filterQ.toLowerCase();
			if (!j.job_title.toLowerCase().includes(q) && !j.company_name.toLowerCase().includes(q)) return false;
		}
		if (j.posted_date) {
			const postedDate = getLocalDateKey(j.posted_date);
			if (filterDateFrom && postedDate < filterDateFrom) return false;
			if (filterDateTo && postedDate > filterDateTo) return false;
		} else if (filterDateFrom || filterDateTo) {
			// If filtering by date, hide jobs without a posted_date
			return false;
		}
		return true;
	});

	// Unique role matches for filter dropdown
	const roleOptions = [...new Set(jobs.map((j) => j.role_match))].sort();

	if (loading) {
		return (
			<div
				style={{
					display: "flex",
					alignItems: "center",
					justifyContent: "center",
					height: "calc(100vh - 56px)",
					color: "var(--text-secondary)",
				}}>
				<div style={{ textAlign: "center" }}>
					<div
						className='spin'
						style={{
							width: 32,
							height: 32,
							border: "3px solid var(--border)",
							borderTopColor: "var(--accent)",
							borderRadius: "50%",
							margin: "0 auto 12px",
						}}
					/>
					<p>Loading jobs…</p>
				</div>
			</div>
		);
	}

	if (error) {
		return (
			<div
				style={{
					display: "flex",
					alignItems: "center",
					justifyContent: "center",
					height: "calc(100vh - 56px)",
					color: "var(--red)",
				}}>
				<div style={{ textAlign: "center" }}>
					<p style={{ fontSize: "20px", marginBottom: 8 }}>⚠️ Failed to load</p>
					<p style={{ color: "var(--text-secondary)", fontSize: "13px" }}>{error}</p>
					<button className='btn-primary' style={{ marginTop: 16 }} onClick={load}>
						Retry
					</button>
				</div>
			</div>
		);
	}

	return (
		<div style={{ padding: "24px", maxWidth: "100%", overflow: "hidden" }}>
			{/* Header */}
			<div style={{ marginBottom: "20px" }}>
				<h1
					style={{
						fontSize: "22px",
						fontWeight: 700,
						color: "var(--text-primary)",
						margin: 0,
					}}>
					Job Dashboard
				</h1>
				<p style={{ color: "var(--text-secondary)", marginTop: 4, fontSize: 13 }}>
					{jobs.length} job{jobs.length !== 1 ? "s" : ""} tracked
					{filteredJobs.length !== jobs.length && ` · ${filteredJobs.length} shown`}
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
				onStateChange={setFilterState}
				onSourceChange={setFilterSource}
				onRoleChange={setFilterRole}
				onQChange={setFilterQ}
				onDateFromChange={setFilterDateFrom}
				onDateToChange={setFilterDateTo}
			/>

			{/* Empty state */}
			{jobs.length === 0 ?
				<div
					style={{
						display: "flex",
						flexDirection: "column",
						alignItems: "center",
						justifyContent: "center",
						padding: "80px 20px",
						color: "var(--text-secondary)",
						textAlign: "center",
					}}>
					<div style={{ fontSize: 48, marginBottom: 16, opacity: 0.4 }}>📭</div>
					<h2
						style={{
							fontSize: 18,
							fontWeight: 600,
							color: "var(--text-primary)",
							margin: "0 0 8px",
						}}>
						No jobs yet
					</h2>
					<p style={{ fontSize: 13, maxWidth: 360, margin: "0 0 20px" }}>
						Head to the{" "}
						<a href='/admin' style={{ color: "var(--accent)", textDecoration: "underline" }}>
							Admin Portal
						</a>{" "}
						and click <strong>Start Fetching</strong> to pull jobs from your configured sources.
					</p>
				</div>
			: filteredJobs.length === 0 ?
				<div
					style={{
						display: "flex",
						flexDirection: "column",
						alignItems: "center",
						justifyContent: "center",
						padding: "80px 20px",
						color: "var(--text-secondary)",
						textAlign: "center",
					}}>
					<div style={{ fontSize: 48, marginBottom: 16, opacity: 0.4 }}>🔍</div>
					<h2
						style={{
							fontSize: 18,
							fontWeight: 600,
							color: "var(--text-primary)",
							margin: "0 0 8px",
						}}>
						No matching jobs
					</h2>
					<p style={{ fontSize: 13, maxWidth: 360, margin: 0 }}>
						Try adjusting your filters above, or clear them to see all {jobs.length} tracked jobs.
					</p>
				</div>
			:	/* List View */
				<div style={{ display: "flex", flexDirection: "column" }}>
					{filteredJobs.map((job) => (
						<JobCard key={job.id} job={job} onStateChange={handleStateChange} />
					))}
				</div>
			}
		</div>
	);
}
