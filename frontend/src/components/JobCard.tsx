"use client";
import { useState } from "react";
import type { Job, ApplicationState } from "@/types/job";
import { useLiveRelativeTime } from "@/lib/datetime";

interface JobCardProps {
	job: Job;
	onStateChange: (job: Job, newState: ApplicationState) => void;
}

function RelativeTimeLabel({ iso }: { iso: string | null }) {
	const value = useLiveRelativeTime(iso);
	return <span style={{ fontSize: 12, color: "var(--text-muted)", whiteSpace: "nowrap" }}>{value}</span>;
}

const PLATFORM_COLORS: Record<string, string> = {
	"itpro.lk": "badge-indigo",
	"anyjobok.com": "badge-green",
	"governmentjob.lk": "badge-amber",
	"jobenvoy.com": "badge-purple",
	"rooster.jobs": "badge-cyan",
	"topjobs.lk": "badge-red",
};

export default function JobCard({ job, onStateChange }: JobCardProps) {
	const [expanded, setExpanded] = useState(false);

	const handleApplyToggle = () => {
		onStateChange(job, job.application_state === "APPLIED" ? "NEW" : "APPLIED");
	};

	return (
		<div
			className='card card-hover'
			style={{
				padding: "16px",
				cursor: "default",
				display: "flex",
				gap: "16px",
				alignItems: "flex-start",
				marginBottom: "12px",
			}}>
			{/* Image */}
			<div
				style={{
					width: 64,
					height: 64,
					flexShrink: 0,
					borderRadius: 8,
					background: "var(--bg-surface)",
					border: "1px solid var(--border)",
					display: "flex",
					alignItems: "center",
					justifyContent: "center",
					overflow: "hidden",
				}}>
				{job.image_url ?
					<img
						src={job.image_url}
						alt={job.company_name}
						style={{ width: "100%", height: "100%", objectFit: "contain" }}
						onError={(e) => {
							(e.target as HTMLImageElement).style.display = "none";
							(e.target as HTMLImageElement).nextElementSibling?.removeAttribute("style");
						}}
					/>
				:	null}
				<div
					style={{
						display: job.image_url ? "none" : "block",
						fontSize: 24,
						color: "var(--text-muted)",
					}}>
					🏢
				</div>
			</div>

			{/* Main content */}
			<div style={{ flex: 1, minWidth: 0 }}>
				{/* Title and date */}
				<div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
					<h3
						style={{
							fontWeight: 600,
							fontSize: 16,
							color: "var(--text-primary)",
							lineHeight: 1.3,
							margin: "0 0 4px",
						}}>
						{job.job_title}
					</h3>
					{job.posted_date && (
						<span title={`Posted ${new Date(job.posted_date).toLocaleString()}`}>
							<RelativeTimeLabel iso={job.posted_date} />
						</span>
					)}
				</div>

				{/* Company + location */}
				<p
					style={{
						fontSize: 14,
						color: "var(--text-secondary)",
						margin: "0 0 8px",
					}}>
					{job.company_name}
					{job.location_normalized && (
						<span style={{ color: "var(--text-muted)" }}>
							{" · "}
							{job.location_normalized}
						</span>
					)}
				</p>

				{/* Badges */}
				<div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 12 }}>
					<span className='badge badge-indigo' style={{ fontSize: 11, padding: "4px 10px" }}>
						{job.role_match}
					</span>
					{job.salary_disclosed && job.salary_min != null && (
						<span className='badge badge-green' style={{ fontSize: 11, padding: "4px 10px" }}>
							LKR {job.salary_min.toLocaleString()}
							{job.salary_max && job.salary_max !== job.salary_min ? `–${job.salary_max.toLocaleString()}` : ""}
						</span>
					)}
					{job.sources.map((s) => (
						<a
							key={s.id}
							href={s.url}
							target='_blank'
							rel='noopener noreferrer'
							className={`badge ${PLATFORM_COLORS[s.platform] ?? "badge-neutral"}`}
							style={{ fontSize: 11, padding: "4px 10px", textDecoration: "none" }}>
							↗ {s.platform}
						</a>
					))}
				</div>

				{/* Description toggle */}
				{job.description_clean && (
					<div style={{ marginTop: 8 }}>
						<button
							className='btn-ghost'
							style={{ fontSize: 12, padding: "4px 8px" }}
							onClick={() => setExpanded(!expanded)}>
							{expanded ? "Hide description ▲" : "Read description ▼"}
						</button>
						{expanded && (
							<p
								style={{
									fontSize: 13,
									color: "var(--text-secondary)",
									marginTop: 12,
									marginBottom: 0,
									lineHeight: 1.6,
									maxHeight: 200,
									overflowY: "auto",
									padding: "12px",
									background: "var(--bg-surface)",
									borderRadius: 8,
									border: "1px solid var(--border)",
								}}>
								{job.description_clean}
							</p>
						)}
					</div>
				)}
			</div>

			{/* Action */}
			<div style={{ flexShrink: 0, display: "flex", flexDirection: "column", gap: 8 }}>
				<button
					className={job.application_state === "APPLIED" ? "btn-ghost" : "btn-primary"}
					onClick={handleApplyToggle}
					style={{ width: 100 }}>
					{job.application_state === "APPLIED" ? "✓ Applied" : "Mark Applied"}
				</button>
			</div>
		</div>
	);
}
