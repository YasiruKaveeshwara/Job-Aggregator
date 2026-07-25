"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_LINKS = [
	{
		href: "/",
		label: "Dashboard",
		icon: (
			<svg width='15' height='15' viewBox='0 0 24 24' fill='none' stroke='currentColor' strokeWidth='2'>
				<rect x='3' y='3' width='7' height='7' rx='1.5' />
				<rect x='14' y='3' width='7' height='7' rx='1.5' />
				<rect x='14' y='14' width='7' height='7' rx='1.5' />
				<rect x='3' y='14' width='7' height='7' rx='1.5' />
			</svg>
		),
	},
	{
		href: "/admin",
		label: "Admin Portal",
		icon: (
			<svg width='15' height='15' viewBox='0 0 24 24' fill='none' stroke='currentColor' strokeWidth='2'>
				<polygon points='13 2 3 14 12 14 11 22 21 10 12 10 13 2' />
			</svg>
		),
	},
];

export default function Nav() {
	const path = usePathname();

	return (
		<nav
			style={{
				position: "sticky",
				top: 0,
				zIndex: 200,
				height: "64px",
				background: "rgba(255, 255, 255, 0.88)",
				backdropFilter: "blur(16px)",
				WebkitBackdropFilter: "blur(16px)",
				borderBottom: "1px solid var(--border)",
				boxShadow: "0 1px 3px rgba(15, 23, 42, 0.05)",
			}}>
			<div
				className='container'
				style={{
					height: "100%",
					display: "flex",
					alignItems: "center",
					justifyContent: "space-between",
					maxWidth: "1200px",
				}}>
				{/* Brand Wordmark & Logo */}
				<Link
					href='/'
					style={{
						display: "flex",
						alignItems: "center",
						gap: 12,
						textDecoration: "none",
					}}>
					<div
						style={{
							width: 36,
							height: 36,
							borderRadius: "10px",
							background: "linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)",
							display: "flex",
							alignItems: "center",
							justifyContent: "center",
							flexShrink: 0,
							boxShadow: "0 2px 10px rgba(79, 70, 229, 0.3)",
						}}>
						<svg width='20' height='20' viewBox='0 0 24 24' fill='none'>
							<path
								d='M12 2L2 7L12 12L22 7L12 2Z'
								stroke='white'
								strokeWidth='2'
								strokeLinecap='round'
								strokeLinejoin='round'
							/>
							<path d='M2 17L12 22L22 17' stroke='white' strokeWidth='2' strokeLinecap='round' strokeLinejoin='round' />
							<path d='M2 12L12 17L22 12' stroke='white' strokeWidth='2' strokeLinecap='round' strokeLinejoin='round' />
						</svg>
					</div>
					<div>
						<div style={{ display: "flex", alignItems: "center", gap: 8 }}>
							<span
								style={{
									fontWeight: 800,
									fontSize: 16,
									color: "var(--text-primary)",
									letterSpacing: "-0.03em",
									lineHeight: 1.1,
								}}>
								JobAggregator
							</span>
						</div>
						<div
							style={{
								fontSize: 11,
								color: "var(--text-muted)",
								letterSpacing: "0.02em",
								fontWeight: 500,
								marginTop: 2,
							}}>
							Sri Lanka Tech Jobs Engine
						</div>
					</div>
				</Link>

				{/* Navigation Links & Actions */}
				<div style={{ display: "flex", alignItems: "center", gap: 12 }}>
					<div
						style={{
							display: "flex",
							alignItems: "center",
							gap: 4,
							background: "var(--bg-base)",
							padding: "4px",
							borderRadius: "var(--radius-md)",
							border: "1px solid var(--border)",
						}}>
						{NAV_LINKS.map(({ href, label, icon }) => {
							const active = path === href;
							return (
								<Link
									key={href}
									href={href}
									style={{
										display: "flex",
										alignItems: "center",
										gap: 7,
										padding: "7px 16px",
										borderRadius: "var(--radius)",
										fontSize: 13,
										fontWeight: active ? 700 : 500,
										color: active ? "var(--accent)" : "var(--text-secondary)",
										background: active ? "var(--bg-surface)" : "transparent",
										boxShadow: active ? "var(--shadow-xs)" : "none",
										textDecoration: "none",
										transition: "all 0.15s ease",
										letterSpacing: "-0.01em",
									}}>
									<span style={{ color: active ? "var(--accent)" : "var(--text-muted)" }}>{icon}</span>
									{label}
								</Link>
							);
						})}
					</div>
				</div>
			</div>
		</nav>
	);
}
