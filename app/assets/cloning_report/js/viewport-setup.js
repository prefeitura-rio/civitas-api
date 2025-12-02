/**
 * Viewport setup script for screenshots
 * Configures viewport and body styles for consistent rendering
 */

function setupViewport(width, height) {
    document.body.style.zoom = '100%';
    document.body.style.transform = 'scale(1)';
    document.body.style.margin = '0';
    document.body.style.padding = '0';
    document.documentElement.style.margin = '0';
    document.documentElement.style.padding = '0';

    let viewport = document.querySelector('meta[name="viewport"]');
    if (!viewport) {
        viewport = document.createElement('meta');
        viewport.name = 'viewport';
        document.head.appendChild(viewport);
    }
    viewport.content = `width=${width}, height=${height}, initial-scale=1.0, user-scalable=no`;
}
