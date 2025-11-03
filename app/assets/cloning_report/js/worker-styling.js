/**
 * Worker styling script for screenshots
 * Alternative styling for worker threads with different scaling
 */

function applyWorkerStyling() {
    // Hide controls like legacy
    const cont = document.querySelector('.leaflet-control-container');
    if (cont) cont.style.display = 'none';
    const br = document.querySelector('.leaflet-bottom.leaflet-right');
    if (br) br.style.display = 'none';

    // Ensure proper zoom and positioning like legacy
    window.scrollTo(0, 0);

    // CRITICAL: Force readable text sizes for map elements
    const mapDiv = document.querySelector('.leaflet-container');
    if (mapDiv) {
        // Keep a mild zoom-out so the full map remains visible while text stays legible
        const SCALE_FACTOR = 0.94;
        mapDiv.style.transform = `translate(-50%, -50%) scale(${SCALE_FACTOR})`;
        mapDiv.style.transformOrigin = 'center center';
        mapDiv.style.fontSize = '16px';
        mapDiv.style.width = '100%';
        mapDiv.style.height = '100%';
        mapDiv.style.position = 'absolute';
        mapDiv.style.top = '50%';
        mapDiv.style.left = '50%';
        mapDiv.style.margin = '0';
        mapDiv.style.padding = '0';
    }

    // Make popup text MUCH larger and more readable
    document.querySelectorAll('.leaflet-popup-content').forEach(popup => {
        popup.style.fontSize = '22px';  // Further increased for readability
        popup.style.fontWeight = 'bold';
        popup.style.lineHeight = '1.4';
    });

    // Make marker labels much more readable
    document.querySelectorAll('.leaflet-marker-icon').forEach(marker => {
        marker.style.transform += ' scale(1.0)'; 
        marker.style.fontSize = '20px';  // Reduced from 1.2 to 1.0
    });

    // Enhance tooltip text significantly
    document.querySelectorAll('.leaflet-tooltip').forEach(tooltip => {
        tooltip.style.fontSize = '20px';  // Increased from 16px
        tooltip.style.fontWeight = 'bold';
        tooltip.style.backgroundColor = 'rgba(255, 255, 255, 0.95)';
        tooltip.style.border = '2px solid #333';
        tooltip.style.borderRadius = '6px';
        tooltip.style.padding = '8px 12px';  // More padding
        tooltip.style.minWidth = '60px';
        tooltip.style.textAlign = 'center';
    });

    // Make speed labels MUCH more visible and larger
    document.querySelectorAll('div[title*="km/h"]').forEach(speedLabel => {
        speedLabel.style.fontSize = '16px';  
        speedLabel.style.fontWeight = 'bold';
        speedLabel.style.color = '#000';
        speedLabel.style.textShadow = '1px 1px 3px white';
        speedLabel.style.backgroundColor = 'rgba(255, 255, 255, 0.9)';
        speedLabel.style.padding = '4px 8px';  // Reduced padding
        speedLabel.style.borderRadius = '4px';  // Smaller radius
        speedLabel.style.border = '1px solid #333';  // Thinner border
        speedLabel.style.minWidth = '60px';  // Smaller width
        speedLabel.style.textAlign = 'center';
        speedLabel.style.fontFamily = 'Arial, sans-serif';
    });
}
