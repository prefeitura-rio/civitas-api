/**
 * Basic controls script for screenshots
 * Simple control hiding and positioning
 */

function hideBasicControls() {
    const cont = document.querySelector('.leaflet-control-container');
    if (cont) cont.style.display = 'none';
    const br = document.querySelector('.leaflet-bottom.leaflet-right');
    if (br) br.style.display = 'none';
    window.scrollTo(0, 0);
}
