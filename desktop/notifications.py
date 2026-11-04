"""Windows toast notifications for the packaged desktop application."""

import logging

logger = logging.getLogger(__name__)


def show_windows_notification(title: str, message: str) -> None:
    """Display a native Windows notification through the Winotify package."""
    try:
        from winotify import Notification

        Notification(app_id="Job Aggregator", title=title, msg=message).show()
    except Exception:
        logger.exception("Could not display Windows notification")
        raise


class DesktopNotificationAPI:
    """Methods exposed to the frontend through PyWebView's JavaScript bridge."""

    def notify_aggregation_complete(self, new_jobs: int, source_count: int) -> None:
        job_label = "job" if new_jobs == 1 else "jobs"
        source_label = "source" if source_count == 1 else "sources"
        show_windows_notification(
            "Job aggregation complete",
            f"Found {new_jobs} new {job_label} from {source_count} {source_label}.",
        )

    def send_test_notification(self) -> None:
        show_windows_notification(
            "Job Aggregator notifications",
            "Windows notifications are working.",
        )
