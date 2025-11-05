"""Utility helpers for Selenium WebDriver configuration used in cloning reports."""

from pathlib import Path

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service


def _resolve_firefox_binary() -> str | None:
    """Return the Firefox binary path if one of the known locations exists."""
    for candidate in ("/usr/bin/firefox-esr", "/usr/bin/firefox"):
        if Path(candidate).exists():
            return candidate
    return None


def _resolve_geckodriver_binary() -> str:
    """Return a valid geckodriver path or raise a descriptive error."""
    candidates = (
        "/usr/bin/geckodriver",
        "/usr/local/bin/geckodriver",
        "/usr/lib/firefox-esr/geckodriver",
    )
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    raise RuntimeError(
        "Nenhum geckodriver foi encontrado nos caminhos esperados. "
        "Verifique se o pacote 'geckodriver' está instalado no container."
    )


def setup_driver_options(width: int = 1800, height: int = 1400) -> webdriver.Firefox:
    """
    Configure and instantiate a Firefox WebDriver suitable for headless usage inside
    containers. Returns an already-created driver instance ready for use.
    """

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(f"--width={width}")
    options.add_argument(f"--height={height}")

    firefox_binary = _resolve_firefox_binary()
    if firefox_binary:
        options.binary_location = firefox_binary

    geckodriver_path = _resolve_geckodriver_binary()
    service = Service(executable_path=geckodriver_path)

    driver = webdriver.Firefox(service=service, options=options)
    driver.set_window_size(width, height)

    return driver
