#!/usr/bin/env python3
"""
Enhanced gallery server with category and image management API.

Features:
- Serves the SPA gallery (gallery.html) and files from the repo root
- API endpoints under /api/* for categories, images, upload, move, delete
- Persists categories and assignments to .gallery_db.json in the repo root
- Validates uploads and prevents path traversal

No external dependencies required. Works with Python 3.8+.
"""

from http.server import SimpleHTTPRequestHandler, HTTPServer
import os
import json
import threading
import webbrowser
import socket
from contextlib import closing
import urllib.parse
import cgi
import shutil
import sys
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
IMAGES_DIR = os.path.join(REPO_ROOT, 'images')
DB_PATH = os.path.join(REPO_ROOT, '.gallery_db.json')
GALLERY_NAME = 'gallery.html'

IMAGE_EXTS = ('.svg', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp')
SAFE_FILENAME_RE = re.compile(r'[^A-Za-z0-9._-]')
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB per file


def ensure_dirs():
    os.makedirs(IMAGES_DIR, exist_ok=True)
    if not os.path.exists(DB_PATH):
        # initialize DB with no user categories and empty assignments
        db = {'categories': [], 'assignments': {}}
        with open(DB_PATH, 'w', encoding='utf-8') as f:
            json.dump(db, f, indent=2)


def load_db():
    try:
        with open(DB_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {'categories': [], 'assignments': {}}


def save_db(db):
    tmp = DB_PATH + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=2, ensure_ascii=False)
    os.replace(tmp, DB_PATH)


def list_images():
    files = []
    if not os.path.isdir(IMAGES_DIR):
        return files
    for fname in sorted(os.listdir(IMAGES_DIR)):
        if fname.lower().endswith(IMAGE_EXTS):
            files.append(fname)
    return files


def secure_filename(filename):
    # Remove directory components and unsafe characters
    filename = os.path.basename(filename)
    filename = SAFE_FILENAME_RE.sub('_', filename)
    # prevent hidden files
    filename = filename.lstrip('._')
    if not filename:
        filename = 'file'
    return filename


def unique_path(dest_dir, filename):
    base, ext = os.path.splitext(filename)
    candidate = filename
    i = 1
    while os.path.exists(os.path.join(dest_dir, candidate)):
        candidate = f"{base}-{i}{ext}"
        i += 1
    return os.path.join(dest_dir, candidate), os.path.basename(candidate)


class APIServerHandler(SimpleHTTPRequestHandler):
    server_version = "GalleryAPI/1.0"

    def __init__(self, *args, directory=None, **kwargs):
        # Ensure the handler serves from the repo root
        if directory is None:
            directory = REPO_ROOT
        super().__init__(*args, directory=directory, **kwargs)

    def log_message(self, format, *args):
        # quiet logging
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path.startswith('/api/'):
            self.handle_api_get(parsed)
        else:
            # serve static files (gallery.html, images/, etc.)
            return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/api/upload':
            self.handle_upload()
        elif parsed.path.startswith('/api/categories'):
            self.handle_api_post(parsed)
        elif parsed.path == '/api/move':
            self.handle_move()
        else:
            self.send_error(404, 'Not Found')

    def do_PUT(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path.startswith('/api/categories/'):
            self.handle_rename_category(parsed)
        else:
            self.send_error(404, 'Not Found')

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path.startswith('/api/categories/'):
            self.handle_delete_category(parsed)
        elif parsed.path.startswith('/api/images/'):
            self.handle_delete_image(parsed)
        else:
            self.send_error(404, 'Not Found')

    # ---------- API handlers ----------
    def handle_api_get(self, parsed):
        path = parsed.path
        if path == '/api/images':
            db = load_db()
            imgs = list_images()
            items = []
            for f in imgs:
                items.append({'filename': f, 'category': db.get('assignments', {}).get(f, '')})
            self.send_json(items)
        elif path == '/api/categories':
            db = load_db()
            self.send_json({'categories': db.get('categories', [])})
        else:
            self.send_error(404, 'Not Found')

    def handle_api_post(self, parsed):
        # POST /api/categories -> create category
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode('utf-8') if length else ''
        try:
            data = json.loads(body) if body else {}
        except Exception:
            data = {}
        if parsed.path == '/api/categories':
            name = str(data.get('name', '')).strip()
            if not name:
                self.send_error(400, 'Name required')
                return
            db = load_db()
            if name in db.get('categories', []):
                self.send_error(409, 'Category exists')
                return
            db.setdefault('categories', []).append(name)
            save_db(db)
            self.send_json({'ok': True, 'name': name})
        else:
            self.send_error(404, 'Not Found')

    def handle_rename_category(self, parsed):
        # PUT /api/categories/<oldname> with JSON {name: newname}
        parts = parsed.path.split('/')
        if len(parts) < 4:
            self.send_error(400, 'Bad request')
            return
        old = urllib.parse.unquote(parts[3])
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode('utf-8') if length else ''
        try:
            data = json.loads(body) if body else {}
        except Exception:
            data = {}
        new = str(data.get('name', '')).strip()
        if not new:
            self.send_error(400, 'New name required')
            return
        db = load_db()
        cats = db.setdefault('categories', [])
        if old not in cats:
            self.send_error(404, 'Category not found')
            return
        if new in cats:
            self.send_error(409, 'Category exists')
            return
        # rename category
        cats[cats.index(old)] = new
        # update assignments
        for k, v in list(db.get('assignments', {}).items()):
            if v == old:
                db['assignments'][k] = new
        save_db(db)
        self.send_json({'ok': True, 'old': old, 'new': new})

    def handle_delete_category(self, parsed):
        # DELETE /api/categories/<name>
        parts = parsed.path.split('/')
        if len(parts) < 4:
            self.send_error(400, 'Bad request')
            return
        name = urllib.parse.unquote(parts[3])
        db = load_db()
        cats = db.setdefault('categories', [])
        if name not in cats:
            self.send_error(404, 'Category not found')
            return
        cats.remove(name)
        # unassign images in this category
        for k, v in list(db.get('assignments', {}).items()):
            if v == name:
                db['assignments'][k] = ''
        save_db(db)
        self.send_json({'ok': True, 'name': name})

    def handle_upload(self):
        # Accept multipart/form-data with 'file' and optional 'category'
        ctype, pdict = cgi.parse_header(self.headers.get('Content-Type', ''))
        if ctype != 'multipart/form-data':
            self.send_error(400, 'Content-Type must be multipart/form-data')
            return
        pdict['boundary'] = pdict['boundary'].encode('utf-8') if isinstance(pdict.get('boundary'), str) else pdict.get('boundary')
        fs = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={'REQUEST_METHOD': 'POST'}, keep_blank_values=True)
        filefield = fs['file'] if 'file' in fs else None
        category = str(fs.getvalue('category') or '').strip()
        if not filefield or not hasattr(filefield, 'filename') or not filefield.filename:
            self.send_error(400, 'File required')
            return
        filename = secure_filename(filefield.filename)
        if not filename.lower().endswith(IMAGE_EXTS):
            self.send_error(400, 'Unsupported file type')
            return
        # check size: FieldStorage may have .file with .seek
        filedata = filefield.file
        filedata.seek(0, os.SEEK_END)
        size = filedata.tell()
        filedata.seek(0)
        if size > MAX_UPLOAD_SIZE:
            self.send_error(400, 'File too large')
            return
        dest_path, safe_name = unique_path(IMAGES_DIR, filename)
        try:
            with open(dest_path, 'wb') as out:
                shutil.copyfileobj(filedata, out)
        except Exception as e:
            self.send_error(500, f'Write failed: {e}')
            return
        # record assignment
        db = load_db()
        if category and category in db.get('categories', []):
            db.setdefault('assignments', {})[safe_name] = category
        else:
            db.setdefault('assignments', {})[safe_name] = ''
        save_db(db)
        self.send_json({'ok': True, 'filename': safe_name, 'category': db['assignments'].get(safe_name, '')})

    def handle_move(self):
        # POST /api/move with JSON {filename, category}
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode('utf-8') if length else ''
        try:
            data = json.loads(body) if body else {}
        except Exception:
            data = {}
        filename = data.get('filename')
        category = data.get('category', '')
        if not filename:
            self.send_error(400, 'filename required')
            return
        filename = os.path.basename(filename)
        if filename not in list_images():
            self.send_error(404, 'Image not found')
            return
        db = load_db()
        if category and category not in db.get('categories', []):
            self.send_error(404, 'Category not found')
            return
        db.setdefault('assignments', {})[filename] = category or ''
        save_db(db)
        self.send_json({'ok': True, 'filename': filename, 'category': category or ''})

    def handle_delete_image(self, parsed):
        # DELETE /api/images/<filename>
        parts = parsed.path.split('/')
        if len(parts) < 4:
            self.send_error(400, 'Bad request')
            return
        name = urllib.parse.unquote(parts[3])
        name = os.path.basename(name)
        path = os.path.join(IMAGES_DIR, name)
        # safety checks
        if not os.path.commonpath([os.path.abspath(path), IMAGES_DIR]) == os.path.abspath(IMAGES_DIR):
            self.send_error(400, 'Invalid filename')
            return
        if not os.path.exists(path):
            self.send_error(404, 'Image not found')
            return
        try:
            os.remove(path)
        except Exception as e:
            self.send_error(500, f'Failed to delete: {e}')
            return
        # remove assignment
        db = load_db()
        if name in db.get('assignments', {}):
            del db['assignments'][name]
            save_db(db)
        self.send_json({'ok': True, 'filename': name})

    # ---------- utilities ----------
    def send_json(self, obj, status=200):
        data = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def pick_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def run_server():
    ensure_dirs()
    port = pick_port()
    handler = APIServerHandler
    httpd = HTTPServer(('127.0.0.1', port), handler)
    url = f'http://127.0.0.1:{port}/{GALLERY_NAME}'
    print(f'Serving on {url}')
    # open browser
    threading.Thread(target=lambda: webbrowser.open(url), daemon=True).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('Shutting down server')
        httpd.server_close()


if __name__ == '__main__':
    run_server()
