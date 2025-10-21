#!/usr/bin/env python3
"""
HTTP server with automatic hot reload for templates.
Monitors file changes and automatically reloads.

Usage: python scripts/watch_template.py cloning_suspects_no_data_new
"""

import sys
import time
import jinja2
import mimetypes
import hashlib
import json
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import webbrowser
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import config

# Template being monitored
CURRENT_TEMPLATE = None
CONTEXT_JSON_PATH = None
LAST_RENDER = None
TEMPLATE_HASH = None


def load_context_from_json(json_path: str) -> dict:
    """Load context from a JSON file."""
    try:
        with open(json_path, encoding="utf-8") as f:
            context = json.load(f)
        print(f"📦 Context loaded from: {json_path}")
        return context
    except Exception as e:
        raise Exception(f"Error loading JSON: {e}")


def get_context(template_name: str) -> dict:
    """Returns the context for the template (from JSON or default)."""
    global CONTEXT_JSON_PATH

    # If a JSON was provided, load from it
    if CONTEXT_JSON_PATH:
        context = load_context_from_json(CONTEXT_JSON_PATH)
    else:
        raise Exception("JSON context not found")

    # Always add the necessary paths (overwrites if they already exist)
    context["styles_base_path"] = "/app/templates/styles_base.css"
    context["logo_prefeitura_path"] = "/app/assets/logo_prefeitura.png"
    context["logo_civitas_path"] = "/app/assets/logo_civitas.png"

    return context


def get_template_hash(template_name: str) -> str:
    """Calculates hash of template and related files to detect changes."""
    global CONTEXT_JSON_PATH

    template_path = config.HTML_TEMPLATES_DIR / f"pdf/{template_name}.html"
    css_path = config.HTML_TEMPLATES_DIR / "styles_base.css"

    combined_content = ""

    # Add template content
    if template_path.exists():
        combined_content += template_path.read_text()
        combined_content += str(template_path.stat().st_mtime)

    # Add CSS content
    if css_path.exists():
        combined_content += css_path.read_text()
        combined_content += str(css_path.stat().st_mtime)

    # Add context JSON content (if it exists)
    if CONTEXT_JSON_PATH:
        json_path = Path(CONTEXT_JSON_PATH)
        if json_path.exists():
            combined_content += json_path.read_text()
            combined_content += str(json_path.stat().st_mtime)

    return hashlib.md5(combined_content.encode()).hexdigest()


def render_template(template_name: str) -> str:
    """Renders the template and injects auto-reload script."""
    global TEMPLATE_HASH

    context = get_context(template_name)

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(config.HTML_TEMPLATES_DIR), autoescape=True
    )

    template = env.get_template(f"pdf/{template_name}.html")
    html = template.render(**context)

    # Update the hash
    TEMPLATE_HASH = get_template_hash(template_name)

    # Inject auto-reload script before </body>
    auto_reload_script = """
    <script>
        // Auto-reload when the template changes
        let lastHash = null;

        async function checkForUpdates() {
            try {
                const response = await fetch('/check-update');
                const data = await response.json();

                if (lastHash === null) {
                    lastHash = data.hash;
                    console.log('🔍 Monitoring template changes...');
                } else if (lastHash !== data.hash) {
                    console.log('🔄 Template updated! Reloading...');
                    location.reload();
                }
            } catch (error) {
                console.error('Error checking for updates:', error);
            }
        }

        // Check every 500ms
        setInterval(checkForUpdates, 500);
    </script>
    """

    html = html.replace("</body>", f"{auto_reload_script}</body>")

    return html


class TemplateHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global CURRENT_TEMPLATE

        path = unquote(self.path)

        # Endpoint to check for updates (used by auto-reload)
        if path == "/check-update":
            self.serve_update_check()
        # Serve static files (accepts /static/ or /app/)
        elif (
            path.startswith("/static/")
            or path.startswith("/app/")
            or path.endswith((".css", ".png", ".jpg", ".jpeg", ".gif", ".svg"))
        ):
            self.serve_static_file(path)
        # Serve the HTML template
        else:
            self.serve_template()

    def serve_static_file(self, path):
        """Serve static files (CSS, images)."""
        print(f"🔍 Attempting to serve: {path}")

        # Clean the path
        file_name = path.lstrip("/")

        # If it starts with /app/, map to the project root directory
        if path.startswith("/app/"):
            # Remove '/app/' and build the absolute path
            relative_path = path.replace("/app/", "", 1)
            project_root = Path(
                __file__
            ).parent.parent  # Go up two levels from scripts/
            file_path = project_root / "app" / relative_path

            if file_path.exists():
                print(f"✅ File found: {file_path}")
            else:
                print(f"❌ File not found at: {file_path}")
                self.send_error(404, f"File not found: {path}")
                return
        else:
            # Remove /static/ from the path if it exists
            file_name = path.replace("/static/", "").lstrip("/")

            # Try to find the file
            possible_paths = [
                config.ASSETS_DIR / file_name,
                config.ASSETS_DIR / "cloning_report" / file_name,
                config.HTML_TEMPLATES_DIR / file_name,
            ]

            file_path = None
            for p in possible_paths:
                if p.exists():
                    file_path = p
                    break

            if not file_path:
                self.send_error(404, f"File not found: {file_name}")
                print(f"❌ File not found: {file_name}")
                print(f"   Tried at: {[str(p) for p in possible_paths]}")
                return

        try:
            # Detect the MIME type
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if mime_type is None:
                mime_type = "application/octet-stream"

            # Read and send the file
            with open(file_path, "rb") as f:
                content = f.read()

            self.send_response(200)
            self.send_header("Content-type", mime_type)
            self.send_header("Content-Length", len(content))
            self.end_headers()
            self.wfile.write(content)

            print(f"✅ File served: {file_name} ({mime_type})")

        except Exception as e:
            self.send_error(500, f"Error reading file: {str(e)}")
            print(f"❌ Error serving file: {e}")

    def serve_update_check(self):
        """Endpoint that returns the current template hash to check for changes."""
        global CURRENT_TEMPLATE

        try:
            current_hash = get_template_hash(CURRENT_TEMPLATE)
            response_data = f'{{"hash": "{current_hash}"}}'

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            self.wfile.write(response_data.encode("utf-8"))

        except Exception as e:
            self.send_error(500, f"Error checking for updates: {str(e)}")

    def serve_template(self):
        """Serve the rendered HTML template."""
        try:
            html = render_template(CURRENT_TEMPLATE)

            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))

            print(
                f"✅ Template rendered: {CURRENT_TEMPLATE} at {time.strftime('%H:%M:%S')}"
            )

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            error_html = f"<h1>Template Rendering Error</h1><pre>{str(e)}</pre>"
            self.wfile.write(error_html.encode("utf-8"))
            print(f"❌ Rendering error: {e}")

    def log_message(self, format, *args):
        # Keep minimal logs for debugging
        if "GET" in str(args):
            pass  # Already logging in serve_static_file and serve_template
        else:
            print(f"📡 {format % args}")


def main():
    global CURRENT_TEMPLATE, CONTEXT_JSON_PATH

    if len(sys.argv) < 2:
        print(
            "❌ Usage: python scripts/watch_template.py <template_name> [context.json]"
        )
        print("\nExamples:")
        print("  python scripts/watch_template.py cloning_suspects tmp/context.json")
        print(
            "  python scripts/watch_template.py multiple_correlated_plates tmp/context.json"
        )
        sys.exit(1)

    CURRENT_TEMPLATE = sys.argv[1]

    # Check if a JSON with context was provided
    if len(sys.argv) >= 3:
        CONTEXT_JSON_PATH = sys.argv[2]
        json_path = Path(CONTEXT_JSON_PATH)
        if not json_path.exists():
            print(f"⚠️  JSON file not found: {CONTEXT_JSON_PATH}")
            print("   Using default context...")
            CONTEXT_JSON_PATH = None

    port = 8888

    server = HTTPServer(("localhost", port), TemplateHandler)

    print(f"🚀 Server running at: http://localhost:{port}")
    print(f"📄 Template: {CURRENT_TEMPLATE}")
    print(f"📦 Context: {CONTEXT_JSON_PATH}")
    print(f"📁 Assets Dir: {config.ASSETS_DIR}")
    print(f"📁 Templates Dir: {config.HTML_TEMPLATES_DIR}")
    print("\n✨ Auto-Reload Active!")
    print("   Monitoring changes in:")
    print(f"   • app/templates/pdf/{CURRENT_TEMPLATE}.html")
    print("   • app/templates/styles_base.css")
    if CONTEXT_JSON_PATH:
        print(f"   • {CONTEXT_JSON_PATH}")
    print("\n   💡 Save any file (Ctrl+S) and the browser reloads AUTOMATICALLY!")
    print("   ⏱️  Checking for changes every 500ms...")
    print("\nPress Ctrl+C to stop\n")

    # Open in browser
    webbrowser.open(f"http://localhost:{port}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
        server.shutdown()


if __name__ == "__main__":
    main()
