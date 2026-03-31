# PyInstaller Production Distribution — Implementation Prompt

## Context

This is the AI File Organizer app — a PyQt6 desktop GUI that uses Google Gemini to suggest
folder organization categories for a user's files. It is located at:

```
/home/shane/Development/FileSwipper/
├── run.sh                          # Current dev launcher (source of the xcb error)
├── file-organizer/
│   ├── main.py                     # Entry point — creates QApplication, loads MainWindow
│   ├── requirements.txt            # PyQt6>=6.6.0, google-genai>=1.0.0, python-dotenv>=1.0.0
│   ├── .env.example                # GEMINI_API_KEY=your_key_here
│   ├── resources/
│   │   └── styles.qss              # Qt stylesheet loaded at startup
│   ├── core/
│   │   ├── __init__.py
│   │   ├── ai_suggester.py         # Google Gemini integration
│   │   ├── analyzer.py
│   │   ├── file_mover.py
│   │   └── undo_manager.py
│   └── gui/
│       ├── __init__.py
│       ├── main_window.py
│       ├── dialogs.py
│       ├── folder_selection.py
│       ├── preview.py
│       ├── progress.py
│       └── suggestions.py
```

## The Problem

Users get this error on Linux when running `run.sh`:
```
qt.qpa.plugin: From 6.5.0, xcb-cursor0 or libxcb-cursor0 is needed to load the Qt xcb platform plugin.
qt.qpa.plugin: Could not load the Qt platform plugin "xcb" in "" even though it was found.
This application failed to start because no Qt platform plugin could be initialized.
```

This happens because the system is missing `libxcb-cursor0`, a Qt system dependency that is
NOT bundled with the PyQt6 pip package. Users should not need to manually install system packages.

## Goal

Make this app production-ready for distribution to end users on **Linux and Windows** using
**PyInstaller** — so users download and run a binary with no Python, no `pip install`, and no
system dependency headaches.

## What To Implement

### 1. PyInstaller spec file (`file-organizer/fileswipper.spec`)

Create a PyInstaller `.spec` file (not just a CLI command) that:

- Entry point: `file-organizer/main.py`
- App name: `FileSwipper`
- Bundles ALL Qt platform plugins (especially `xcb` and its cursor library on Linux)
- Includes `resources/styles.qss` as a data file
- Collects all hidden imports for `google.genai`, `google-genai`, `dotenv`
- On Linux: explicitly collects `libxcb-cursor.so*` and other xcb libs that PyInstaller misses
- On Windows: sets the icon if one is provided, creates a windowed (no console) exe
- `onedir` mode (not `onefile`) — faster startup, easier to debug

Use `PyInstaller.utils.hooks` collect functions where needed:
```python
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
```

### 2. Build scripts

**`build-linux.sh`** — runs on Linux:
```
- Creates/activates a venv
- pip install pyinstaller + requirements.txt
- Runs pyinstaller with the spec file
- Output: dist/FileSwipper/ folder
- Zips it to dist/FileSwipper-linux-x86_64.tar.gz
```

**`build-windows.bat`** — runs on Windows:
```
- Creates/activates a venv
- pip install pyinstaller + requirements.txt
- Runs pyinstaller with the spec file
- Output: dist\FileSwipper\ folder
```

### 3. GitHub Actions workflow (`.github/workflows/build.yml`)

Triggered on: push to `main` AND when a GitHub Release is published.

Jobs:
- `build-linux`: runs on `ubuntu-22.04`, produces `FileSwipper-linux-x86_64.tar.gz`
- `build-windows`: runs on `windows-latest`, produces `FileSwipper-windows-x64.zip`

When triggered by a Release event: upload both artifacts to the GitHub Release automatically.

The workflow must install system deps on the Linux runner:
```
sudo apt-get install -y libxcb-cursor0 libxcb-xinerama0 libxcb-icccm4 libxcb-image0 \
  libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-shape0 libxcb-xkb1 \
  libxkbcommon-x11-0 libgl1
```
(These are needed to BUILD, and PyInstaller will collect them into the bundle so users don't need them.)

### 4. Update `run.sh` for dev use only

Add a comment clarifying `run.sh` is for development only. Also add a check at the top that
installs `libxcb-cursor0` if missing (for devs):
```bash
if ! dpkg -l libxcb-cursor0 &>/dev/null 2>&1; then
    echo "Installing missing Qt dependency libxcb-cursor0..."
    sudo apt-get install -y libxcb-cursor0 2>/dev/null || true
fi
```

### 5. User-facing README section

Add a "Download & Run" section to the existing README (or create one if none exists) that explains:
- Download the release for your platform from GitHub Releases
- Linux: extract tar.gz, run `./FileSwipper`
- Windows: extract zip, run `FileSwipper.exe`
- Users need a Gemini API key (free at ai.google.dev) — entered in the app on first run
- No Python installation required

## Key Technical Details

### PyInstaller xcb fix (critical for Linux)

PyInstaller doesn't always collect `libxcb-cursor.so.0`. In the spec file, add:

```python
import sys
from PyInstaller.utils.hooks import collect_dynamic_libs

binaries = []
if sys.platform == 'linux':
    binaries += collect_dynamic_libs('PyQt6')
```

Also add these hidden imports to handle PyQt6 Qt plugin discovery:
```python
hiddenimports = [
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.sip',
    'google.genai',
    'google.auth',
    'google.auth.transport',
    'dotenv',
]
```

### Data files

The `resources/styles.qss` must be accessible at runtime. In the spec:
```python
datas = [
    ('resources/styles.qss', 'resources'),
]
```

And `main.py` already loads it via `Path(__file__).parent / "resources" / "styles.qss"` —
this works correctly in PyInstaller bundles because `__file__` resolves correctly in onedir mode.

### QSettings on Windows

`QSettings` with `SETTINGS_ORG = "AIFileOrganizer"` will use the Windows registry. No change
needed — PyQt6 handles this automatically.

## Verification Steps

After implementing, verify by:

1. Running `build-linux.sh` locally
2. Checking `dist/FileSwipper/` contains `libxcb-cursor.so*` or similar xcb libs
3. Running `dist/FileSwipper/FileSwipper` — should launch with no xcb errors
4. Confirming styles.qss is loaded (UI has correct styling)

## Do NOT

- Do not use `--onefile` mode (slower startup, harder to debug missing libs)
- Do not use Docker
- Do not add a splash screen or auto-updater (out of scope)
- Do not change any application logic — only build/distribution infrastructure
