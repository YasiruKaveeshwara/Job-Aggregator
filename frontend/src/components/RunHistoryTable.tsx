"use client";
import { useEffect, useState } from "react";
import { getScrapeRuns } from "@/lib/api";
import { useLiveRelativeTime } from "@/lib/datetime";
import type { ScrapeRun } from "@/types/job";

function RelativeDateCell({ iso }: { iso: string }) {
	return <>{useLiveRelativeTime(iso)}</>;
}

function formatDuration(start: string, end: string | null): string {
	if (!end) return "—";
	const ms = new Date(end).getTime() - new Date(start).getTime();
	const s = Math.round(ms / 1000);
	return s < 60 ? `${s}s` : `${Math.round(s / 60)}m ${s % 60}s`;
}

interface Props {
	refreshKey?: number;
}

export default function RunHistoryTable({ refreshKey = 0 }: Props) {
	const [runs, setRuns] = useState<ScrapeRun[]>([]);
	const [loading, setLoading] = useState(true);

	useEffect(() => {
		getScrapeRuns()
			.then(setRuns)
			.catch(console.error)
			.finally(() => setLoading(false));
	}, [refreshKey]);

	if (loading) {
		return (
			<div className='card loading' style={{ padding: 16, color: "var(--text-muted)", fontSize: 13 }}>
				Loading run history…
			</div>
		);
	}

	if (runs.length === 0) {
		return (
			<div className='card' style={{ padding: 16, color: "var(--text-muted)", fontSize: 13 }}>
				No runs yet. Click &quot;Start Fetching&quot; above.
			</div>
		);
	}

	return (
		<div className='card' style={{ overflowX: "auto" }}>
			<table
				style={{
					width: "100%",
					borderCollapse: "collapse",
					fontSize: 13,
				}}>
				<thead>
					<tr
						style={{
							borderBottom: "1px solid var(--border)",
							color: "var(--text-muted)",
						}}>
						{["#", "Started", "Duration", "Status", "Sites"].map((h) => (
							<th
								key={h}
								style={{
									padding: "10px 14px",
									textAlign: "left",
									fontWeight: 600,
									fontSize: 11,
									letterSpacing: "0.05em",
									textTransform: "uppercase",
								}}>
								{h}
							</th>
						))}
					</tr>
				</thead>
				<tbody>
					{runs.map((run, i) => {
						return (
							<tr
								key={run.id}
								style={{
									borderBottom: i < runs.length - 1 ? "1px solid var(--border-subtle)" : "none",
								}}>
								{/* ID */}
								<td style={{ padding: "10px 14px", color: "var(--text-muted)" }}>#{run.id}</td>

								{/* Started */}
								<td style={{ padding: "10px 14px" }}>
									<RelativeDateCell iso={run.started_at} />
								</td>
								{/* Duration */}
								<td
									style={{
										padding: "10px 14px",
										color: "var(--text-secondary)",
									}}>
									{formatDuration(run.started_at, run.finished_at)}
								</td>

								{/* Status */}
								<td style={{ padding: "10px 14px" }}>
									<span
										className={`badge ${
											run.status === "COMPLETED" ? "badge-green"
											: run.status === "FAILED" ? "badge-red"
											: "badge-indigo"
										}`}>
										{run.status === "RUNNING" && (
											<span
												style={{
													display: "inline-block",
													width: 6,
													height: 6,
													borderRadius: "50%",
													background: "currentColor",
													animation: "pulse 1s ease-in-out infinite",
												}}
											/>
										)}
										{run.status}
									</span>
								</td>

								{/* Site results */}
								<td style={{ padding: "10px 14px" }}>
									{Object.keys(run.site_results).length === 0 ?
										<span style={{ color: "var(--text-muted)" }}>—</span>
									:	<div
											style={{
												display: "flex",
												flexDirection: "column",
												gap: 2,
											}}>
											{Object.entries(run.site_results).map(([site, r]) => (
												<div
													key={site}
													style={{
														display: "flex",
														gap: 8,
														fontSize: 12,
														alignItems: "center",
													}}>
													<span style={{ color: "var(--text-secondary)", minWidth: 130 }}>{site}</span>
													{r.error ?
														<span style={{ color: "var(--red)" }}>Error: {r.error}</span>
													:	<>
															<span style={{ color: "var(--text-muted)" }}>{r.found} found</span>
															<span
																style={{
																	color: r.new > 0 ? "var(--green)" : "var(--text-muted)",
																	fontWeight: r.new > 0 ? 700 : 400,
																}}>
																+{r.new} new
															</span>
															<span style={{ color: "var(--text-muted)" }}>{r.duplicates} dup</span>
														</>
													}
												</div>
											))}
										</div>
									}
								</td>
							</tr>
						);
					})}
				</tbody>
			</table>
		</div>
	);
}
