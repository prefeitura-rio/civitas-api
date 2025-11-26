"""
graph.py - Graph analysis operations
-----------------------------------
Single responsibility: Handle graph-related calculations
"""


class GraphAnalyzer:
    """Handle graph analysis operations following SRP"""

    @staticmethod
    def count_violations(
        labels: dict[str, int], edges: list[tuple[str, str, dict]]
    ) -> int:
        """Count violations where edge endpoints have same label"""
        return sum(1 for u, v, _ in edges if GraphAnalyzer._same_label(labels, u, v))

    @staticmethod
    def _same_label(labels: dict[str, int], node1: str, node2: str) -> bool:
        """Check if two nodes have the same label"""
        return labels.get(node1, 0) == labels.get(node2, 0)
