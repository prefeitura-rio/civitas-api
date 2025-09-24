"""High-performance parallel screenshot generation for HTML maps using threading."""

import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from ...utils.logging import get_logger

logger = get_logger()


try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    _HAVE_SELENIUM = True
except Exception:
    _HAVE_SELENIUM = False
    webdriver = None
    Options = None


@dataclass
class ScreenshotTask:
    """Represents a screenshot task."""

    html_path: str
    png_path: str
    width: int = 1280
    height: int = 800
    only_layers: list[str] | None = None


def setup_chrome_options():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--force-device-scale-factor=1")
    chrome_options.add_argument("--high-dpi-support=1")
    return chrome_options


def process_screenshot_task(task: ScreenshotTask) -> tuple[bool, str]:
    """
    Process a single screenshot task in a separate thread.
    This function will be executed by ThreadPoolExecutor workers.
    """
    thread_id = threading.get_ident()
    png_name = os.path.basename(task.png_path)

    if not _HAVE_SELENIUM:
        return False, f"Thread {thread_id}: Selenium/Chrome WebDriver not available"

    task_start = time.time()
    logger.info(f"Thread {thread_id}: Starting screenshot for {png_name}")

    chrome_options = setup_chrome_options()

    driver = None
    try:
        init_start = time.time()
        driver = webdriver.Chrome(options=chrome_options)
        init_time = time.time() - init_start
        logger.debug(f"Thread {thread_id}: WebDriver initialized in {init_time:.2f}s")

        # Configure window size to exact target dimensions
        driver.set_window_size(task.width, task.height)

        # Set viewport and ensure proper positioning
        driver.execute_script(f"""
            document.body.style.zoom = '100%';
            document.body.style.transform = 'scale(1)';
            document.body.style.margin = '0';
            document.body.style.padding = '0';
            document.documentElement.style.margin = '0';
            document.documentElement.style.padding = '0';

            let viewport = document.querySelector('meta[name="viewport"]');
            if (!viewport) {{
                viewport = document.createElement('meta');
                viewport.name = 'viewport';
                document.head.appendChild(viewport);
            }}
            viewport.content = 'width={task.width}, height={task.height}, initial-scale=1.0, user-scalable=no';
        """)

        load_start = time.time()
        driver.get(f"file:///{os.path.abspath(task.html_path)}")

        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, "leaflet-container"))
            )
            time.sleep(0.8)
        except Exception:
            time.sleep(1.5)

        load_time = time.time() - load_start
        logger.debug(f"Thread {thread_id}: Page loaded in {load_time:.2f}s")

        # Setup layers
        if task.only_layers is None:
            js = """
            const labels = document.querySelectorAll('.leaflet-control-layers-overlays label');
            labels.forEach(lb => {
                const cb = lb.querySelector('input[type="checkbox"]');
                if (cb && !cb.checked) cb.click();
            });
            """
        else:
            js = f"""
            const want = new Set({task.only_layers});
            const labels = document.querySelectorAll('.leaflet-control-layers-overlays label');
            labels.forEach(lb => {{
                const name = lb.textContent.trim();
                const cb = lb.querySelector('input[type="checkbox"]');
                if (!cb) return;
                const on = want.has(name);
                if (cb.checked && !on) cb.click();
                if (!cb.checked && on) cb.click();
            }});
            """
        driver.execute_script(js)

        driver.execute_script("""
            // Hide controls like legacy
            const cont = document.querySelector('.leaflet-control-container');
            if (cont) cont.style.display = 'none';
            const br = document.querySelector('.leaflet-bottom.leaflet-right');
            if (br) br.style.display = 'none';

            window.scrollTo(0,0);

            // CRITICAL: Add significant zoom-in for much better text readability
            const mapDiv = document.querySelector('.leaflet-container');
            if (mapDiv) {
                // Apply 1.5x zoom to make everything much more readable
                mapDiv.style.transform = 'scale(1.5)';
                mapDiv.style.transformOrigin = 'center center';
                mapDiv.style.fontSize = '18px';  // Even larger base font
                mapDiv.style.width = '100%';
                mapDiv.style.height = '100%';
                mapDiv.style.overflow = 'hidden';
                mapDiv.style.position = 'absolute';
                mapDiv.style.top = '0';
                mapDiv.style.left = '0';
                mapDiv.style.margin = '0';
                mapDiv.style.padding = '0';
            }

            // Ensure body doesn't show scroll bars and is properly positioned
            document.body.style.overflow = 'hidden';
            document.body.style.margin = '0';
            document.body.style.padding = '0';
            document.body.style.position = 'relative';
            document.documentElement.style.overflow = 'hidden';
            document.documentElement.style.margin = '0';
            document.documentElement.style.padding = '0';

            // Make popup text MUCH larger and more readable
            document.querySelectorAll('.leaflet-popup-content').forEach(popup => {
                popup.style.fontSize = '22px';  // Increased from 18px
                popup.style.fontWeight = 'bold';
                popup.style.lineHeight = '1.4';
            });

            // Make marker labels much more readable
            document.querySelectorAll('.leaflet-marker-icon').forEach(marker => {
                marker.style.transform += ' scale(1.2)';  // Reduced from 1.5 to 1.2
            });

            // Enhance tooltip text significantly
            document.querySelectorAll('.leaflet-tooltip').forEach(tooltip => {
                tooltip.style.fontSize = '20px';  // Increased from 16px
                tooltip.style.fontWeight = 'bold';
                tooltip.style.backgroundColor = 'rgba(255, 255, 255, 0.95)';
                tooltip.style.border = '2px solid #333';
                tooltip.style.borderRadius = '6px';
                tooltip.style.padding = '8px 12px';  // More padding
                tooltip.style.minWidth = '60px';
                tooltip.style.textAlign = 'center';
            });

            // Make speed labels MUCH more visible and larger
            document.querySelectorAll('div[title*="km/h"]').forEach(speedLabel => {
                speedLabel.style.fontSize = '16px';  // Reduced from 22px to 16px
                speedLabel.style.fontWeight = 'bold';
                speedLabel.style.color = '#000';
                speedLabel.style.textShadow = '1px 1px 3px white';
                speedLabel.style.backgroundColor = 'rgba(255, 255, 255, 0.9)';
                speedLabel.style.padding = '4px 8px';  // Reduced padding
                speedLabel.style.borderRadius = '4px';  // Smaller radius
                speedLabel.style.border = '1px solid #333';  // Thinner border
                speedLabel.style.minWidth = '60px';  // Smaller width
                speedLabel.style.textAlign = 'center';
                speedLabel.style.fontFamily = 'Arial, sans-serif';
            });
        """)
        time.sleep(0.3)

        driver.save_screenshot(task.png_path)

        total_time = time.time() - task_start
        logger.info(f"Thread {thread_id}: Completed {png_name} in {total_time:.2f}s")

        return (
            True,
            f"Thread {thread_id}: Screenshot saved to {task.png_path} in {total_time:.2f}s",
        )

    except Exception as e:
        total_time = time.time() - task_start
        logger.error(
            f"Thread {thread_id}: Failed {png_name} after {total_time:.2f}s - {str(e)}"
        )
        return False, f"Thread {thread_id}: Error - {str(e)}"

    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


class ScreenshotWorker:
    """Worker that maintains its own WebDriver instance for thread safety."""

    def __init__(self, worker_id: int):
        self.worker_id = worker_id
        self.driver = None

    def initialize(self):
        """Initialize WebDriver instance for this worker."""
        if not _HAVE_SELENIUM:
            raise RuntimeError("Selenium/Chrome WebDriver não disponível.")

        start_time = time.time()
        logger.info(f"🔧 Worker {self.worker_id}: Initializing WebDriver...")

        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-logging")
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--force-device-scale-factor=1")
        chrome_options.add_argument("--high-dpi-support=1")

        self.driver = webdriver.Chrome(options=chrome_options)

        init_time = time.time() - start_time
        logger.info(
            f"✅ Worker {self.worker_id}: WebDriver initialized in {init_time:.2f}s"
        )

    def take_screenshot(self, task: ScreenshotTask) -> tuple[bool, str]:
        """Take screenshot for a single task."""
        task_start = time.time()
        png_name = os.path.basename(task.png_path)

        logger.info(f"📸 Worker {self.worker_id}: Starting screenshot for {png_name}")

        if not self.driver:
            self.initialize()

        try:
            step_start = time.time()
            self._configure_window(task.width, task.height)
            logger.debug(
                f"   Worker {self.worker_id}: Window configured in {time.time() - step_start:.3f}s"
            )

            step_start = time.time()
            self._load_page(task.html_path)
            load_time = time.time() - step_start
            logger.info(f"   Worker {self.worker_id}: Page loaded in {load_time:.2f}s")

            step_start = time.time()
            self._setup_layers(task.only_layers)
            logger.debug(
                f"   Worker {self.worker_id}: Layers configured in {time.time() - step_start:.3f}s"
            )

            step_start = time.time()
            self._hide_controls()
            logger.debug(
                f"   Worker {self.worker_id}: Controls hidden in {time.time() - step_start:.3f}s"
            )

            step_start = time.time()
            self._capture_screenshot(task.png_path)
            capture_time = time.time() - step_start
            logger.debug(
                f"   Worker {self.worker_id}: Screenshot captured in {capture_time:.3f}s"
            )

            total_time = time.time() - task_start
            logger.info(
                f"✅ Worker {self.worker_id}: Completed {png_name} in {total_time:.2f}s"
            )

            return (
                True,
                f"Worker {self.worker_id}: Screenshot saved to {task.png_path} in {total_time:.2f}s",
            )

        except Exception as e:
            total_time = time.time() - task_start
            logger.error(
                f"❌ Worker {self.worker_id}: Failed {png_name} after {total_time:.2f}s - {str(e)}"
            )
            return False, f"Worker {self.worker_id}: Error - {str(e)}"

    def _configure_window(self, width: int, height: int):
        """Configure browser window size to match legacy behavior."""

        scaled_width = int(width * 1.2)
        scaled_height = int(height * 1.2)
        self.driver.set_window_size(scaled_width, scaled_height)

        self.driver.execute_script(f"""
            document.body.style.zoom = '100%';
            document.body.style.transform = 'scale(1)';
            // Set explicit viewport for better text rendering
            let viewport = document.querySelector('meta[name="viewport"]');
            if (!viewport) {{
                viewport = document.createElement('meta');
                viewport.name = 'viewport';
                document.head.appendChild(viewport);
            }}
            viewport.content = 'width={width}, height={height}, initial-scale=1.0, user-scalable=no';
        """)

    def _load_page(self, html_path: str):
        """Load HTML page and wait for it to be ready."""
        load_start = time.time()
        self.driver.get(f"file:///{os.path.abspath(html_path)}")
        get_time = time.time() - load_start
        logger.debug(
            f"      Worker {self.worker_id}: driver.get() took {get_time:.3f}s"
        )

        wait_start = time.time()
        try:
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, "leaflet-container"))
            )
            wait_time = time.time() - wait_start
            logger.debug(
                f"      Worker {self.worker_id}: Leaflet detected in {wait_time:.3f}s"
            )

            time.sleep(0.8)
            logger.debug(
                f"      Worker {self.worker_id}: Additional 0.8s wait (vs 2.5s legacy)"
            )
        except Exception:
            wait_time = time.time() - wait_start
            logger.debug(
                f"      Worker {self.worker_id}: Leaflet not detected after {wait_time:.3f}s, using fallback"
            )
            time.sleep(1.5)

    def _setup_layers(self, only_layers: list[str] | None):
        """Configure map layers visibility."""
        if only_layers is None:
            js = """
            const labels = document.querySelectorAll('.leaflet-control-layers-overlays label');
            labels.forEach(lb => {
                const cb = lb.querySelector('input[type="checkbox"]');
                if (cb && !cb.checked) cb.click();
            });
            """
        else:
            js = f"""
            const want = new Set({only_layers});
            const labels = document.querySelectorAll('.leaflet-control-layers-overlays label');
            labels.forEach(lb => {{
                const name = lb.textContent.trim();
                const cb = lb.querySelector('input[type="checkbox"]');
                if (!cb) return;
                const on = want.has(name);
                if (cb.checked && !on) cb.click();
                if (!cb.checked && on) cb.click();
            }});
            """

        self.driver.execute_script(js)

    def _hide_controls(self):
        """Hide map controls for cleaner screenshot and ensure proper zoom."""
        self.driver.execute_script("""
            // Hide controls like legacy
            const cont = document.querySelector('.leaflet-control-container');
            if (cont) cont.style.display = 'none';
            const br = document.querySelector('.leaflet-bottom.leaflet-right');
            if (br) br.style.display = 'none';

            // Ensure proper zoom and positioning like legacy
            window.scrollTo(0,0);

            // CRITICAL: Force readable text sizes for map elements
            const mapDiv = document.querySelector('.leaflet-container');
            if (mapDiv) {
                // Scale the entire map for better readability
                mapDiv.style.transform = 'scale(1.2)';
                mapDiv.style.transformOrigin = 'top left';
                mapDiv.style.fontSize = '16px';
            }

            // Make popup text MUCH larger and more readable
            document.querySelectorAll('.leaflet-popup-content').forEach(popup => {
                popup.style.fontSize = '22px';  // Increased from 18px
                popup.style.fontWeight = 'bold';
                popup.style.lineHeight = '1.4';
            });

            // Make marker labels much more readable
            document.querySelectorAll('.leaflet-marker-icon').forEach(marker => {
                marker.style.transform += ' scale(1.2)';  // Reduced from 1.5 to 1.2
            });

            // Enhance tooltip text significantly
            document.querySelectorAll('.leaflet-tooltip').forEach(tooltip => {
                tooltip.style.fontSize = '20px';  // Increased from 16px
                tooltip.style.fontWeight = 'bold';
                tooltip.style.backgroundColor = 'rgba(255, 255, 255, 0.95)';
                tooltip.style.border = '2px solid #333';
                tooltip.style.borderRadius = '6px';
                tooltip.style.padding = '8px 12px';  // More padding
                tooltip.style.minWidth = '60px';
                tooltip.style.textAlign = 'center';
            });

            // Make speed labels MUCH more visible and larger
            document.querySelectorAll('div[title*="km/h"]').forEach(speedLabel => {
                speedLabel.style.fontSize = '16px';  // Reduced from 22px to 16px
                speedLabel.style.fontWeight = 'bold';
                speedLabel.style.color = '#000';
                speedLabel.style.textShadow = '1px 1px 3px white';
                speedLabel.style.backgroundColor = 'rgba(255, 255, 255, 0.9)';
                speedLabel.style.padding = '4px 8px';  // Reduced padding
                speedLabel.style.borderRadius = '4px';  // Smaller radius
                speedLabel.style.border = '1px solid #333';  // Thinner border
                speedLabel.style.minWidth = '60px';  // Smaller width
                speedLabel.style.textAlign = 'center';
                speedLabel.style.fontFamily = 'Arial, sans-serif';
            });
        """)
        time.sleep(0.3)
        logger.debug(f"      Worker {self.worker_id}: Enhanced text rendering applied")

    def _capture_screenshot(self, png_path: str):
        """Capture and save screenshot with proper cropping."""

        temp_path = png_path.replace(".png", "_temp.png")
        self.driver.save_screenshot(temp_path)

        try:
            from PIL import Image

            with Image.open(temp_path) as img:
                img.save(png_path, optimize=True, quality=95)

            import os

            os.remove(temp_path)
        except ImportError:
            import os

            os.rename(temp_path, png_path)

    def cleanup(self):
        """Clean up WebDriver instance."""
        if self.driver:
            cleanup_start = time.time()
            logger.info(f"🧹 Worker {self.worker_id}: Cleaning up WebDriver...")
            try:
                self.driver.quit()
                cleanup_time = time.time() - cleanup_start
                logger.info(
                    f"✅ Worker {self.worker_id}: Cleanup completed in {cleanup_time:.2f}s"
                )
            except Exception as e:
                logger.warning(f"⚠️  Worker {self.worker_id}: Cleanup warning - {e}")
            self.driver = None


class ParallelScreenshotProcessor:
    """High-performance parallel screenshot processor using threading."""

    def __init__(self, max_workers: int = 6):
        self.max_workers = max_workers

    def process_batch(self, tasks: list[ScreenshotTask]) -> dict[str, any]:
        """Process multiple screenshot tasks in parallel using separate threads."""
        if not tasks:
            return {"success": 0, "failed": 0, "results": []}

        logger.info(
            f"Starting batch of {len(tasks)} screenshots with {self.max_workers} threads"
        )
        start_time = time.time()
        results = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            logger.debug(f"Thread pool created with max_workers={self.max_workers}")

            submission_start = time.time()
            future_to_task = {}
            for i, task in enumerate(tasks):
                png_name = os.path.basename(task.png_path)
                logger.debug(f"Submitting task {i + 1}/{len(tasks)} ({png_name})")
                future = executor.submit(process_screenshot_task, task)
                future_to_task[future] = task

            submission_time = time.time() - submission_start
            logger.debug(f"All {len(tasks)} tasks submitted in {submission_time:.3f}s")

            collection_start = time.time()
            completed_count = 0
            for future in as_completed(future_to_task):
                completed_count += 1
                task = future_to_task[future]
                png_name = os.path.basename(task.png_path)

                try:
                    success, message = future.result()
                    status = "SUCCESS" if success else "FAILED"
                    if success:
                        logger.debug(
                            f"Result {completed_count}/{len(tasks)}: {status} - {png_name}"
                        )
                    else:
                        logger.warning(
                            f"Result {completed_count}/{len(tasks)}: {status} - {png_name}"
                        )
                    results.append(
                        {"task": task, "success": success, "message": message}
                    )
                except Exception as e:
                    logger.error(
                        f"Result {completed_count}/{len(tasks)}: EXCEPTION - {png_name} - {str(e)}"
                    )
                    results.append(
                        {
                            "task": task,
                            "success": False,
                            "message": f"Exception: {str(e)}",
                        }
                    )

            collection_time = time.time() - collection_start
            logger.debug(f"All results collected in {collection_time:.2f}s")

        end_time = time.time()
        total_time = end_time - start_time

        success_count = sum(1 for r in results if r["success"])
        failed_count = len(results) - success_count
        avg_time = total_time / len(tasks) if tasks else 0

        return {
            "success": success_count,
            "failed": failed_count,
            "total_time": total_time,
            "results": results,
            "avg_time_per_screenshot": avg_time,
        }

    def process_single(self, task: ScreenshotTask) -> tuple[bool, str]:
        """Process single screenshot task using threading."""
        return process_screenshot_task(task)


def create_screenshot_processor(
    max_workers: int | None = None,
) -> ParallelScreenshotProcessor:
    """Create optimized threading screenshot processor with automatic worker count."""
    if max_workers is None:
        # For I/O bound tasks like screenshots, we can use more threads than CPU cores
        max_workers = min(threading.active_count() + 8, 16)
        logger.info(f"Auto-detected threading, using max_workers={max_workers}")
    else:
        logger.info(f"Using manual max_workers={max_workers}")

    return ParallelScreenshotProcessor(max_workers)
