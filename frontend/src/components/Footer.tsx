"use client";

import Link from "next/link";

export default function Footer() {
	return (
		<footer
			style={{
				background: "rgba(255, 255, 255, 0.92)",
				backdropFilter: "blur(16px)",
				WebkitBackdropFilter: "blur(16px)",
				borderTop: "1px solid var(--border)",
				color: "var(--text-secondary)",
				padding: "20px 0",
				fontSize: "13px",
				marginTop: "auto",
				boxShadow: "0 -1px 3px rgba(15, 23, 42, 0.03)",
			}}>
			<div
				className='container'
				style={{
					maxWidth: "1200px",
					margin: "0 auto",
					padding: "0 24px",
					display: "flex",
					flexWrap: "wrap",
					alignItems: "center",
					justifyContent: "space-between",
					gap: "16px",
				}}>
				{/* Left: Brand Logo & Title */}
				<div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
					<img
						src='/logo.png'
						alt='JobAggregator Logo'
						width={26}
						height={26}
						style={{ borderRadius: "6px", objectFit: "cover", boxShadow: "0 2px 6px rgba(79, 70, 229, 0.2)" }}
					/>
					<span style={{ fontWeight: 700, color: "var(--text-primary)", fontSize: "14px", letterSpacing: "-0.02em" }}>
						Job Aggregator
					</span>
					<span style={{ fontSize: "11px", fontWeight: 600, color: "#0284c7", background: "#e0f2fe", padding: "2px 8px", borderRadius: "12px", border: "1px solid #bae6fd" }}>
						v1.0.0
					</span>
				</div>

				{/* Center: Creator Signature & Contact */}
				<div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--text-secondary)", fontSize: "13px" }}>
					<span>Designed & Developed by</span>
					<strong style={{ color: "var(--text-primary)", fontWeight: 700 }}>Yasiru Kaveeshwara</strong>
					<span style={{ color: "var(--border)" }}>•</span>
					<a
						href='mailto:kaveeshwaray@gmail.com'
						style={{
							color: "var(--accent)",
							textDecoration: "none",
							fontWeight: 600,
							transition: "color 0.15s ease",
						}}
						onMouseEnter={(e) => (e.currentTarget.style.color = "#4338ca")}
						onMouseLeave={(e) => (e.currentTarget.style.color = "var(--accent)")}>
						kaveeshwaray@gmail.com
					</a>
				</div>

				{/* Right: GitHub Repo Link & Copyright */}
				<div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
					<a
						href='https://github.com/YasiruKaveeshwara/Job-Aggregator'
						target='_blank'
						rel='noreferrer'
						style={{
							color: "var(--text-secondary)",
							textDecoration: "none",
							display: "flex",
							alignItems: "center",
							gap: "6px",
							fontSize: "12px",
							fontWeight: 500,
							transition: "color 0.15s ease",
						}}
						onMouseEnter={(e) => (e.currentTarget.style.color = "var(--text-primary)")}
						onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text-secondary)")}>
						<svg width='15' height='15' viewBox='0 0 24 24' fill='currentColor'>
							<path d='M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z' />
						</svg>
						GitHub Repo
					</a>
					<span style={{ fontSize: "12px", color: "var(--text-muted)" }}>© {new Date().getFullYear()}</span>
				</div>
			</div>
		</footer>
	);
}
