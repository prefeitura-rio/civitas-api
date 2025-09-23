"""Professional logging configuration for FastAPI deployment"""
import logging
import sys
from typing import Optional
from enum import Enum


class LogLevel(Enum):
    """Log levels for different deployment environments"""
    DEBUG = "DEBUG"
    INFO = "INFO" 
    WARNING = "WARNING"
    ERROR = "ERROR"
    PRODUCTION = "PRODUCTION"  # Minimal logging for prod


class CivitasLogger:
    """Centralized logging for Civitas Cloning Detection System"""
    
    def __init__(self, log_level: LogLevel = LogLevel.INFO):
        self.log_level = log_level
        self._setup_logger()
    
    def _setup_logger(self) -> None:
        """Configure logging based on environment"""
        self.logger = logging.getLogger("civitas_cloning")
        self.logger.setLevel(self._get_python_log_level())
        
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = self._get_formatter()
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def _get_python_log_level(self) -> int:
        """Convert LogLevel to Python logging level"""
        mapping = {
            LogLevel.DEBUG: logging.DEBUG,
            LogLevel.INFO: logging.INFO,
            LogLevel.WARNING: logging.WARNING, 
            LogLevel.ERROR: logging.ERROR,
            LogLevel.PRODUCTION: logging.WARNING
        }
        return mapping[self.log_level]
    
    def _get_formatter(self) -> logging.Formatter:
        """Get formatter based on log level"""
        if self.log_level == LogLevel.PRODUCTION:
            return logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        else:
            return logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')


# Global logger instance
_logger_instance: Optional[CivitasLogger] = None


def get_logger() -> logging.Logger:
    """Get the global logger instance"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = CivitasLogger()
    return _logger_instance.logger


def configure_logging(log_level: LogLevel) -> None:
    """Configure global logging level"""
    global _logger_instance
    _logger_instance = CivitasLogger(log_level)


# Convenience functions for different log levels
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