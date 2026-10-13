# Random Ussless Imaje-s — Viewer & Manager

This update adds a category and image management UI integrated with the existing local viewer.

What's new
- Full SPA at `gallery.html` with category creation/rename/delete, upload, delete images, and moving images between categories.
- Backend API served by `app/viewer.py` (no external deps) providing endpoints under `/api/*`.
- Persistent DB file `.gallery_db.json` stored in the repo root that keeps categories and image assignments across restarts.

Files changed/added
- app/viewer.py — replaced previous static-only server with API-backed server
- gallery.html — new single-page app (keeps the dark theme and gallery design)
- .gallery_db.json — persistent DB (auto-created)
- app/run_viewer.sh and app/run_viewer.bat unchanged — continue to launch app/viewer.py

How to run

1. Clone the repo (if you haven't already):

   git clone https://github.com/UnnownTShox/random-ussless-imaje-s.git
   cd random-ussless-imaje-s

2. Run viewer (Python 3.8+ recommended):

   # Linux / macOS
   ./app/run_viewer.sh

   # Windows
   app\\run_viewer.bat

3. The viewer will open your browser to the gallery page. Use the sidebar to create categories; use the uploader to add images and choose a category. Use the image controls to delete or move images.

Safety & validation
- Uploads are restricted by extension and maximum size (10 MB).
- Filenames are sanitized and collisions avoided by adding a -N suffix.
- Deleting images only affects files inside the `images/` directory; path traversal is prevented.

If you want a native executable or auto-reload when new images are added to disk, I can add those next. Enjoy the new manager!
