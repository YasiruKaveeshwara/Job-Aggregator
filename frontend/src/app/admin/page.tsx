"use client";
import { useEffect, useState } from "react";
import { getSources } from "@/lib/api";
import type { Source } from "@/types/job";
import ScrapeControlPanel from "@/components/ScrapeControlPanel";
import RunHistoryTable from "@/components/RunHistoryTable";
import KeywordEditor from "@/components/KeywordEditor";

export default function AdminPage() {
	const [sources, setSources] = useState<Source[]>([]);
	const [historyRefreshKey, setHistoryRefreshKey] = useState(0);

	const loadSources = () => {
		getSources().then(setSources).catch(console.error);
	};

	useEffect(() => {
		loadSources();
	}, []);

	return (
		<div style={{ padding: "24px", maxWidth: 900, margin: "0 auto" }}>
			<div style={{ marginBottom: 28 }}>
				<h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>Admin Portal</h1>
				<p style={{ color: "var(--text-secondary)", fontSize: 13, marginTop: 4 }}>
					Manually trigger scrape runs, manage sources, and configure keywords.
				</p>
			</div>

			{/* Scrape control */}
			<section style={{ marginBottom: 28 }}>
				<SectionLabel icon='🔌' title='Sources & Scrape Control' />
				<ScrapeControlPanel
					sources={sources}
					onSourcesChange={setSources}
					onRunFinished={() => {
						setHistoryRefreshKey((value) => value + 1);
						loadSources();
					}}
				/>
			</section>

			{/* Keyword config */}
			<section style={{ marginBottom: 28 }}>
				<SectionLabel icon='🔑' title='Role Keywords' />
				<KeywordEditor />
			</section>

			{/* Run history */}
			<section>
				<SectionLabel icon='📋' title='Run History' />
				<RunHistoryTable refreshKey={historyRefreshKey} />
			</section>
		</div>
	);
}

function SectionLabel({ icon, title }: { icon: string; title: string }) {
	return (
		<div
			style={{
				display: "flex",
				alignItems: "center",
				gap: 8,
				marginBottom: 12,
			}}>
			<span style={{ fontSize: 16 }}>{icon}</span>
			<h2 style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>{title}</h2>
		</div>
	);
}
