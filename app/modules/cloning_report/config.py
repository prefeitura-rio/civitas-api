"""Configuration settings for Civitas Cloning Detection System"""

from enum import Enum


class Environment(Enum):
    """Deployment environments"""

    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class ScreenshotConfig:
    """Screenshot processing configuration"""

    # Performance settings
    DEFAULT_MAX_WORKERS = 8
    MAX_CPU_WORKERS = 8
    SCREENSHOT_TIMEOUT = 30  # seconds

    # Quality settings
    DEFAULT_WIDTH = 1280
    DEFAULT_HEIGHT = 800
    ZOOM_SCALE = 1.5

    # Verbose logging (can be disabled for production)
    VERBOSE_LOGGING = True
    SHOW_PROCESS_DETAILS = False  # Set to False for FastAPI
    SHOW_PERFORMANCE_METRICS = False  # Set to False for FastAPI


class APIConfig:
    """FastAPI server configuration"""

    # Logging
    LOG_LEVEL = "INFO"
    ENABLE_PERFORMANCE_LOGGING = True
    ENABLE_DETAILED_PROGRESS = True

    # Screenshot settings for API
    SCREENSHOT_PROGRESS_UPDATES = True
    BATCH_SIZE_LIMIT = 50  # Max screenshots per request
