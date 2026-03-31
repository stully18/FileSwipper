# PyInstaller Distribution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Package FileSwipper as a self-contained binary for Linux and Windows so users download, extract, and run — no Python, no pip, no system deps.

**Architecture:** Single PyInstaller spec file with platform guards collects Qt xcb libs on Linux and produces a onedir bundle. Two build scripts (bash/bat) drive local builds; a GitHub Actions workflow builds both platforms on push and uploads to GitHub Releases on release publish. No application logic changes.

**Tech Stack:** PyInstaller 6+, PyQt6, google-genai, python-dotenv, GitHub Actions, softprops/action-gh-release@v2

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `file-organizer/fileswipper.spec` | Create | PyInstaller spec — datas, binaries, hiddenimports, EXE/COLLECT |
| `build-linux.sh` | Create | Create build venv, run pyinstaller, produce tar.gz |
| `build-windows.bat` | Create | Create build venv, run pyinstaller (Windows) |
| `.github/workflows/build.yml` | Create | CI: build Linux + Windows, upload artifacts and release assets |
| `run.sh` | Modify | Add dev-only comment + auto-install libxcb-cursor0 guard |
| `file-organizer/README.md` | Modify | Fix stale OpenAI references, add Download & Run section |

---

### Task 1: Create PyInstaller spec file

**Files:**
- Create: `file-organizer/fileswipper.spec`

Note: No unit tests for build config. Verification is running the build in Task 2.

- [ ] **Step 1: Write the spec file**

Create `file-organizer/fileswipper.spec` with this exact content:

```python
# fileswipper.spec
#
# PyInstaller build spec for FileSwipper.
# Run from inside file-organizer/:
#   pyinstaller fileswipper.spec --clean --noconfirm
#
# Platform guards handle Linux xcb library collection automatically.

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_dynamic_libs


# ── Data files ───────────────────────────────────────────────────────────────
# styles.qss is loaded at runtime via Path(__file__).parent / "resources" / "styles.qss"
# onedir mode keeps __file__ correct so no sys._MEIPASS dance needed.

datas = [
    ('resources/styles.qss', 'resources'),
]
datas += collect_data_files('google.genai')
datas += collect_data_files('google.auth')


# ── Binaries ─────────────────────────────────────────────────────────────────
# On Linux, PyInstaller misses libxcb-cursor.so.0 and related xcb libs.
# collect_dynamic_libs('PyQt6') finds everything linked by the PyQt6 package
# and adds it to the bundle — users then need no system Qt libs at all.

binaries = []
if sys.platform == 'linux':
    binaries += collect_dynamic_libs('PyQt6')


# ── Hidden imports ────────────────────────────────────────────────────────────
# PyInstaller static analysis misses dynamically-loaded Qt plugins and
# google.genai submodules. List them explicitly so they land in the bundle.

hiddenimports = [
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.sip',
    'google.genai',
    'google.auth',
    'google.auth.transport',
    'google.auth.transport.requests',
    'dotenv',
]
hiddenimports += collect_submodules('google.genai')
hiddenimports += collect_submodules('google.auth')


# ── Analysis ──────────────────────────────────────────────────────────────────

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)


# ── Executable ────────────────────────────────────────────────────────────────
# console=False on Windows hides the terminal window (GUI app behaviour).
# console=True on Linux keeps stdout visible for debugging xcb errors.

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FileSwipper',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=(sys.platform != 'win32'),
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)


# ── Collect (onedir) ──────────────────────────────────────────────────────────
# Output: dist/FileSwipper/   (all libs + exe in one directory)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='FileSwipper',
)
```

- [ ] **Step 2: Commit**

```bash
git add file-organizer/fileswipper.spec
git commit -m "build: add PyInstaller spec for Linux and Windows"
```

---

### Task 2: Create Linux build script

**Files:**
- Create: `build-linux.sh`

- [ ] **Step 1: Write the build script**

Create `build-linux.sh` at the repo root:

```bash
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
DIST_DIR="$SCRIPT_DIR/dist"

echo "=== FileSwipper Linux Build ==="

# Build venv is kept separate from the dev venv inside file-organizer/
if [ ! -d "$BUILD_VENV" ]; then
    echo "Creating build virtual environment..."
    python3 -m venv "$BUILD_VENV"
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
echo "Archiving..."
mkdir -p "$DIST_DIR"
OUTPUT="$DIST_DIR/FileSwipper-linux-x86_64.tar.gz"
tar -czf "$OUTPUT" -C "$APP_DIR/dist" FileSwipper

echo ""
echo "Build complete: $OUTPUT"
echo "Test it: tar -xzf $OUTPUT && ./FileSwipper/FileSwipper"
```

- [ ] **Step 2: Make it executable**

```bash
chmod +x build-linux.sh
```

- [ ] **Step 3: Commit**

```bash
git add build-linux.sh
git commit -m "build: add Linux build script"
```

---

### Task 3: Create Windows build script

**Files:**
- Create: `build-windows.bat`

- [ ] **Step 1: Write the build script**

Create `build-windows.bat` at the repo root:

```bat
@echo off
:: build-windows.bat — FOR DEVELOPMENT / CI USE ONLY
:: Produces file-organizer\dist\FileSwipper\
::
:: Run from repo root on a Windows machine with Python 3.10+ installed.
setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set APP_DIR=%SCRIPT_DIR%file-organizer
set BUILD_VENV=%SCRIPT_DIR%.build-venv

echo === FileSwipper Windows Build ===

if not exist "%BUILD_VENV%" (
    echo Creating build virtual environment...
    python -m venv "%BUILD_VENV%"
    if errorlevel 1 (
        echo ERROR: python not found. Install Python 3.10+ and add to PATH.
        exit /b 1
    )
)

call "%BUILD_VENV%\Scripts\activate.bat"

echo Installing build dependencies...
pip install --quiet --upgrade pip
pip install --quiet pyinstaller
pip install --quiet -r "%APP_DIR%\requirements.txt"

echo Running PyInstaller...
cd /d "%APP_DIR%"
pyinstaller fileswipper.spec --clean --noconfirm

echo.
echo Build complete: %APP_DIR%\dist\FileSwipper\
echo Test it: double-click %APP_DIR%\dist\FileSwipper\FileSwipper.exe
```

- [ ] **Step 2: Commit**

```bash
git add build-windows.bat
git commit -m "build: add Windows build script"
```

---

### Task 4: Create GitHub Actions workflow

**Files:**
- Create: `.github/workflows/build.yml`

- [ ] **Step 1: Create the workflow directory**

```bash
mkdir -p .github/workflows
```

- [ ] **Step 2: Write the workflow**

Create `.github/workflows/build.yml`:

```yaml
name: Build

on:
  push:
    branches: [main]
  release:
    types: [published]

jobs:
  # ── Linux ───────────────────────────────────────────────────────────────────
  build-linux:
    runs-on: ubuntu-22.04

    steps:
      - uses: actions/checkout@v4

      - name: Install Qt system dependencies
        # These are needed to BUILD on the runner.
        # PyInstaller collects them into the bundle so end-users don't need them.
        run: |
          sudo apt-get update
          sudo apt-get install -y \
            libxcb-cursor0 libxcb-xinerama0 libxcb-icccm4 libxcb-image0 \
            libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-shape0 \
            libxcb-xkb1 libxkbcommon-x11-0 libgl1

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install Python dependencies
        run: |
          pip install pyinstaller
          pip install -r file-organizer/requirements.txt

      - name: Build with PyInstaller
        run: |
          cd file-organizer
          pyinstaller fileswipper.spec --clean --noconfirm

      - name: Archive bundle
        run: |
          tar -czf FileSwipper-linux-x86_64.tar.gz -C file-organizer/dist FileSwipper

      - name: Upload build artifact
        uses: actions/upload-artifact@v4
        with:
          name: FileSwipper-linux-x86_64
          path: FileSwipper-linux-x86_64.tar.gz
          retention-days: 7

      - name: Upload to GitHub Release
        if: github.event_name == 'release'
        uses: softprops/action-gh-release@v2
        with:
          files: FileSwipper-linux-x86_64.tar.gz

  # ── Windows ─────────────────────────────────────────────────────────────────
  build-windows:
    runs-on: windows-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install Python dependencies
        run: |
          pip install pyinstaller
          pip install -r file-organizer/requirements.txt

      - name: Build with PyInstaller
        run: |
          cd file-organizer
          pyinstaller fileswipper.spec --clean --noconfirm

      - name: Archive bundle
        run: |
          Compress-Archive -Path file-organizer/dist/FileSwipper `
                           -DestinationPath FileSwipper-windows-x64.zip

      - name: Upload build artifact
        uses: actions/upload-artifact@v4
        with:
          name: FileSwipper-windows-x64
          path: FileSwipper-windows-x64.zip
          retention-days: 7

      - name: Upload to GitHub Release
        if: github.event_name == 'release'
        uses: softprops/action-gh-release@v2
        with:
          files: FileSwipper-windows-x64.zip
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/build.yml
git commit -m "ci: add GitHub Actions build workflow for Linux and Windows"
```

---

### Task 5: Update run.sh

**Files:**
- Modify: `run.sh`

Current content:
```bash
#!/bin/bash
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
```

- [ ] **Step 1: Update run.sh**

Replace the entire content of `run.sh` with:

```bash
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
```

- [ ] **Step 2: Commit**

```bash
git add run.sh
git commit -m "build: clarify run.sh is dev-only, auto-install libxcb-cursor0"
```

---

### Task 6: Update README.md

**Files:**
- Modify: `file-organizer/README.md`

- [ ] **Step 1: Rewrite README.md**

Replace the entire content of `file-organizer/README.md` with:

```markdown
# FileSwipper

A desktop app that uses Google Gemini AI to suggest folder categories for your files,
then organizes them safely with full undo support.

## Download & Run

No Python installation required.

**Linux:**
1. Download `FileSwipper-linux-x86_64.tar.gz` from [GitHub Releases](../../releases)
2. Extract and run:
   ```bash
   tar -xzf FileSwipper-linux-x86_64.tar.gz
   ./FileSwipper/FileSwipper
   ```

**Windows:**
1. Download `FileSwipper-windows-x64.zip` from [GitHub Releases](../../releases)
2. Extract the zip, then double-click `FileSwipper.exe`

On first launch you'll be prompted for a Gemini API key.
Get a free key at [ai.google.dev](https://ai.google.dev).

---

## Features

- **Smart Analysis** — Scans your folder and breaks down files by type
- **AI-Powered Suggestions** — Uses Google Gemini to suggest logical folder categories based on your files
- **Visual Review** — Edit, rename, delete, or add folder suggestions before organizing
- **Safe Operations** — Preview all changes before files are moved
- **Undo Support** — Reverse any organization operation with one click
- **Progress Tracking** — Visual progress bar during file organization

## Development Setup

Requires Python 3.10+ and Linux or Windows.

```bash
# Install Qt system dependency (Linux only)
sudo apt-get install -y libxcb-cursor0

# Run from source
./run.sh
```

Or manually:

```bash
cd file-organizer
pip install -r requirements.txt
python main.py
```

## Configuration

On first launch, enter your Gemini API key when prompted.

Alternatively, create a `.env` file:

```bash
cp file-organizer/.env.example file-organizer/.env
# Edit .env and set GEMINI_API_KEY=your_key_here
```

## Settings

Access settings from the File menu to configure:

- Gemini API key
- AI model (default: `gemini-2.5-flash-lite`)
- Number of folder suggestions (3–8)
- Theme (Light/Dark)

## Usage

1. **Select Folder** — Click "Browse" to choose a folder to organize
2. **Analyze** — Click "Analyze Files" to scan the directory
3. **Review Suggestions** — Gemini suggests folder categories. Edit names, delete suggestions, or add your own
4. **Preview** — Review exactly which files will move where
5. **Organize** — Click "Organize Files" to sort everything into folders
6. **Undo** — Changed your mind? Click "Undo" to reverse the operation

## Building a Distributable

```bash
# Linux (produces dist/FileSwipper-linux-x86_64.tar.gz)
./build-linux.sh

# Windows (produces file-organizer\dist\FileSwipper\)
build-windows.bat
```

Releases are also built automatically by GitHub Actions on every push to `main`
and attached to GitHub Releases when you publish a release.

## Project Structure

```
file-organizer/
├── main.py              # Application entry point
├── fileswipper.spec     # PyInstaller build spec
├── requirements.txt
├── core/                # Business logic
│   ├── analyzer.py      # File analysis
│   ├── ai_suggester.py  # Google Gemini integration
│   ├── file_mover.py    # File operations
│   └── undo_manager.py  # Undo tracking
├── gui/                 # PyQt6 interface
│   ├── main_window.py
│   ├── folder_selection.py
│   ├── suggestions.py
│   ├── preview.py
│   ├── progress.py
│   └── dialogs.py
├── utils/
│   └── file_icons.py
└── resources/
    └── styles.qss       # Qt stylesheet
```

## License

MIT
```

- [ ] **Step 2: Commit**

```bash
git add file-organizer/README.md
git commit -m "docs: update README — fix OpenAI references, add Download & Run section"
```

---

## Verification

After all tasks are committed, run a local build to confirm the xcb fix works:

```bash
# Install build-time system deps (Linux)
sudo apt-get install -y libxcb-cursor0 libxcb-xinerama0 libxcb-icccm4 libxcb-image0 \
  libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-shape0 \
  libxcb-xkb1 libxkbcommon-x11-0 libgl1

# Build
./build-linux.sh

# Check xcb libs are present in the bundle
ls file-organizer/dist/FileSwipper/ | grep xcb

# Launch (should open with correct styling, no xcb errors)
./file-organizer/dist/FileSwipper/FileSwipper
```
