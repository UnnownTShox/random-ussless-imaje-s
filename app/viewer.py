#!/usr/bin/env python3
"""
Simple cross-platform image viewer for the repository.

What it does:
- Finds the repository root (one level up from this script's directory)
- Scans the `images/` directory for common image files (SVG/PNG/JPG/GIF/etc.)
- Generates a lightweight `gallery.html` in the repo root and starts a local HTTP server
- Opens the default web browser to show the gallery

This approach avoids external dependencies and works on Windows, Linux, and macOS
as long as Python 3 is available.
"""

import http.server
import socketserver
import os
import webbrowser
import threading
import socket
import sys
from contextlib import closing

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
IMAGES_DIR = os.path.join(REPO_ROOT, 'images')
GALLERY_NAME = 'gallery.html'

IMAGE_EXTS = ('.svg', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp')


def find_images():
    if not os.path.isdir(IMAGES_DIR):
        return []
    files = []
    for fname in sorted(os.listdir(IMAGES_DIR)):
        if fname.lower().endswith(IMAGE_EXTS):
            files.append(fname)
    return files


def render_gallery(image_files):
    items = []
    for f in image_files:
        url = f"/images/{f}"
        items.append(f'  <figure>\n    <img src="{url}" alt="{f}" loading="lazy">\n    <figcaption>{f}</figcaption>\n  </figure>')

    html = f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Random Ussless Imaje-s — Gallery</title>
  <style>
    body {{ background: #0f172a; color: #e6eef6; font-family: system-ui, -apple-system, Segoe UI, Roboto, 'Helvetica Neue', Arial; margin: 0; padding: 24px; }}
    h1 {{ margin-top: 0; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 18px; }}
    figure {{ background: rgba(255,255,255,0.03); padding: 12px; border-radius: 8px; margin: 0; }}
    img {{ max-width: 100%; height: auto; display: block; border-radius: 6px; background: white; }}
    figcaption {{ font-size: 12px; color: #9fb6d8; margin-top: 8px; word-break: break-all; }}
    header .note {{ color: #9fb6d8; font-size: 13px; margin-bottom: 12px; }}
    footer {{ margin-top: 18px; color: #8aa0c2; font-size: 12px; }}
  </style>
</head>
<body>
  <header>
    <h1>Random Ussless Imaje-s — Gallery</h1>
    <div class="note">Serving images from <code>/images/</code> — close this program to stop the local server.</div>
  </header>
  <main>
    <section class="grid">
{('\n'.join(items))}
    </section>
  </main>
  <footer>Local viewer started by <code>app/viewer.py</code></footer>
</body>
</html>
"""
    return html


def pick_port():
    # Let OS pick a free port by binding to 0, then close socket and return port
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


class SilentHandler(http.server.SimpleHTTPRequestHandler):
    # suppress log messages to stdout
    def log_message(self, format, *args):
        pass


def serve(repo_root, port):
    os.chdir(repo_root)
    handler = SilentHandler
    with socketserver.TCPServer(('127.0.0.1', port), handler) as httpd:
        sa = httpd.socket.getsockname()
        print(f"Serving HTTP on {sa[0]} port {sa[1]} (http://{sa[0]}:{sa[1]}/) ...")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass


def main():
    images = find_images()
    if not images:
        print("No images found in the images/ directory. Add files there and run this again.")
        sys.exit(1)

    gallery_html = render_gallery(images)
    gallery_path = os.path.join(REPO_ROOT, GALLERY_NAME)
    try:
        with open(gallery_path, 'w', encoding='utf-8') as f:
            f.write(gallery_html)
    except Exception as e:
        print(f"Failed to write gallery file: {e}")
        sys.exit(1)

    port = pick_port()

    thread = threading.Thread(target=serve, args=(REPO_ROOT, port), daemon=True)
    thread.start()

    url = f'http://127.0.0.1:{port}/{GALLERY_NAME}'
    print(f"Opening your default browser to {url}")
    webbrowser.open(url)

    try:
        print("Press Ctrl+C to stop the server and exit.")
        while thread.is_alive():
            thread.join(1)
    except KeyboardInterrupt:
        print("Shutting down...")


if __name__ == '__main__':
    main()
