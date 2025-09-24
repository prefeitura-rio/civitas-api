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
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    _HAVE_SELENIUM = True
except Exception:
    _HAVE_SELENIUM = False
    webdriver = None
    Options = None


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
        raise RuntimeError("Selenium/Chrome WebDriver não disponível.")

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(f"--window-size={width},{height}")

    driver = webdriver.Chrome(options=chrome_options)
    try:
        driver.get(f"file:///{os.path.abspath(html_path)}")
        time.sleep(2.5)

        if only_layers is None:
            js = """
            const labels = document.querySelectorAll('.leaflet-control-layers-overlays label');
            labels.forEach(lb => { const cb = lb.querySelector('input[type="checkbox"]'); if (cb && !cb.checked) cb.click(); });
            """
        else:
            js = f"""
            const want = new Set({only_layers});
            const labels = document.querySelectorAll('.leaflet-control-layers-overlays label');
            labels.forEach(lb => {{ const name = lb.textContent.trim(); const cb = lb.querySelector('input[type="checkbox"]'); if (!cb) return; const on = want.has(name); if (cb.checked && !on) cb.click(); if (!cb.checked && on) cb.click(); }});
            """

        driver.execute_script(js)
        driver.execute_script("""
            const cont = document.querySelector('.leaflet-control-container'); if (cont) cont.style.display = 'none';
            const br = document.querySelector('.leaflet-bottom.leaflet-right'); if (br) br.style.display = 'none';
            window.scrollTo(0,0);
        """)
        time.sleep(0.4)
        driver.save_screenshot(png_path)
    finally:
        driver.quit()
