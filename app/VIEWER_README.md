# Random Ussless Imaje-s — Viewer

This repository includes a small, cross-platform image viewer that opens a local gallery showing the images in the `images/` folder.

Files:
- app/viewer.py — Python 3 script that starts a local HTTP server and writes a simple gallery.html
- app/run_viewer.sh — Unix launcher (make executable with `chmod +x app/run_viewer.sh`)
- app/run_viewer.bat — Windows launcher

How to run

- Linux / macOS:
  - Ensure Python 3 is installed
  - From the repository root run: ./app/run_viewer.sh

- Windows:
  - Ensure Python is installed and on PATH
  - From the repository root run: app\\run_viewer.bat

Notes

- The viewer generates a `gallery.html` file in the repository root (it will be overwritten each run). The program starts a tiny local HTTP server and opens your default browser to view the gallery.
- This avoids external dependencies and works on Python 3.6+.
