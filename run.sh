#!/bin/bash
# run.sh — DEVELOPMENT LAUNCHER ONLY
#
# This script runs FileSwipper directly from source for development.
# For distributable builds, use build-linux.sh instead.
#
# Installs libxcb-cursor0 if missing — required by Qt 6.5+ on Linux.
# End-users of the distributed binary do NOT need this (it is bundled).

set -e

if ! dpkg -l libxcb-cursor0 &>/dev/null 2>&1; then
    echo "Installing missing Qt dependency libxcb-cursor0..."
    sudo apt-get install -y libxcb-cursor0 2>/dev/null || true
fi

cd "$(dirname "$0")/file-organizer"

if [ ! -d "venv" ]; then
    echo "Setting up virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

python main.py
