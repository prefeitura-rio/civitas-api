/**
 * Layer control script for map screenshots
 * Controls which layers are visible on the map
 */

function setupLayerControl(onlyLayers) {
    if (!onlyLayers || onlyLayers.length === 0) {
        // Show all layers
        const labels = document.querySelectorAll('.leaflet-control-layers-overlays label');
        labels.forEach(lb => {
            const cb = lb.querySelector('input[type="checkbox"]');
            if (!cb) return;
            if (!cb.checked) cb.click();
        });
    } else {
        // Show only specified layers
        const want = new Set(onlyLayers);
        const labels = document.querySelectorAll('.leaflet-control-layers-overlays label');
        labels.forEach(lb => {
            const name = lb.textContent.trim();
            const cb = lb.querySelector('input[type="checkbox"]');
            if (!cb) return;
            const on = want.has(name);
            if (cb.checked && !on) cb.click();
            if (!cb.checked && on) cb.click();
        });
    }
}
