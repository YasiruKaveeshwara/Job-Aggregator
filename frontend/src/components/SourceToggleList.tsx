"use client";
import { toggleSource } from "@/lib/api";
import { useLiveRelativeTime } from "@/lib/datetime";
import type { Source } from "@/types/job";

interface Props {
	sources: Source[];
	onSourcesChange: (sources: Source[]) => void;
}

function RelativeTimeLabel({ iso }: { iso: string | null }) {
	const value = useLiveRelativeTime(iso);
	return <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>{value}</span>;
}

export default function SourceToggleList({ sources, onSourcesChange }: Props) {
	const handleToggle = async (source: Source) => {
		const updated = await toggleSource(source.name, !source.enabled);
		onSourcesChange(sources.map((s) => (s.id === updated.id ? updated : s)));
	};

	return (
		<div className='card' style={{ overflow: "hidden" }}>
			{sources.length === 0 && (
				<p style={{ padding: 16, color: "var(--text-muted)", fontSize: 13 }}>Loading sources…</p>
			)}
			{sources.map((src, i) => (
				<div
					key={src.id}
					style={{
						padding: "12px 16px",
						display: "flex",
						alignItems: "center",
						gap: 12,
						borderBottom: i < sources.length - 1 ? "1px solid var(--border-subtle)" : "none",
					}}>
					{/* Status dot */}
					<span
						style={{
							width: 8,
							height: 8,
							borderRadius: "50%",
							background: src.enabled ? "var(--green)" : "var(--text-muted)",
							flexShrink: 0,
						}}
					/>

					{/* Name + last scraped */}
					<div style={{ flex: 1 }}>
						<span style={{ fontWeight: 600, fontSize: 13 }}>{src.name}</span>
						<div
							style={{
								fontSize: 11,
								color: "var(--text-muted)",
								marginTop: 1,
								opacity: 0.8,
							}}>
							{src.last_scraped_at ?
								<>
									Last scraped <RelativeTimeLabel iso={src.last_scraped_at} />
								</>
							:	<span style={{ fontStyle: "italic" }}>Never scraped</span>}
						</div>
					</div>

					{/* Status text */}
					<span
						style={{
							fontSize: 12,
							color: src.enabled ? "var(--green)" : "var(--text-muted)",
						}}>
						{src.enabled ? "Enabled" : "Disabled"}
					</span>

					{/* Toggle */}
					<label className='toggle'>
						<input type='checkbox' checked={src.enabled} onChange={() => handleToggle(src)} />
						<span className='toggle-slider' />
					</label>
				</div>
			))}
		</div>
	);
}
