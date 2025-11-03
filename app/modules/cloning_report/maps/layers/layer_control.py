"""Layer control functionality"""
import folium


def add_layer_control(map_obj: folium.Map, *, collapsed: bool = False) -> None:
    """Add layer control to map"""
    folium.LayerControl(collapsed=collapsed).add_to(map_obj)