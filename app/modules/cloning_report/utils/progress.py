"""Professional progress tracking for FastAPI deployment"""

from typing import Any
from collections.abc import Callable
import time
from dataclasses import dataclass
from enum import Enum


class TaskStatus(Enum):
    """Task execution statuses"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskProgress:
    """Progress information for a task"""

    task_id: str
    status: TaskStatus
    progress_percent: float
    message: str
    started_at: float | None = None
    completed_at: float | None = None
    details: dict[str, Any] | None = None


class ProgressTracker:
    """Clean progress tracking for FastAPI endpoints"""

    def __init__(self, callback: Callable[[TaskProgress], None] | None = None):
        self.callback = callback
        self.tasks: dict[str, TaskProgress] = {}

    def start_task(self, task_id: str, message: str) -> None:
        """Start tracking a task"""
        progress = TaskProgress(
            task_id=task_id,
            status=TaskStatus.RUNNING,
            progress_percent=0.0,
            message=message,
            started_at=time.time(),
        )
        self.tasks[task_id] = progress
        self._notify(progress)

    def update_progress(
        self,
        task_id: str,
        percent: float,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Update task progress"""
        if task_id not in self.tasks:
            return

        task = self.tasks[task_id]
        task.progress_percent = min(100.0, max(0.0, percent))
        task.message = message
        if details:
            task.details = details

        self._notify(task)

    def complete_task(self, task_id: str, message: str = "Completed") -> None:
        """Mark task as completed"""
        if task_id not in self.tasks:
            return

        task = self.tasks[task_id]
        task.status = TaskStatus.COMPLETED
        task.progress_percent = 100.0
        task.message = message
        task.completed_at = time.time()

        self._notify(task)

    def fail_task(self, task_id: str, error_message: str) -> None:
        """Mark task as failed"""
        if task_id not in self.tasks:
            return

        task = self.tasks[task_id]
        task.status = TaskStatus.FAILED
        task.message = f"Failed: {error_message}"
        task.completed_at = time.time()

        self._notify(task)

    def get_task_status(self, task_id: str) -> TaskProgress | None:
        """Get current task status"""
        return self.tasks.get(task_id)

    def _notify(self, progress: TaskProgress) -> None:
        """Notify callback if provided"""
        if self.callback:
            self.callback(progress)


class ScreenshotProgressTracker(ProgressTracker):
    """Specialized progress tracker for screenshot operations"""

    def __init__(self, callback: Callable[[TaskProgress], None] | None = None):
        super().__init__(callback)
        self.screenshot_stats = {
            "total": 0,
            "completed": 0,
            "failed": 0,
            "avg_time": 0.0,
        }

    def start_batch(self, task_id: str, total_screenshots: int) -> None:
        """Start tracking a screenshot batch"""
        self.screenshot_stats["total"] = total_screenshots
        self.screenshot_stats["completed"] = 0
        self.screenshot_stats["failed"] = 0

        self.start_task(task_id, f"Processing {total_screenshots} screenshots")

    def screenshot_completed(
        self, task_id: str, screenshot_name: str, time_taken: float
    ) -> None:
        """Mark one screenshot as completed"""
        self.screenshot_stats["completed"] += 1
        total = self.screenshot_stats["total"]
        completed = self.screenshot_stats["completed"]

        # Update average time
        prev_avg = self.screenshot_stats["avg_time"]
        self.screenshot_stats["avg_time"] = (
            prev_avg * (completed - 1) + time_taken
        ) / completed

        percent = (completed / total) * 100
        message = f"Completed {completed}/{total} screenshots"

        details = {
            "last_screenshot": screenshot_name,
            "time_taken": round(time_taken, 2),
            "avg_time": round(self.screenshot_stats["avg_time"], 2),
            "remaining": total - completed,
        }

        self.update_progress(task_id, percent, message, details)

    def screenshot_failed(self, task_id: str, screenshot_name: str, error: str) -> None:
        """Mark one screenshot as failed"""
        self.screenshot_stats["failed"] += 1
        total = self.screenshot_stats["total"]
        completed = self.screenshot_stats["completed"]
        failed = self.screenshot_stats["failed"]

        percent = ((completed + failed) / total) * 100
        message = f"Progress {completed + failed}/{total} (✅{completed} ❌{failed})"

        details = {
            "failed_screenshot": screenshot_name,
            "error": error,
            "success_rate": round((completed / (completed + failed)) * 100, 1)
            if (completed + failed) > 0
            else 0,
        }

        self.update_progress(task_id, percent, message, details)
