"""
Clustering validator - Validates clustering feasibility and criteria
"""
from __future__ import annotations

import pandas as pd
from typing import Tuple, Dict, Any, List
from ..utils import haversine_km, VMAX_KMH, violations


class ClusteringValidator:
    """Validates clustering feasibility based on data quality and criteria"""
    
    @staticmethod
    def is_clusterizable(df_day: pd.DataFrame, vmax_kmh: float = VMAX_KMH) -> Tuple[bool, Dict[str, Any]]:
        """Determines if a day's data can be clustered with metadata"""
        validation_result = ClusteringValidator._validate_input_requirements(df_day)
        if not validation_result[0]:
            return validation_result
        
        feasibility_result = ClusteringValidator._check_clustering_feasibility(validation_result[1])
        if not feasibility_result[0]:
            return feasibility_result
            
        return ClusteringValidator._select_clustering_strategy(feasibility_result[1], vmax_kmh)
    
    @staticmethod
    def _validate_input_requirements(df_day: pd.DataFrame) -> Tuple[bool, Dict[str, Any]]:
        """Check empty data and prepare clustering data"""
        if ClusteringValidator._is_empty_data(df_day):
            return False, ClusteringValidator._empty_metadata()
        return True, ClusteringValidator._prepare_clustering_data(df_day)
    
    @staticmethod
    def _check_clustering_feasibility(prepared_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Check critical mass and spatial criteria"""
        if ClusteringValidator._lacks_critical_mass(prepared_data):
            return False, prepared_data
        if not ClusteringValidator._meets_spatial_criteria(prepared_data):
            return False, prepared_data
        return True, prepared_data
    
    @staticmethod
    def _select_clustering_strategy(prepared_data: Dict[str, Any], vmax_kmh: float) -> Tuple[bool, Dict[str, Any]]:
        """Evaluate and choose clustering approach"""
        return ClusteringValidator._evaluate_clustering_strategy(prepared_data, vmax_kmh)
    
    @staticmethod
    def _is_empty_data(df_day: pd.DataFrame) -> bool:
        """Checks if input data is empty"""
        return df_day is None or df_day.empty
    
    @staticmethod
    def _empty_metadata() -> Dict[str, Any]:
        """Returns empty metadata structure"""
        return {
            'df_nodes': pd.DataFrame(), 
            'edges': [], 
            'labels': {}, 
            'method': None, 
            'min_pair_km': 0.0, 
            'n_pairs': 0
        }
    
    @staticmethod
    def _prepare_clustering_data(df_day: pd.DataFrame) -> Dict[str, Any]:
        """Prepares data structures needed for clustering"""
        from .graph_builder import GraphBuilder
        
        df_clean = df_day.reset_index(drop=True).copy()
        df_nodes, edges = GraphBuilder.create_nodes_and_edges(df_clean)
        min_pair_km = ClusteringValidator._calculate_minimum_distance(df_clean)
        
        return {
            'df_nodes': df_nodes,
            'edges': edges,
            'labels': {},
            'method': None,
            'min_pair_km': min_pair_km,
            'n_pairs': len(edges)
        }
    
    @staticmethod
    def _calculate_minimum_distance(df: pd.DataFrame) -> float:
        """Calculates minimum distance between detection pairs"""
        distances = []
        
        for _, row in df.iterrows():
            km_value = pd.to_numeric(row.get('Km'), errors='coerce')
            if pd.notna(km_value):
                distances.append(float(km_value))
            else:
                try:
                    distance = haversine_km(
                        float(row['latitude_1']), float(row['longitude_1']),
                        float(row['latitude_2']), float(row['longitude_2'])
                    )
                    distances.append(distance)
                except Exception:
                    pass
        
        return min(distances) if distances else 0.0
    
    @staticmethod
    def _lacks_critical_mass(metadata: Dict[str, Any]) -> bool:
        """Checks if data lacks critical mass for clustering"""
        return metadata['df_nodes'].empty or not metadata['edges']
    
    @staticmethod
    def _meets_spatial_criteria(metadata: Dict[str, Any]) -> bool:
        """Checks if spatial criteria are met"""
        return metadata['min_pair_km'] > 2.0
    
    @staticmethod
    def _evaluate_clustering_strategy(metadata: Dict[str, Any], vmax_kmh: float) -> Tuple[bool, Dict[str, Any]]:
        """Evaluates and selects clustering strategy"""
        n_pairs = metadata['n_pairs']
        
        if n_pairs == 1:
            return ClusteringValidator._handle_single_pair(metadata)
        elif n_pairs == 2:
            return ClusteringValidator._handle_two_pairs(metadata)
        elif 1 < n_pairs < 4:
            return False, metadata
        else:
            return ClusteringValidator._handle_multiple_pairs(metadata, vmax_kmh)
    
    @staticmethod
    def _handle_single_pair(metadata: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Handles single pair case"""
        u, v, _ = metadata['edges'][0]
        metadata['labels'] = {u: 0, v: 1}
        metadata['method'] = 'ManualSinglePair'
        return True, metadata
    
    @staticmethod
    def _handle_two_pairs(metadata: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Handles two pairs case"""
        from .clustering_algorithm import TwoPairsChainHandler
        
        is_chain, chain_labels = TwoPairsChainHandler.handle_chain_partition(metadata['edges'])
        if is_chain:
            metadata['labels'] = chain_labels
            metadata['method'] = 'TwoPairsChain'
            return True, metadata
        
        return False, metadata
    
    @staticmethod
    def _handle_multiple_pairs(metadata: Dict[str, Any], vmax_kmh: float) -> Tuple[bool, Dict[str, Any]]:
        """Handles multiple pairs case with algorithm selection"""
        from .clustering_algorithm import GreedyTemporalClustering, SpatialKMeansClustering
        
        # Test both algorithms
        greedy_labels = GreedyTemporalClustering.cluster_nodes(
            metadata['df_nodes'], metadata['edges'], vmax_kmh
        )
        spatial_labels = SpatialKMeansClustering.cluster_nodes(
            metadata['df_nodes'], metadata['edges'], seed=123
        )
        
        # Select best algorithm
        greedy_violations = violations(greedy_labels, metadata['edges'])
        spatial_violations = violations(spatial_labels, metadata['edges'])
        
        if greedy_violations <= spatial_violations:
            metadata['labels'] = greedy_labels
            metadata['method'] = 'GreedyTemporalFeasible'
        else:
            metadata['labels'] = spatial_labels
            metadata['method'] = 'SpatialKMeansRepair'
        
        return True, metadata