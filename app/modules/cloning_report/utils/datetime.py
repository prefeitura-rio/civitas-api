"""
datetime.py - Date and time operations
-------------------------------------
Single responsibility: Handle datetime conversions and formatting
"""

from typing import Any
import pandas as pd


class DateTimeService:
    """Handle datetime operations following SRP"""

    @staticmethod
    def to_utc_timestamp(value: Any) -> pd.Timestamp:
        """Convert value to UTC timestamp"""
        return pd.to_datetime(value, errors="coerce", utc=True)

    @staticmethod
    def format_safely(timestamp: Any, format_str: str = "%d/%m/%Y %H:%M:%S") -> str:
        """Format timestamp safely, handling timezone issues"""
        converted_ts = pd.to_datetime(timestamp, errors="coerce")

        if pd.isna(converted_ts):
            return ""

        return DateTimeService._try_format_with_timezone(converted_ts, format_str)

    @staticmethod
    def _try_format_with_timezone(timestamp: pd.Timestamp, format_str: str) -> str:
        """Try formatting with timezone conversion"""
        try:
            return timestamp.tz_convert(None).strftime(format_str)
        except Exception:
            return timestamp.strftime(format_str)
