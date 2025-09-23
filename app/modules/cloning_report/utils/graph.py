# -*- coding: utf-8 -*-
"""
graph.py - Graph analysis operations
-----------------------------------
Single responsibility: Handle graph-related calculations
"""
from typing import Dict, List, Tuple, Any


class GraphAnalyzer:
    """Handle graph analysis operations following SRP"""
    
    @staticmethod
    def count_violations(labels: Dict[str, int], edges: List[Tuple[str, str, Dict]]) -> int:
        """Count violations where edge endpoints have same label"""
        return sum(1 for u, v, _ in edges if GraphAnalyzer._same_label(labels, u, v))
    
    @staticmethod
    def _same_label(labels: Dict[str, int], node1: str, node2: str) -> bool:
        """Check if two nodes have the same label"""
        return labels.get(node1, 0) == labels.get(node2, 0)