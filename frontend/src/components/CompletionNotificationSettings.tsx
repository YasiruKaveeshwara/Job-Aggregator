"use client";

import { useCallback, useEffect, useState } from "react";
import { getDesktopNotificationAPI } from "@/lib/notifications";

type NotificationMode = "checking" | "desktop" | "browser" | "unsupported";

export default function CompletionNotificationSettings() {
	const [mode, setMode] = useState<NotificationMode>("checking");
	const [permission, setPermission] = useState<NotificationPermission | null>(null);
	const [busy, setBusy] = useState(false);
	const [message, setMessage] = useState<string | null>(null);
	const [error, setError] = useState<string | null>(null);

	const refreshMode = useCallback(() => {
		if (getDesktopNotificationAPI()) {
			setMode("desktop");
			return;
		}
		if (typeof window === "undefined" || !window.isSecureContext || !("Notification" in window)) {
			setMode("unsupported");
			return;
		}
		setMode("browser");
		setPermission(Notification.permission);
	}, []);

	useEffect(() => {
		const timeoutId = window.setTimeout(refreshMode, 0);
		window.addEventListener("pywebviewready", refreshMode);
		return () => {
			window.clearTimeout(timeoutId);
			window.removeEventListener("pywebviewready", refreshMode);
		};
	}, [refreshMode]);

	async function enableBrowserNotifications() {
		setBusy(true);
		setError(null);
		setMessage(null);
		try {
			const result = await Notification.requestPermission();
			setPermission(result);
			if (result === "granted") {
				new Notification("Job Aggregator notifications", {
					body: "You will be notified when job aggregation finishes.",
				});
				setMessage("Browser notifications enabled.");
			}
		} catch (reason) {
			setError(reason instanceof Error ? reason.message : String(reason));
		} finally {
			setBusy(false);
		}
	}

	async function sendDesktopTest() {
		setBusy(true);
		setError(null);
		setMessage(null);
		try {
			const api = getDesktopNotificationAPI();
			if (!api) throw new Error("The Windows notification bridge is not ready.");
			await api.send_test_notification();
			setMessage("A test Windows notification was sent.");
		} catch (reason) {
			setError(reason instanceof Error ? reason.message : String(reason));
		} finally {
			setBusy(false);
		}
	}

	return (
		<div
			style={{
				marginBottom: 18,
				padding: "14px 16px",
				display: "flex",
				alignItems: "center",
				justifyContent: "space-between",
				gap: 16,
				flexWrap: "wrap",
				border: "1px solid var(--border)",
				borderRadius: "var(--radius)",
				background: "var(--bg-base)",
			}}>
			<div style={{ flex: "1 1 360px" }}>
				<h3 style={{ fontSize: 13, marginBottom: 3 }}>Aggregation completion notifications</h3>
				{mode === "checking" && (
					<p style={{ fontSize: 12, color: "var(--text-secondary)" }}>Checking notification support...</p>
				)}
				{mode === "desktop" && (
					<p style={{ fontSize: 12, color: "var(--text-secondary)" }}>
						Windows notifications are used in the desktop app. If they do not appear, allow notifications for Job
						Aggregator in Windows Settings.
					</p>
				)}
				{mode === "browser" && permission === "granted" && (
					<p style={{ fontSize: 12, color: "var(--green)" }}>Browser notifications are enabled.</p>
				)}
				{mode === "browser" && permission === "default" && (
					<p style={{ fontSize: 12, color: "var(--text-secondary)" }}>
						Allow browser notifications to be notified when fetching and processing finishes.
					</p>
				)}
				{mode === "browser" && permission === "denied" && (
					<p style={{ fontSize: 12, color: "var(--amber)" }}>
						Notifications are blocked by the browser. Allow them for this site in your browser&apos;s site settings.
					</p>
				)}
				{mode === "unsupported" && (
					<p style={{ fontSize: 12, color: "var(--text-secondary)" }}>
						Notifications require a supported browser and a secure context (HTTPS or localhost).
					</p>
				)}
				{message && (
					<p role='status' style={{ marginTop: 4, fontSize: 12, color: "var(--green)" }}>
						{message}
					</p>
				)}
				{error && (
					<p role='alert' style={{ marginTop: 4, fontSize: 12, color: "var(--red)" }}>
						{error}
					</p>
				)}
			</div>

			{mode === "desktop" && (
				<button type='button' className='btn btn-ghost btn-sm' disabled={busy} onClick={() => void sendDesktopTest()}>
					{busy ? "Sending..." : "Send test notification"}
				</button>
			)}
			{mode === "browser" && permission === "default" && (
				<button
					type='button'
					className='btn btn-primary btn-sm'
					disabled={busy}
					onClick={() => void enableBrowserNotifications()}>
					{busy ? "Requesting..." : "Enable browser notifications"}
				</button>
			)}
		</div>
	);
}
