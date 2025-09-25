/**
 * Map styling script for screenshots
 * Applies visual enhancements for better readability
 */

function applyMapStyling() {
    // Hide controls like legacy
    const cont = document.querySelector('.leaflet-control-container');
    if (cont) cont.style.display = 'none';
    const br = document.querySelector('.leaflet-bottom.leaflet-right');
    if (br) br.style.display = 'none';

    window.scrollTo(0, 0);

    // CRITICAL: Add significant zoom-in for much better text readability
    const mapDiv = document.querySelector('.leaflet-container');
    if (mapDiv) {
        // Apply 1.3x zoom to make everything much more readable
        mapDiv.style.transform = 'scale(1.3)';
        mapDiv.style.transformOrigin = 'center center';
        mapDiv.style.fontSize = '18px';  // Even larger base font
        mapDiv.style.width = '100%';
        mapDiv.style.height = '100%';
        mapDiv.style.overflow = 'hidden';
        mapDiv.style.position = 'absolute';
        mapDiv.style.top = '0';
        mapDiv.style.left = '0';
        mapDiv.style.margin = '0';
        mapDiv.style.padding = '0';
    }

    // Ensure body doesn't show scroll bars and is properly positioned
    document.body.style.overflow = 'hidden';
    document.body.style.margin = '0';
    document.body.style.padding = '0';
    document.body.style.position = 'relative';
    document.documentElement.style.overflow = 'hidden';
    document.documentElement.style.margin = '0';
    document.documentElement.style.padding = '0';

    // Make popup text MUCH larger and more readable
    document.querySelectorAll('.leaflet-popup-content').forEach(popup => {
        popup.style.fontSize = '22px';  // Increased from 18px
        popup.style.fontWeight = 'bold';
        popup.style.lineHeight = '1.4';
    });

    // Make marker labels much more readable
    document.querySelectorAll('.leaflet-marker-icon').forEach(marker => {
        marker.style.transform += ' scale(1.0)';  // Reduced from 1.2 to 1.0
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
        speedLabel.style.fontSize = '16px';  // Reduced from 22px to 16px
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
