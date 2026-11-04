"use client";

import { useSyncExternalStore } from "react";

type Theme = "light" | "dark";
const STORAGE_KEY = "job-aggregator-theme";

function getCurrentTheme(): Theme {
	return typeof document !== "undefined" && document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}

function subscribeToThemeChanges(onChange: () => void): () => void {
	window.addEventListener("job-aggregator:theme-change", onChange);
	window.addEventListener("storage", onChange);
	return () => {
		window.removeEventListener("job-aggregator:theme-change", onChange);
		window.removeEventListener("storage", onChange);
	};
}

function getServerTheme(): Theme {
	return "light";
}

export default function ThemeToggle() {
	const theme = useSyncExternalStore(subscribeToThemeChanges, getCurrentTheme, getServerTheme);

	const toggleTheme = () => {
		const nextTheme: Theme = theme === "dark" ? "light" : "dark";
		document.documentElement.dataset.theme = nextTheme;
		document.documentElement.style.colorScheme = nextTheme;

		try {
			window.localStorage.setItem(STORAGE_KEY, nextTheme);
		} catch (error) {
			console.warn("Could not save the selected color theme", error);
		}
		window.dispatchEvent(new Event("job-aggregator:theme-change"));
	};

	const isDark = theme === "dark";

	return (
		<button
			type='button'
			onClick={toggleTheme}
			aria-label={`Switch to ${isDark ? "light" : "dark"} mode`}
			aria-pressed={isDark}
			title={`Switch to ${isDark ? "light" : "dark"} mode`}
			style={{
				display: "inline-flex",
				alignItems: "center",
				justifyContent: "center",
				gap: 8,
				minWidth: 42,
				height: 40,
				padding: "0 11px",
				borderRadius: "var(--radius)",
				border: "1px solid var(--border)",
				background: "var(--bg-surface)",
				color: "var(--text-secondary)",
				boxShadow: "var(--shadow-xs)",
				font: "inherit",
				fontSize: 12,
				fontWeight: 600,
				cursor: "pointer",
				transition: "background-color 0.2s ease, color 0.2s ease, border-color 0.2s ease",
			}}>
			{isDark ?
				<svg
					aria-hidden='true'
					width='17'
					height='17'
					viewBox='0 0 24 24'
					fill='none'
					stroke='currentColor'
					strokeWidth='1.8'
					strokeLinecap='round'
					strokeLinejoin='round'>
					<circle cx='12' cy='12' r='4' />
					<path d='M12 2v2m0 16v2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M2 12h2m16 0h2M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42' />
				</svg>
			:	<svg
					aria-hidden='true'
					width='17'
					height='17'
					viewBox='0 0 24 24'
					fill='none'
					stroke='currentColor'
					strokeWidth='1.8'
					strokeLinecap='round'
					strokeLinejoin='round'>
					<path d='M20.9 13A9 9 0 0 1 11 3.1 9 9 0 1 0 20.9 13Z' />
				</svg>
			}
			<span className='theme-toggle-label'>{isDark ? "Light" : "Dark"}</span>
		</button>
	);
}
