"use client";
import { useState } from "react";
import type { Job, ApplicationState } from "@/types/job";
import { useLiveRelativeTime, formatLocalDateTimeFull, formatLocalDate } from "@/lib/datetime";

interface JobCardProps {
	job: Job;
	onStateChange: (job: Job, newState: ApplicationState) => void;
	onRemove: (job: Job) => void;
}

function RelativeTime({ iso }: { iso: string | null }) {
	const label = useLiveRelativeTime(iso);
	return (
		<span
			title={iso ? `Posted: ${formatLocalDateTimeFull(iso)}` : undefined}
			style={{ fontSize: 12, color: "var(--text-muted)", whiteSpace: "nowrap" }}>
			{label}
		</span>
	);
}

const PLATFORM_BADGE: Record<string, string> = {
	"itpro.lk": "badge-indigo",
	"anyjobok.com": "badge-green",
	"governmentjob.lk": "badge-amber",
	"jobenvoy.com": "badge-purple",
	"rooster.jobs": "badge-cyan",
	"topjobs.lk": "badge-red",
	"xpress.jobs": "badge-neutral",
	"findmyjob.lk": "badge-blue",
	"hire.lk": "badge-indigo",
	"jobseeker.lk": "badge-amber",
};

function CompanyAvatar({ name, imageUrl }: { name: string; imageUrl?: string | null }) {
	const [imgError, setImgError] = useState(false);
	const initials = name
		.split(/\s+/)
		.slice(0, 2)
		.map((w) => w[0]?.toUpperCase() ?? "")
		.join("");
	const hue = name.split("").reduce((acc, c) => acc + c.charCodeAt(0), 0) % 360;

	return (
		<div
			style={{
				width: 52,
				height: 52,
				flexShrink: 0,
				borderRadius: "var(--radius)",
				border: "1px solid var(--border)",
				background: `hsl(${hue}, 60%, 96%)`,
				display: "flex",
				alignItems: "center",
				justifyContent: "center",
				overflow: "hidden",
			}}>
			{imageUrl && !imgError ?
				<img
					src={imageUrl}
					alt={name}
					onError={() => setImgError(true)}
					style={{ width: "100%", height: "100%", objectFit: "contain", padding: 4 }}
				/>
			:	<span
					style={{
						fontSize: 15,
						fontWeight: 700,
						color: `hsl(${hue}, 50%, 40%)`,
						letterSpacing: "-0.02em",
					}}>
					{initials || "J"}
				</span>
			}
		</div>
	);
}

// ── Detail panel field row ──────────────────────────────────────────
function DetailRow({ label, children }: { label: string; children: React.ReactNode }) {
	return (
		<div style={{ display: "flex", gap: 12, fontSize: 13, lineHeight: 1.5 }}>
			<span
				style={{
					width: 100,
					flexShrink: 0,
					color: "var(--text-muted)",
					fontWeight: 500,
					fontSize: 12,
					paddingTop: 1,
				}}>
				{label}
			</span>
			<span style={{ color: "var(--text-secondary)", flex: 1 }}>{children}</span>
		</div>
	);
}

export default function JobCard({ job, onStateChange, onRemove }: JobCardProps) {
	const [expanded, setExpanded] = useState(false);
	const isRemoved = job.application_state === "REMOVED";
	const isApplied = job.application_state === "APPLIED";

	return (
		<article
			className='card card-interactive fade-in'
			style={{
				padding: "18px 20px",
				display: "flex",
				flexDirection: "column",
				gap: 0,
				opacity: isRemoved ? 0.55 : 1,
				transition: "opacity 0.2s ease, box-shadow 0.18s ease, border-color 0.18s ease, transform 0.18s ease",
			}}>
			{/* ── Main row ── */}
			<div style={{ display: "flex", gap: 16, alignItems: "flex-start" }}>
				{/* Avatar */}
				<CompanyAvatar name={job.company_name} imageUrl={job.image_url} />

				{/* Content */}
				<div style={{ flex: 1, minWidth: 0 }}>
					{/* Title + date */}
					<div
						style={{
							display: "flex",
							justifyContent: "space-between",
							alignItems: "flex-start",
							gap: 12,
							marginBottom: 4,
						}}>
						<h3
							style={{
								fontSize: 15,
								fontWeight: 600,
								color: "var(--text-primary)",
								lineHeight: 1.35,
								letterSpacing: "-0.01em",
							}}>
							{job.job_title}
						</h3>
						<RelativeTime iso={job.posted_date ?? null} />
					</div>

					{/* Company & location */}
					<p
						style={{
							fontSize: 13,
							color: "var(--text-secondary)",
							marginBottom: 10,
							display: "flex",
							alignItems: "center",
							gap: 6,
							flexWrap: "wrap",
						}}>
						<span style={{ fontWeight: 500 }}>{job.company_name}</span>
						{job.location_normalized && (
							<>
								<span style={{ color: "var(--border-strong)" }}>·</span>
								<span style={{ color: "var(--text-muted)" }}>{job.location_normalized}</span>
							</>
						)}
					</p>

					{/* Badges */}
					<div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
						<span className='badge badge-indigo'>{job.role_match}</span>

						{job.salary_disclosed && job.salary_min != null && (
							<span className='badge badge-green'>
								LKR {job.salary_min.toLocaleString()}
								{job.salary_max && job.salary_max !== job.salary_min ? ` – ${job.salary_max.toLocaleString()}` : ""}
							</span>
						)}

						{job.sources.map((s) => (
							<a
								key={s.id}
								href={s.url}
								target='_blank'
								rel='noopener noreferrer'
								className={`badge ${PLATFORM_BADGE[s.platform] ?? "badge-neutral"}`}
								style={{ textDecoration: "none", cursor: "pointer" }}>
								{s.platform}
							</a>
						))}

						{isApplied && <span className='badge badge-state-applied'>Applied</span>}
						{isRemoved && <span className='badge badge-state-removed'>Removed</span>}
					</div>
				</div>

				{/* Actions */}
				<div
					style={{
						flexShrink: 0,
						display: "flex",
						flexDirection: "column",
						gap: 8,
						alignItems: "stretch",
						minWidth: 108,
					}}>
					{isRemoved ?
						<button
							className='btn btn-ghost btn-sm'
							onClick={() => onStateChange(job, "NEW")}
							style={{ width: "100%", justifyContent: "center" }}>
							Restore
						</button>
					:	<button
							className={`btn btn-sm ${isApplied ? "btn-success" : "btn-primary"}`}
							onClick={() => onStateChange(job, isApplied ? "NEW" : "APPLIED")}
							style={{ width: "100%", justifyContent: "center" }}>
							{isApplied ? "Applied" : "Mark Applied"}
						</button>
					}

					{!isRemoved && (
						<button
							className='btn btn-danger btn-sm'
							onClick={() => onRemove(job)}
							style={{ width: "100%", justifyContent: "center" }}>
							Remove
						</button>
					)}

					<button
						className='btn btn-ghost btn-sm'
						onClick={() => setExpanded(!expanded)}
						style={{ width: "100%", justifyContent: "center", gap: 4 }}>
						Details
						<svg
							width='11'
							height='11'
							viewBox='0 0 11 11'
							fill='none'
							style={{ transition: "transform 0.2s", transform: expanded ? "rotate(180deg)" : "rotate(0)" }}>
							<path
								d='M1.5 3.5l4 4 4-4'
								stroke='currentColor'
								strokeWidth='1.5'
								strokeLinecap='round'
								strokeLinejoin='round'
							/>
						</svg>
					</button>
				</div>
			</div>

			{/* ── Expanded detail panel ── */}
			{expanded && (
				<div
					style={{
						marginTop: 16,
						paddingTop: 16,
						borderTop: "1px solid var(--border)",
					}}>
					<div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
						{/* Posted date — full format */}
						{job.posted_date && (
							<DetailRow label='Posted'>
								{formatLocalDate(job.posted_date)}
								<span style={{ marginLeft: 8, fontSize: 11, color: "var(--text-muted)" }}>
									({formatLocalDateTimeFull(job.posted_date)})
								</span>
							</DetailRow>
						)}

						{/* Added to dashboard */}
						<DetailRow label='Added'>{formatLocalDate(job.created_at)}</DetailRow>

						{/* Location */}
						{(job.location_raw || job.location_normalized) && (
							<DetailRow label='Location'>
								{job.location_normalized || job.location_raw}
								{job.location_raw && job.location_normalized && job.location_raw !== job.location_normalized && (
									<span style={{ marginLeft: 6, fontSize: 11, color: "var(--text-muted)" }}>
										(raw: {job.location_raw})
									</span>
								)}
							</DetailRow>
						)}

						{/* Salary */}
						{job.salary_disclosed && job.salary_min != null && (
							<DetailRow label='Salary'>
								<span style={{ color: "var(--green)", fontWeight: 600 }}>
									LKR {job.salary_min.toLocaleString()}
									{job.salary_max && job.salary_max !== job.salary_min ? ` – ${job.salary_max.toLocaleString()}` : ""}
								</span>
								{" / month"}
							</DetailRow>
						)}

						{/* Role match */}
						<DetailRow label='Role match'>
							<span className='badge badge-indigo' style={{ display: "inline-flex" }}>
								{job.role_match}
							</span>
						</DetailRow>

						{/* Application state */}
						<DetailRow label='Status'>
							<span
								className={`badge badge-state-${job.application_state.toLowerCase()}`}
								style={{ display: "inline-flex" }}>
								{job.application_state}
							</span>
						</DetailRow>

						{/* Sources */}
						<DetailRow label='Sources'>
							<div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
								{job.sources.map((s) => (
									<a
										key={s.id}
										href={s.url}
										target='_blank'
										rel='noopener noreferrer'
										className={`badge ${PLATFORM_BADGE[s.platform] ?? "badge-neutral"}`}
										style={{ textDecoration: "none" }}>
										{s.platform}
										<svg width='10' height='10' viewBox='0 0 10 10' fill='none' style={{ marginLeft: 2 }}>
											<path
												d='M2 8L8 2M8 2H4M8 2v4'
												stroke='currentColor'
												strokeWidth='1.25'
												strokeLinecap='round'
												strokeLinejoin='round'
											/>
										</svg>
									</a>
								))}
							</div>
						</DetailRow>

						{/* Scraped date per source */}
						{job.sources.length > 0 && (
							<DetailRow label='Scraped'>
								<div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
									{job.sources.map((s) => (
										<span key={s.id} style={{ fontSize: 12 }}>
											<span style={{ color: "var(--text-secondary)" }}>{s.platform}</span>
											{" — "}
											{formatLocalDate(s.scraped_date)}
										</span>
									))}
								</div>
							</DetailRow>
						)}

						{/* Description */}
						{job.description_clean ?
							<div style={{ marginTop: 4 }}>
								<div
									style={{
										fontSize: 11,
										fontWeight: 600,
										color: "var(--text-muted)",
										textTransform: "uppercase",
										letterSpacing: "0.06em",
										marginBottom: 8,
									}}>
									Job Description
								</div>
								<div
									style={{
										fontSize: 13,
										color: "var(--text-secondary)",
										lineHeight: 1.75,
										whiteSpace: "pre-wrap",
										background: "var(--bg-base)",
										borderRadius: "var(--radius)",
										border: "1px solid var(--border)",
										padding: "14px 16px",
										maxHeight: 360,
										overflowY: "auto",
									}}>
									{job.description_clean}
								</div>
							</div>
						:	<DetailRow label='Description'>
								<span style={{ color: "var(--text-muted)", fontStyle: "italic" }}>
									No description available. Click a source link above to view on the original site.
								</span>
							</DetailRow>
						}
					</div>
				</div>
			)}
		</article>
	);
}
