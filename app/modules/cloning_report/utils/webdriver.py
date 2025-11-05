"""Utility helpers for Selenium WebDriver configuration used in cloning reports."""

import os
import shutil
from pathlib import Path
import platform
from threading import Lock

from loguru import logger
from selenium import webdriver
from selenium.webdriver.firefox.service import Service

_GECKODRIVER_LOCK = Lock()


def _resolve_firefox_binary() -> str | None:
    """Return the Firefox binary path if one of the known locations exists."""
    for candidate in ("/usr/bin/firefox-esr", "/usr/bin/firefox"):
        if Path(candidate).exists():
            return candidate
    env_candidate = os.getenv("FIREFOX_BINARY")
    if env_candidate and Path(env_candidate).exists():
        return env_candidate
    return None


def _resolve_geckodriver_binary() -> str | None:
    """
    Return a geckodriver path, mirroring existing Firefox usage in the project.
    Prefers GECKODRIVER_PATH or a binary already available on PATH.
    """
    with _GECKODRIVER_LOCK:
        env_candidate = os.getenv("GECKODRIVER_PATH")
        if env_candidate and Path(env_candidate).exists():
            return env_candidate

        which_path = shutil.which("geckodriver")
        if which_path:
            return which_path

        candidates = [
            "/usr/bin/geckodriver",
            "/usr/local/bin/geckodriver",
            "/usr/lib/firefox-esr/geckodriver",
        ]
        for candidate in candidates:
            if Path(candidate).exists():
                return candidate

        logger.error(
            "geckodriver não encontrado. Instale o binário ou defina GECKODRIVER_PATH."
        )
        return None


def setup_driver_options(width: int = 1800, height: int = 1400) -> webdriver.Firefox:
    """
    Configure and instantiate a Firefox WebDriver suitable for headless usage inside
    containers. Returns an already-created driver instance ready for use.
    """

    options = webdriver.firefox.options.Options()
    options.add_argument("--headless")
    options.add_argument(f"--width={width}")
    options.add_argument(f"--height={height}")

    arch = platform.machine().lower()
    use_explicit_service = arch not in ("x86_64", "amd64")

    if use_explicit_service:
        geckodriver_path = _resolve_geckodriver_binary()
        if not geckodriver_path:
            raise RuntimeError(
                "geckodriver não encontrado. Instale o binário ou defina GECKODRIVER_PATH."
            )
        service = Service(executable_path=geckodriver_path)
        driver = webdriver.Firefox(options=options, service=service)
    else:
        driver = webdriver.Firefox(options=options)

    return driver
