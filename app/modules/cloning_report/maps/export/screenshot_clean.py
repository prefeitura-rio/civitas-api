"""Clean screenshot processor for FastAPI deployment using threading"""

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from collections.abc import Callable
from dataclasses import dataclass

from app.modules.cloning_report.utils.logging import get_logger
from app.modules.cloning_report.utils.progress import (
    ScreenshotProgressTracker,
    TaskProgress,
)
from app.modules.cloning_report.config import ScreenshotConfig
from app.modules.cloning_report.maps.export.screenshot_batch import (
    ScreenshotTask,
    process_screenshot_task,
)

logger = get_logger()


@dataclass
class ScreenshotResult:
    """Clean result structure for API responses"""

    success: bool
    screenshot_path: str
    processing_time: float
    error_message: str | None = None


class CleanScreenshotProcessor:
    """Production-ready screenshot processor for FastAPI"""

    def __init__(
        self,
        max_workers: int | None = None,
        progress_callback: Callable[[TaskProgress], None] | None = None,
    ):
        self.max_workers = max_workers or ScreenshotConfig.DEFAULT_MAX_WORKERS
        self.progress_tracker = ScreenshotProgressTracker(progress_callback)

    def process_screenshots(
        self, tasks: list[ScreenshotTask], task_id: str = "screenshot_batch"
    ) -> dict[str, any]:
        """Process screenshots with clean progress tracking"""
        if not tasks:
            return self._empty_result()

        logger.info(f"Processing {len(tasks)} screenshots")
        self.progress_tracker.start_batch(task_id, len(tasks))

        start_time = time.time()
        results = []

        try:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                future_to_task = {
                    executor.submit(process_screenshot_task, task): task
                    for task in tasks
                }

                # Collect results as they complete
                for future in as_completed(future_to_task):
                    task = future_to_task[future]

                    try:
                        success, message = future.result()
                        processing_time = time.time() - start_time

                        result = ScreenshotResult(
                            success=success,
                            screenshot_path=task.png_path,
                            processing_time=processing_time,
                            error_message=None if success else message,
                        )
                        results.append(result)

                        # Update progress
                        if success:
                            self.progress_tracker.screenshot_completed(
                                task_id,
                                os.path.basename(task.png_path),
                                processing_time,
                            )
                        else:
                            self.progress_tracker.screenshot_failed(
                                task_id, os.path.basename(task.png_path), message
                            )

                    except Exception as e:
                        error_msg = f"Execution error: {str(e)}"
                        logger.traceback(f"Screenshot failed: {error_msg}")

                        result = ScreenshotResult(
                            success=False,
                            screenshot_path=task.png_path,
                            processing_time=0.0,
                            error_message=error_msg,
                        )
                        results.append(result)

                        self.progress_tracker.screenshot_failed(
                            task_id, os.path.basename(task.png_path), error_msg
                        )

        except Exception as e:
            error_msg = f"Batch processing failed: {str(e)}"
            logger.traceback(error_msg)
            self.progress_tracker.fail_task(task_id, error_msg)
            return self._error_result(error_msg)

        # Complete and return results
        total_time = time.time() - start_time
        successful = sum(1 for r in results if r.success)

        self.progress_tracker.complete_task(
            task_id, f"Completed {successful}/{len(results)} screenshots"
        )

        logger.info(
            f"Batch completed: {successful}/{len(results)} successful in {total_time:.2f}s"
        )

        return self._format_results(results, total_time)

    def _empty_result(self) -> dict[str, any]:
        """Return empty result structure"""
        return {
            "success": True,
            "results": [],
            "summary": {
                "total_screenshots": 0,
                "successful": 0,
                "failed": 0,
                "total_time": 0.0,
                "avg_time_per_screenshot": 0.0,
            },
        }

    def _error_result(self, error_message: str) -> dict[str, any]:
        """Return error result structure"""
        return {
            "success": False,
            "error": error_message,
            "results": [],
            "summary": {
                "total_screenshots": 0,
                "successful": 0,
                "failed": 0,
                "total_time": 0.0,
                "avg_time_per_screenshot": 0.0,
            },
        }

    def _format_results(
        self, results: list[ScreenshotResult], total_time: float
    ) -> dict[str, any]:
        """Format results for API response"""
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        return {
            "success": len(failed) == 0,
            "results": [
                {
                    "success": r.success,
                    "path": r.screenshot_path,
                    "processing_time": round(r.processing_time, 2),
                    "error": r.error_message,
                }
                for r in results
            ],
            "summary": {
                "total_screenshots": len(results),
                "successful": len(successful),
                "failed": len(failed),
                "total_time": round(total_time, 2),
                "avg_time_per_screenshot": round(total_time / len(results), 2)
                if results
                else 0.0,
            },
        }


# Convenience function for backward compatibility
def process_screenshots_clean(
    tasks: list[ScreenshotTask],
    max_workers: int | None = None,
    progress_callback: Callable[[TaskProgress], None] | None = None,
) -> dict[str, any]:
    """Clean screenshot processing function"""
    processor = CleanScreenshotProcessor(max_workers, progress_callback)
    return processor.process_screenshots(tasks)
