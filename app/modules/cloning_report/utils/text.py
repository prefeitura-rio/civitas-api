# -*- coding: utf-8 -*-
"""
text.py — Text formatting operations
-----------------------------------
Single responsibility: Handle text formatting and abbreviations
"""
import pandas as pd


class TextFormatter:
    """Handle text formatting operations following SRP"""
    
    ABBREVIATIONS = {
        'AVENIDA': 'AV.', 
        'ESTRADA': 'ESTR.', 
        'NOSSA SENHORA': 'N. S.ª',
        'VIA EXPRESSA': 'V. EXPR.', 
        'PRESIDENTE': 'PRES.'
    }
    
    @classmethod
    def abbreviate_location(cls, text: str) -> str:
        """Apply standard abbreviations to location text"""
        if not cls._is_valid_text(text):
            return cls._handle_invalid_text(text)
            
        return cls._apply_abbreviations(text)
    
    @staticmethod
    def _is_valid_text(text: str) -> bool:
        """Check if text is a valid string"""
        return isinstance(text, str)
    
    @staticmethod
    def _handle_invalid_text(text: str) -> str:
        """Handle non-string or null text"""
        return "" if pd.isna(text) else str(text)
    
    @classmethod
    def _apply_abbreviations(cls, text: str) -> str:
        """Apply all abbreviation rules to text"""
        result = text
        for full_form, abbreviation in cls.ABBREVIATIONS.items():
            result = result.replace(full_form, abbreviation)
        return result