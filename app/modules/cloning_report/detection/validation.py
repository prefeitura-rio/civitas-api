# -*- coding: utf-8 -*-
"""
validation.py — Input validation for detection pipeline
----------------------------------------------------
Single responsibility: Validate detection input data
"""
from typing import List
import pandas as pd


class DetectionValidator:
    """Validates input data for cloning detection"""
    
    REQUIRED_COLUMNS = ['datahora', 'latitude', 'longitude', 'logradouro', 'codcet']
    
    @classmethod
    def validate_dataframe(cls, df: pd.DataFrame) -> None:
        """Validate that dataframe has required columns"""
        missing_columns = cls._find_missing_columns(df)
        
        if missing_columns:
            raise KeyError(f"Missing required columns: {', '.join(missing_columns)}")
    
    @classmethod
    def _find_missing_columns(cls, df: pd.DataFrame) -> List[str]:
        """Find missing required columns"""
        return [col for col in cls.REQUIRED_COLUMNS if col not in df.columns]