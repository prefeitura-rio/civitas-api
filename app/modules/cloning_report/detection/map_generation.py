"""
map_generation.py - Map generation for detection results
------------------------------------------------------
Single responsibility: Generate maps and visualizations
"""

import pandas as pd
from pathlib import Path
from app.modules.cloning_report.utils import ensure_dir
from app.modules.cloning_report.utils.filesystem import FileSystemService


class MapGenerator:
    """Generates maps and visualizations for detection results"""

    @staticmethod
    def generate_detection_map(
        suspicious_pairs: pd.DataFrame, all_detections: pd.DataFrame, speed_limit: float
    ) -> str:
        """Generate main detection map and return HTML path"""
        html_path = MapGenerator._prepare_html_path()
        html_content = MapGenerator._create_map_content(
            suspicious_pairs, all_detections, speed_limit
        )
        MapGenerator._save_html_file(html_path, html_content)
        return str(html_path)

    @staticmethod
    def _prepare_html_path() -> Path:
        """Prepare HTML output path"""
        html_dir = ensure_dir("app/assets/cloning_report/htmls")
        filename = FileSystemService.build_unique_filename("mapa_clonagem.html")
        return html_dir / filename

    @staticmethod
    def _create_map_content(
        suspicious_pairs: pd.DataFrame, all_detections: pd.DataFrame, speed_limit: float
    ) -> str:
        """Create map HTML content"""
        # Import here to avoid circular dependency
        import sys

        sys.path.append(".")
        from app.modules.cloning_report.maps import generate_map_clonagem

        return generate_map_clonagem(
            suspicious_pairs,
            use_clusters=True,
            vmax_kmh=speed_limit,
            df_all=all_detections,
            show_other_daily=True,
            include_non_sus_days=False,
        )

    @staticmethod
    def _save_html_file(html_path: Path, html_content: str) -> None:
        """Save HTML content to file"""
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
