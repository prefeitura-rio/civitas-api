"""
JavaScript loader utility for cloning report module
Loads JavaScript files from assets directory
"""

from pathlib import Path


def load_js_file(filename: str) -> str:
    """
    Load JavaScript file from assets directory

    Args:
        filename: Name of the JavaScript file (e.g., 'layer-control.js')

    Returns:
        JavaScript code as string
    """
    # Get the project root directory
    current_dir = Path(__file__).parent
    project_root = current_dir.parent.parent.parent.parent

    # Build path to assets directory
    assets_dir = project_root / "app" / "assets" / "cloning_report" / "js"
    js_file_path = assets_dir / filename

    if not js_file_path.exists():
        raise FileNotFoundError(f"JavaScript file not found: {js_file_path}")

    with open(js_file_path, encoding="utf-8") as f:
        return f.read()


def get_layer_control_script(only_layers: list = None) -> str:
    """
    Get layer control JavaScript code

    Args:
        only_layers: List of layer names to show (None for all layers)

    Returns:
        JavaScript code for layer control
    """
    js_code = load_js_file("layer-control.js")

    if not only_layers or len(only_layers) == 0:
        # Show all layers
        return f"""
        {js_code}
        setupLayerControl([]);
        """
    else:
        # Show only specified layers
        return f"""
        {js_code}
        setupLayerControl({only_layers});
        """


def get_map_styling_script() -> str:
    """
    Get map styling JavaScript code

    Returns:
        JavaScript code for map styling
    """
    js_code = load_js_file("map-styling.js")
    return f"""
    {js_code}
    applyMapStyling();
    """


def get_worker_styling_script() -> str:
    """
    Get worker styling JavaScript code

    Returns:
        JavaScript code for worker styling
    """
    js_code = load_js_file("worker-styling.js")
    return f"""
    {js_code}
    applyWorkerStyling();
    """


def get_viewport_setup_script(width: int, height: int) -> str:
    """
    Get viewport setup JavaScript code

    Args:
        width: Viewport width
        height: Viewport height

    Returns:
        JavaScript code for viewport setup
    """
    js_code = load_js_file("viewport-setup.js")
    return f"""
    {js_code}
    setupViewport({width}, {height});
    """


def get_basic_controls_script() -> str:
    """
    Get basic controls JavaScript code

    Returns:
        JavaScript code for basic controls
    """
    js_code = load_js_file("basic-controls.js")
    return f"""
    {js_code}
    hideBasicControls();
    """
