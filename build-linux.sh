#!/bin/bash
# build-linux.sh — FOR DEVELOPMENT / CI USE ONLY
# Produces dist/FileSwipper-linux-x86_64.tar.gz
#
# Prerequisites (needed to build; PyInstaller bundles them so users don't need them):
#   sudo apt-get install -y libxcb-cursor0 libxcb-xinerama0 libxcb-icccm4 \
#     libxcb-image0 libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 \
#     libxcb-shape0 libxcb-xkb1 libxkbcommon-x11-0 libgl1

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$SCRIPT_DIR/file-organizer"
BUILD_VENV="$SCRIPT_DIR/.build-venv"
DIST_DIR="$SCRIPT_DIR/dist"  # archive destination (PyInstaller writes to file-organizer/dist/)

echo "=== FileSwipper Linux Build ==="

# Build venv is kept separate from the dev venv inside file-organizer/
if [ ! -d "$BUILD_VENV" ]; then
    echo "Creating build virtual environment..."
    python3 -m venv "$BUILD_VENV"
fi

if [ ! -f "$BUILD_VENV/bin/activate" ]; then
    echo "ERROR: venv creation failed — activate not found at $BUILD_VENV/bin/activate" >&2
    exit 1
fi

source "$BUILD_VENV/bin/activate"

echo "Installing build dependencies..."
pip install --quiet --upgrade pip
pip install --quiet pyinstaller
pip install --quiet -r "$APP_DIR/requirements.txt"

# PyInstaller must run from inside file-organizer/ — all spec paths are relative to it
echo "Running PyInstaller..."
cd "$APP_DIR"
pyinstaller fileswipper.spec --clean --noconfirm

# Archive the onedir bundle
if [ ! -d "$APP_DIR/dist/FileSwipper" ]; then
    echo "ERROR: PyInstaller output not found at $APP_DIR/dist/FileSwipper" >&2
    exit 1
fi

echo "Archiving..."
mkdir -p "$DIST_DIR"
OUTPUT="$DIST_DIR/FileSwipper-linux-x86_64.tar.gz"
tar -czf "$OUTPUT" -C "$APP_DIR/dist" FileSwipper

echo ""
echo "Build complete: $OUTPUT"
echo "Test it: tar -xzf $OUTPUT && ./FileSwipper/FileSwipper"
