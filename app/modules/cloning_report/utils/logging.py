"""Logging configuration using loguru for consistency with main app"""

from loguru import logger
from enum import Enum


class LogLevel(Enum):
    """Log levels for different deployment environments"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    PRODUCTION = "PRODUCTION"


def get_logger():
    """Get the loguru logger instance with civitas_cloning context"""
    return logger.bind(name="civitas_cloning")


def configure_logging(log_level: LogLevel) -> None:
    """Configure global logging level - now handled by main app"""
    pass


def log_info(message: str) -> None:
    """Log info message"""
    get_logger().info(message)


def log_warning(message: str) -> None:
    """Log warning message"""
    get_logger().warning(message)


def log_error(message: str) -> None:
    """Log error message"""
    get_logger().error(message)


def log_debug(message: str) -> None:
    """Log debug message"""
    get_logger().debug(message)
