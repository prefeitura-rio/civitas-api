"""
Track generator - Converts clustering labels to vehicle tracks
"""

from __future__ import annotations

import pandas as pd
import re


class TrackGenerator:
    """Converts clustering labels into chronological vehicle tracks"""

    @staticmethod
    def generate_tracks(
        df_nodes: pd.DataFrame, labels: dict[str, int]
    ) -> dict[str, pd.DataFrame]:
        """Converts labels to two chronological track tables"""
        if TrackGenerator._is_empty_input(df_nodes):
            return TrackGenerator._empty_result()

        prepared_df = TrackGenerator._prepare_dataframe(df_nodes, labels)
        track_tables = TrackGenerator._build_track_tables(prepared_df)

        return {
            "carro1": track_tables.get(0, pd.DataFrame()),
            "carro2": track_tables.get(1, pd.DataFrame()),
        }

    @staticmethod
    def _is_empty_input(df_nodes: pd.DataFrame) -> bool:
        """Checks if input is empty"""
        return df_nodes.empty

    @staticmethod
    def _empty_result() -> dict[str, pd.DataFrame]:
        """Returns empty result structure"""
        return {"carro1": pd.DataFrame(), "carro2": pd.DataFrame()}

    @staticmethod
    def _prepare_dataframe(
        df_nodes: pd.DataFrame, labels: dict[str, int]
    ) -> pd.DataFrame:
        """Prepares dataframe with cluster labels"""
        df = df_nodes.copy()
        df["cluster"] = df["node_id"].map(labels).astype("Int64")
        return df

    @staticmethod
    def _build_track_tables(df: pd.DataFrame) -> dict[int, pd.DataFrame]:
        """Builds track tables for each cluster"""
        tables = {}

        for cluster_id in (0, 1):
            cluster_df = df[df["cluster"] == cluster_id].copy()
            if cluster_df.empty:
                tables[cluster_id] = pd.DataFrame()
                continue

            processed_df = TrackGenerator._process_cluster_data(cluster_df)
            tables[cluster_id] = processed_df

        return tables

    @staticmethod
    def _process_cluster_data(cluster_df: pd.DataFrame) -> pd.DataFrame:
        """Processes data for a single cluster"""
        df = TrackGenerator._format_timestamps(cluster_df)
        df = TrackGenerator._add_location_columns(df)
        df = TrackGenerator._add_coordinate_columns(df)
        df = TrackGenerator._remove_duplicates(df)
        return TrackGenerator._select_final_columns(df)

    @staticmethod
    def _format_timestamps(df: pd.DataFrame) -> pd.DataFrame:
        """Formats datetime columns"""
        df["DataHora"] = pd.to_datetime(df["datahora"], errors="coerce")

        # Remove timezone if present
        if getattr(df["DataHora"].dt, "tz", None) is not None:
            df["DataHora"] = df["DataHora"].dt.tz_localize(None)

        # Format to string
        df["DataHora"] = df["DataHora"].dt.strftime("%Y-%m-%d %H:%M:%S")
        return (
            df.dropna(subset=["DataHora", "latitude", "longitude"])
            .sort_values("DataHora")
            .copy()
        )

    @staticmethod
    def _add_location_columns(df: pd.DataFrame) -> pd.DataFrame:
        """Adds location-related columns"""
        df["Local"] = df.apply(TrackGenerator._pick_location, axis=1)
        df["Bairro"] = df.get("bairro", pd.Series(index=df.index, dtype="object"))
        df["Sentido"] = df.get(
            "logradouro", pd.Series(index=df.index, dtype="object")
        ).map(TrackGenerator._extract_direction)
        return df

    @staticmethod
    def _pick_location(row: pd.Series) -> str:
        """Picks best location string from available fields"""
        logradouro = str(row.get("logradouro") or "").strip()
        if logradouro:
            return logradouro
        return str(row.get("localidade") or "").strip()

    @staticmethod
    def _extract_direction(location_str: str) -> str:
        """Extracts direction term from location string"""
        if not isinstance(location_str, str):
            return "N/A"

        # Try hyphen patterns first
        match = re.search(r"-\s*([^\-]+?)\s*-", location_str)
        if match:
            return (
                match.group(1)
                .strip()
                .upper()
                .replace("SENTIDO ", "")
                .replace("SENT ", "")
            )

        # Try SENTIDO/SENT patterns
        match = re.search(
            r"(?:SENTIDO|SENT\.?|SENT\s*:)\s*([A-ZÁÉÍÓÚÂÊÔÃÕÇ0-9\/\s]+)",
            location_str,
            flags=re.IGNORECASE,
        )
        if match:
            return match.group(1).strip().upper()

        return "N/A"

    @staticmethod
    def _add_coordinate_columns(df: pd.DataFrame) -> pd.DataFrame:
        """Adds rounded coordinate columns"""
        df["Latitude"] = pd.to_numeric(df["latitude"], errors="coerce").round(6)
        df["Longitude"] = pd.to_numeric(df["longitude"], errors="coerce").round(6)
        return df

    @staticmethod
    def _remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
        """Removes exact duplicate entries"""
        return df.drop_duplicates(
            subset=["DataHora", "Latitude", "Longitude"], keep="first"
        )

    @staticmethod
    def _select_final_columns(df: pd.DataFrame) -> pd.DataFrame:
        """Selects final columns for output"""
        final_cols = ["DataHora", "Local", "Bairro", "Sentido", "Latitude", "Longitude"]
        return df[[col for col in final_cols if col in df.columns]]
