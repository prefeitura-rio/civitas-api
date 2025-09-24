"""
preprocessing.py - Data preprocessing for detection
-------------------------------------------------
Single responsibility: Preprocess detection data
"""

import pandas as pd


class DetectionPreprocessor:
    """Handles data preprocessing for cloning detection"""

    @staticmethod
    def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """Prepare dataframe for detection processing"""
        preprocessed_df = DetectionPreprocessor._apply_base_preprocessing(df)
        enhanced_df = DetectionPreprocessor._add_location_columns(preprocessed_df)
        return DetectionPreprocessor._sort_by_time(enhanced_df)

    @staticmethod
    def _apply_base_preprocessing(df: pd.DataFrame) -> pd.DataFrame:
        """Apply base preprocessing logic"""
        return DetectionPreprocessor._preprocess_dataframe(df)

    @staticmethod
    def _preprocess_dataframe(
        df: pd.DataFrame, dedup_same_loc_time: bool = True
    ) -> pd.DataFrame:
        """Core preprocessing logic"""
        DetectionPreprocessor._validate_required_columns(df)
        dfx = DetectionPreprocessor._convert_datetime_columns(df)
        dfx = DetectionPreprocessor._clean_text_columns(dfx)
        dfx = DetectionPreprocessor._convert_numeric_columns(dfx)
        return DetectionPreprocessor._handle_duplicates(dfx, dedup_same_loc_time)

    @staticmethod
    def _add_location_columns(df: pd.DataFrame) -> pd.DataFrame:
        """Add formatted location columns"""
        df = df.copy()
        df["logradouro (codcet)"] = (
            df["logradouro"].astype(str) + " (" + df["codcet"].astype(str) + ")"
        )
        df["localidade (codcet)"] = (
            df["localidade"].astype(str) + " (" + df["codcet"].astype(str) + ")"
        )
        return df

    @staticmethod
    def _validate_required_columns(df: pd.DataFrame) -> None:
        """Validate required columns exist"""
        if df.empty:
            raise ValueError("No data found for the specified plate and date range")
        if "datahora" not in df.columns:
            raise KeyError("Column 'datahora' not found in DataFrame")

    @staticmethod
    def _convert_datetime_columns(df: pd.DataFrame) -> pd.DataFrame:
        """Convert datetime columns and remove invalid entries"""
        dfx = df.copy()
        dfx["datahora"] = pd.to_datetime(dfx["datahora"], errors="coerce")
        return dfx.dropna(subset=["datahora"]).copy()

    @staticmethod
    def _clean_text_columns(df: pd.DataFrame) -> pd.DataFrame:
        """Clean and strip text columns"""
        dfx = df.copy()
        for col in ("logradouro", "bairro", "localidade"):
            if col in dfx.columns:
                dfx[col] = dfx[col].astype(str).str.strip()
        return dfx

    @staticmethod
    def _convert_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
        """Convert numeric columns with error handling"""
        dfx = df.copy()
        if "velocidade" in dfx.columns:
            dfx["velocidade"] = pd.to_numeric(dfx["velocidade"], errors="coerce")
        return dfx

    @staticmethod
    def _handle_duplicates(df: pd.DataFrame, dedup_same_loc_time: bool) -> pd.DataFrame:
        """Handle duplicate records based on configuration"""
        if dedup_same_loc_time and {"latitude", "longitude"}.issubset(df.columns):
            return DetectionPreprocessor._remove_location_time_duplicates(df)
        return df.sort_values("datahora").reset_index(drop=True)

    @staticmethod
    def _remove_location_time_duplicates(df: pd.DataFrame) -> pd.DataFrame:
        """Remove duplicates based on location and time"""
        dfx = df.sort_values("datahora").copy()
        dup = dfx.duplicated(subset=["datahora", "latitude", "longitude"], keep="first")
        return dfx[~dup].reset_index(drop=True)

    @staticmethod
    def _sort_by_time(df: pd.DataFrame) -> pd.DataFrame:
        """Sort dataframe by datetime"""
        return df.sort_values("datahora").reset_index(drop=True)
