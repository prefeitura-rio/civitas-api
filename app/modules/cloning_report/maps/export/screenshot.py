"""Screenshot functionality for HTML maps with parallel processing support"""

import os
import time

# Import new parallel processor
from app.modules.cloning_report.maps.export.screenshot_batch import (
    ScreenshotTask,
    create_screenshot_processor,
)

# Optional Selenium import for backward compatibility
try:
    from app.modules.cloning_report.utils.webdriver import setup_driver_options

    _HAVE_SELENIUM = True
except Exception:
    _HAVE_SELENIUM = False
    setup_driver_options = None

# Import JavaScript utilities
from app.modules.cloning_report.utils.js_loader import (
    get_layer_control_script,
    get_basic_controls_script,
)


def take_html_screenshot(
    html_path: str,
    png_path: str,
    width: int = 1280,
    height: int = 800,
    only_layers: list[str] | None = None,
) -> None:
    """Take screenshot of HTML map file - now using optimized processor by default"""
    # Use optimized processor with auto-detected workers (much faster!)
    processor = create_screenshot_processor(max_workers=None)
    task = ScreenshotTask(html_path, png_path, width, height, only_layers)

    success, message = processor.process_single(task)
    if not success:
        raise RuntimeError(f"Screenshot failed: {message}")


def take_html_screenshots_parallel(
    tasks: list[ScreenshotTask], max_workers: int | None = None
) -> dict:
    """Take multiple screenshots in parallel - NEW HIGH-PERFORMANCE FUNCTION"""
    processor = create_screenshot_processor(max_workers)
    return processor.process_batch(tasks)


def take_html_screenshots_batch(
    html_paths: list[str],
    png_paths: list[str],
    width: int = 1280,
    height: int = 800,
    only_layers: list[str] | None = None,
    max_workers: int | None = None,
) -> dict:
    """Convenient batch screenshot function"""
    if len(html_paths) != len(png_paths):
        raise ValueError("html_paths and png_paths must have the same length")

    tasks = [
        ScreenshotTask(html_path, png_path, width, height, only_layers)
        for html_path, png_path in zip(html_paths, png_paths)
    ]

    return take_html_screenshots_parallel(tasks, max_workers)


# Legacy function for complete backward compatibility
def take_html_screenshot_legacy(
    html_path: str,
    png_path: str,
    width: int = 1280,
    height: int = 800,
    only_layers: list[str] | None = None,
) -> None:
    """Original implementation - kept for backward compatibility"""
    if not _HAVE_SELENIUM:
        raise RuntimeError("Selenium WebDriver não disponível.")

    driver = setup_driver_options(width, height)
    try:
        driver.get(f"file:///{os.path.abspath(html_path)}")
        time.sleep(2.5)

        # Setup layers using external JavaScript
        js = get_layer_control_script(only_layers)
        driver.execute_script(js)

        # Hide basic controls using external JavaScript
        js = get_basic_controls_script()
        driver.execute_script(js)
        time.sleep(0.4)
        driver.save_screenshot(png_path)
    finally:
        driver.quit()
