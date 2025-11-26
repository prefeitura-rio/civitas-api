"""Maps module - Fully refactored OO interface"""

# Import refactored components
from app.modules.cloning_report.maps.utils import (
    format_timestamp,
    normalize_timestamp,
    get_optional_field,
)
from app.modules.cloning_report.maps.utils import fit_bounds_to_data, add_speed_label
from app.modules.cloning_report.maps.layers import add_layer_control
from app.modules.cloning_report.maps.generators import (
    generate_map_clonagem,
    generate_map_clonagem_single_day_html,
    MapGenerator,
    DataProcessor,
    BoundsManager,
    BaseLayer,
    ClusteredPairsLayer,
    OtherDetectionsLayer,
    TrailsMapGenerator,
    MapRenderer,
)
from app.modules.cloning_report.maps.batch_processor import UnifiedMapBatchProcessor
from app.modules.cloning_report.maps.export import take_html_screenshot


# Convenience functions for backward compatibility
def render_daily_figures(df_sus):
    """Render daily figures - convenience function"""
    renderer = MapRenderer()
    return renderer.render_daily_figures(df_sus)


def render_overall_map_png(df_sus):
    """Render overall map PNG - convenience function"""
    renderer = MapRenderer()
    return renderer.render_overall_map_png(df_sus)


def generate_trails_map(df_sus, day, trails_tables_day, width=1200, height=800):
    """Generate trails map - convenience function"""
    generator = TrailsMapGenerator(width, height)
    return generator.generate_trails_map(df_sus, day, trails_tables_day)


def process_all_maps_batch(df_sus, trails_tables):
    """🚀 NEW: Process ALL maps (daily, overall, trails) in one parallel batch - MAXIMUM PERFORMANCE"""
    processor = UnifiedMapBatchProcessor()
    return processor.process_all_maps(df_sus, trails_tables)


__all__ = [
    # Main API functions
    "generate_map_clonagem",
    "render_daily_figures",
    "render_overall_map_png",
    "generate_trails_map",
    "process_all_maps_batch",
    # Refactored components
    "format_timestamp",
    "normalize_timestamp",
    "get_optional_field",
    "fit_bounds_to_data",
    "add_speed_label",
    "add_layer_control",
    "generate_map_clonagem_single_day_html",
    "take_html_screenshot",
    # OO Classes
    "MapGenerator",
    "DataProcessor",
    "BoundsManager",
    "BaseLayer",
    "ClusteredPairsLayer",
    "OtherDetectionsLayer",
    "TrailsMapGenerator",
    "MapRenderer",
]
