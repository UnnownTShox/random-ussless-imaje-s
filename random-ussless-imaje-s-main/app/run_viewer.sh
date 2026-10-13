#!/bin/sh
# Simple launcher for Unix-like systems (Linux / macOS)
# Requires python3 on PATH
DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$DIR/viewer.py"
