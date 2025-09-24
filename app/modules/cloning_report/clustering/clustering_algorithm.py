"""
Clustering algorithms for vehicle separation
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from app.modules.cloning_report.utils import haversine_km, VMAX_KMH


class GreedyTemporalClustering:
    """Temporal-based greedy clustering algorithm"""

    @staticmethod
    def cluster_nodes(
        df_nodes: pd.DataFrame,
        edges: list[tuple[str, str, dict]],
        vmax_kmh: float = VMAX_KMH,
    ) -> dict[str, int]:
        """Labels nodes {0,1} in temporal order; satisfies cannot-link constraints"""
        opposite_map = GreedyTemporalClustering._build_opposite_map(edges)
        nodes_sorted = GreedyTemporalClustering._sort_nodes_by_time(df_nodes)
        nodes_idx = df_nodes.set_index("node_id")

        labels: dict[str, int] = {}
        last_by_label = {0: None, 1: None}

        for node_id in nodes_sorted:
            best_label = GreedyTemporalClustering._find_best_label(
                node_id, opposite_map, labels, last_by_label, nodes_idx, vmax_kmh
            )
            labels[node_id] = best_label
            last_by_label[best_label] = node_id

        return labels

    @staticmethod
    def _build_opposite_map(edges: list[tuple[str, str, dict]]) -> dict[str, str]:
        """Builds mapping of connected nodes"""
        opposite = {}
        for u, v, _ in edges:
            opposite[u] = v
            opposite[v] = u
        return opposite

    @staticmethod
    def _sort_nodes_by_time(df_nodes: pd.DataFrame) -> list[str]:
        """Sorts nodes by timestamp"""
        return df_nodes.sort_values("datahora")["node_id"].tolist()

    @staticmethod
    def _find_best_label(
        node_id: str,
        opposite_map: dict[str, str],
        labels: dict[str, int],
        last_by_label: dict[int, str],
        nodes_idx: pd.DataFrame,
        vmax_kmh: float,
    ) -> int:
        """Finds optimal label for node"""
        forced_label = GreedyTemporalClustering._get_forced_label(
            node_id, opposite_map, labels
        )
        candidates = [forced_label] if forced_label is not None else [0, 1]

        best_label, best_cost, best_feasible = None, float("inf"), False

        for candidate in candidates:
            feasible, speed = GreedyTemporalClustering._check_speed_feasibility(
                last_by_label[candidate], node_id, nodes_idx, vmax_kmh
            )
            cost = speed if feasible else (speed + 1e6)

            if GreedyTemporalClustering._is_better_choice(
                feasible, cost, best_feasible, best_cost
            ):
                best_label, best_cost, best_feasible = candidate, cost, feasible

        return best_label if best_label is not None else 0

    @staticmethod
    def _get_forced_label(
        node_id: str, opposite_map: dict[str, str], labels: dict[str, int]
    ) -> int:
        """Gets forced label based on cannot-link constraints"""
        if node_id in opposite_map and opposite_map[node_id] in labels:
            return 1 - labels[opposite_map[node_id]]
        return None

    @staticmethod
    def _check_speed_feasibility(
        prev_id: str, cur_id: str, nodes_idx: pd.DataFrame, vmax_kmh: float
    ) -> tuple[bool, float]:
        """Checks if speed between nodes is feasible"""
        if prev_id is None:
            return True, 0.0

        prev_node = nodes_idx.loc[prev_id]
        cur_node = nodes_idx.loc[cur_id]

        dt_s = (
            pd.to_datetime(cur_node["datahora"]) - pd.to_datetime(prev_node["datahora"])
        ).total_seconds()
        if dt_s <= 0:
            return True, 0.0

        distance_km = haversine_km(
            prev_node["latitude"],
            prev_node["longitude"],
            cur_node["latitude"],
            cur_node["longitude"],
        )
        speed = distance_km / (dt_s / 3600.0)
        return (speed <= vmax_kmh), speed

    @staticmethod
    def _is_better_choice(
        feasible: bool, cost: float, best_feasible: bool, best_cost: float
    ) -> bool:
        """Determines if current choice is better than best so far"""
        if feasible and (not best_feasible or cost < best_cost):
            return True
        return not best_feasible and cost < best_cost


class SpatialKMeansClustering:
    """Spatial K-means based clustering with local search repair"""

    @staticmethod
    def cluster_nodes(
        df_nodes: pd.DataFrame, edges: list[tuple[str, str, dict]], seed: int = 123
    ) -> dict[str, int]:
        """KMeans k=2 on (lat,lon) followed by local search to reduce violations"""
        initial_labels = SpatialKMeansClustering._perform_kmeans(df_nodes, seed)
        return SpatialKMeansClustering._repair_with_local_search(
            initial_labels, edges, df_nodes
        )

    @staticmethod
    def _perform_kmeans(df_nodes: pd.DataFrame, seed: int) -> dict[str, int]:
        """Performs K-means clustering on coordinates"""
        coordinates = df_nodes[["latitude", "longitude"]].to_numpy()

        try:
            from sklearn.cluster import KMeans

            kmeans = KMeans(n_clusters=2, n_init=10, random_state=seed)
            labels_array = kmeans.fit_predict(coordinates)
        except Exception:
            labels_array = SpatialKMeansClustering._fallback_kmeans(coordinates, seed)

        return {
            node_id: int(label)
            for node_id, label in zip(df_nodes["node_id"], labels_array)
        }

    @staticmethod
    def _fallback_kmeans(coordinates: np.ndarray, seed: int) -> np.ndarray:
        """Manual K-means implementation as fallback"""
        if len(coordinates) < 2:
            return np.zeros(len(coordinates), dtype=int)

        rng = np.random.default_rng(seed)
        centroids = coordinates[
            rng.choice(len(coordinates), size=2, replace=False)
        ].astype(float)

        for _ in range(30):
            distances_0 = np.linalg.norm(coordinates - centroids[0], axis=1)
            distances_1 = np.linalg.norm(coordinates - centroids[1], axis=1)
            labels = (distances_1 < distances_0).astype(int)

            SpatialKMeansClustering._update_centroids(centroids, coordinates, labels)

        return labels

    @staticmethod
    def _update_centroids(
        centroids: np.ndarray, coordinates: np.ndarray, labels: np.ndarray
    ) -> None:
        """Updates centroid positions"""
        for k in (0, 1):
            mask = labels == k
            if mask.any():
                centroids[k] = coordinates[mask].mean(axis=0)

    @staticmethod
    def _repair_with_local_search(
        labels: dict[str, int],
        edges: list[tuple[str, str, dict]],
        df_nodes: pd.DataFrame,
    ) -> dict[str, int]:
        """Improves clustering through local search"""
        current_violations = SpatialKMeansClustering._count_violations(labels, edges)
        improved = True

        while improved:
            improved = False
            for node_id in list(df_nodes["node_id"]):
                if SpatialKMeansClustering._try_flip_node(
                    node_id, labels, edges, current_violations
                ):
                    current_violations = SpatialKMeansClustering._count_violations(
                        labels, edges
                    )
                    improved = True

        return labels

    @staticmethod
    def _count_violations(
        labels: dict[str, int], edges: list[tuple[str, str, dict]]
    ) -> int:
        """Counts constraint violations"""
        return sum(1 for u, v, _ in edges if labels.get(u, 0) == labels.get(v, 0))

    @staticmethod
    def _try_flip_node(
        node_id: str,
        labels: dict[str, int],
        edges: list[tuple[str, str, dict]],
        current_violations: int,
    ) -> bool:
        """Tries flipping node label and returns True if improvement found"""
        labels[node_id] = 1 - labels[node_id]
        new_violations = SpatialKMeansClustering._count_violations(labels, edges)

        if new_violations < current_violations:
            return True
        else:
            labels[node_id] = 1 - labels[node_id]  # Revert flip
            return False


class TwoPairsChainHandler:
    """Handles special case of exactly 2 pairs forming a chain"""

    @staticmethod
    def handle_chain_partition(edges: list[tuple]) -> tuple[bool, dict[str, int]]:
        """Handles chain partition for exactly 2 pairs"""
        if not TwoPairsChainHandler._is_valid_input(edges):
            return False, {}

        cores = TwoPairsChainHandler._extract_cores(edges)

        if not TwoPairsChainHandler._is_valid_chain(cores):
            return False, {}

        middle_core = TwoPairsChainHandler._find_middle_core(cores)
        labels = TwoPairsChainHandler._assign_chain_labels(edges, middle_core)

        return True, labels

    @staticmethod
    def _is_valid_input(edges: list[tuple]) -> bool:
        """Validates input has exactly 2 edges"""
        return len(edges) == 2

    @staticmethod
    def _extract_cores(edges: list[tuple]) -> list[str]:
        """Extracts core identifiers from node IDs"""
        (u1, v1, _), (u2, v2, _) = edges
        return [TwoPairsChainHandler._get_core(nid) for nid in [u1, v1, u2, v2]]

    @staticmethod
    def _get_core(node_id: str) -> str:
        """Extracts core part of node ID"""
        return node_id.rsplit("|", 1)[0]

    @staticmethod
    def _is_valid_chain(cores: list[str]) -> bool:
        """Validates chain structure"""
        unique_cores = set(cores)
        return len(unique_cores) == 3

    @staticmethod
    def _find_middle_core(cores: list[str]) -> str:
        """Finds the middle core that appears twice"""
        unique_cores = set(cores)
        return max(unique_cores, key=lambda c: cores.count(c))

    @staticmethod
    def _assign_chain_labels(edges: list[tuple], middle_core: str) -> dict[str, int]:
        """Assigns labels for chain partition"""
        (u1, v1, _), (u2, v2, _) = edges
        labels = {u1: 0, v1: 0, u2: 0, v2: 0}

        for node_id in [u1, v1, u2, v2]:
            if TwoPairsChainHandler._get_core(node_id) == middle_core:
                labels[node_id] = 1

        return labels
