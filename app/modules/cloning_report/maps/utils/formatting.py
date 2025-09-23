"""Timestamp and data formatting utilities"""
import pandas as pd
from typing import Any


def format_timestamp(timestamp: Any) -> str:
    """Format timestamp for display (equivalent to _fmt_ts)"""
    t = pd.to_datetime(timestamp, errors="coerce")
    if pd.isna(t):
        return ""
    if t.tzinfo is not None:
        t = t.tz_convert(None)
    return t.strftime("%d/%m/%Y %H:%M:%S")


def normalize_timestamp(timestamp: Any) -> pd.Timestamp:
    """Normalize timestamp removing timezone and flooring to seconds (equivalent to _ts_norm)"""
    t = pd.to_datetime(timestamp, errors="coerce")
    if pd.isna(t):
        return t
    if t.tzinfo is not None:
        t = t.tz_convert(None)
    return t.floor("s")


def get_optional_field(row: pd.Series, *candidates: str, default: str = "") -> str:
    """Search for optional field (case-insensitive) (equivalent to _get_opt)"""
    for k in candidates:
        if k in row:
            v = row.get(k)
        else:
            v = next((row[c] for c in row.index if c.lower() == k.lower()), None)
        if v is not None and pd.notna(v):
            s = str(v).strip()
            if s:
                return s
    return default