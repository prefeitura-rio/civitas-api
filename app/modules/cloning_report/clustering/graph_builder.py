"""
Graph Builder - Creates nodes and edges from suspicious pairs
"""
from __future__ import annotations

import pandas as pd
import numpy as np
from typing import List, Tuple, Dict, Any


class GraphBuilder:
    """Builds graph structures from suspicious detection pairs"""
    
    @staticmethod
    def create_nodes_and_edges(df_sus_day: pd.DataFrame) -> tuple[pd.DataFrame, List[Tuple[str, str, Dict]]]:
        """Creates nodes/edges from suspicious pairs for a single day"""
        GraphBuilder._validate_input(df_sus_day)
        
        df = GraphBuilder._prepare_timestamps(df_sus_day)
        nodes_rows, edges = [], []
        
        for k, r in df.reset_index(drop=True).iterrows():
            if GraphBuilder._should_skip_row(r):
                continue
                
            node_pair = GraphBuilder._create_node_pair(r, k)
            edge = GraphBuilder._create_edge(r, node_pair)
            
            nodes_rows.extend(node_pair['nodes'])
            edges.append(edge)
        
        return GraphBuilder._build_final_dataframe(nodes_rows), edges
    
    @staticmethod
    def _validate_input(df_sus_day: pd.DataFrame) -> None:
        """Validates input dataframe"""
        if df_sus_day is None or df_sus_day.empty:
            raise ValueError("Input dataframe cannot be empty")
    
    @staticmethod
    def _prepare_timestamps(df: pd.DataFrame) -> pd.DataFrame:
        """Prepares timestamp columns"""
        df = df.copy()
        df["Data_ts"] = pd.to_datetime(df.get("Data_ts", df.get("Data")), errors="coerce", utc=True)
        df["DataDestino"] = pd.to_datetime(df.get("DataDestino", df["Data_ts"]), errors="coerce", utc=True)
        return df
    
    @staticmethod
    def _should_skip_row(row: pd.Series) -> bool:
        """Checks if row should be skipped"""
        return pd.isna(row["Data_ts"]) or pd.isna(row["DataDestino"])
    
    @staticmethod
    def _create_node_id(ts, lat: float, lon: float, suffix: str) -> str:
        """Creates unique node identifier"""
        return f"{pd.to_datetime(ts).isoformat()}|{round(float(lat),6)}|{round(float(lon),6)}|{suffix}"
    
    @staticmethod
    def _create_node_pair(row: pd.Series, index: int) -> Dict[str, Any]:
        """Creates pair of nodes from row data"""
        lat1, lon1 = float(row["latitude_1"]), float(row["longitude_1"])
        lat2, lon2 = float(row["latitude_2"]), float(row["longitude_2"])
        
        u = GraphBuilder._create_node_id(row["Data_ts"], lat1, lon1, f"{index}a")
        v = GraphBuilder._create_node_id(row["DataDestino"], lat2, lon2, f"{index}b")
        
        return {
            'node_ids': (u, v),
            'nodes': [
                GraphBuilder._create_node_data(u, row["Data_ts"], lat1, lon1, row, "origem"),
                GraphBuilder._create_node_data(v, row["DataDestino"], lat2, lon2, row, "destino")
            ]
        }
    
    @staticmethod
    def _create_node_data(node_id: str, timestamp, lat: float, lon: float, row: pd.Series, prefix: str) -> Dict[str, Any]:
        """Creates node data dictionary"""
        return {
            "node_id": node_id,
            "datahora": timestamp,
            "latitude": lat,
            "longitude": lon,
            "logradouro": row.get("Origem" if prefix == "origem" else "Destino"),
            "bairro": row.get(f"bairro_{prefix}"),
            "localidade": row.get(f"localidade_{prefix}"),
            "velocidade": row.get(f"velocidade_{prefix}"),
        }
    
    @staticmethod
    def _create_edge(row: pd.Series, node_pair: Dict[str, Any]) -> Tuple[str, str, Dict[str, float]]:
        """Creates edge from row data"""
        u, v = node_pair['node_ids']
        return (u, v, {
            "km": float(row.get("Km", np.nan)),
            "dt_s": float(row.get("s", np.nan)),
            "kmh": float(row.get("Km/h", np.nan)),
        })
    
    @staticmethod
    def _build_final_dataframe(nodes_rows: List[Dict[str, Any]]) -> pd.DataFrame:
        """Builds final nodes dataframe"""
        return pd.DataFrame(nodes_rows).sort_values("datahora").reset_index(drop=True)