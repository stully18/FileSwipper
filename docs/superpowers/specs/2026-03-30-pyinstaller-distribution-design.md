# PyInstaller Distribution Design

**Date:** 2026-03-30
**Status:** Approved

## Problem

Users on Linux get an xcb platform plugin error when running `run.sh` because
`libxcb-cursor0` is a Qt system dependency not bundled with the PyQt6 pip package.
Users should not need to manually install system packages.

## Goal

Package FileSwipper as a self-contained binary for Linux and Windows using PyInstaller
(onedir mode). Users download, extract, and run — no Python, no pip, no system deps.

## Decisions

- **Single spec file** (`file-organizer/fileswipper.spec`) with `if sys.platform == 'linux':`
  guards. Chosen over separate per-platform specs for simplicity and easier GitHub reading.
- **onedir mode** — faster startup, easier to debug missing libs vs onefile.
- **No app icon** — skipped for now, can be added later.
- **No Docker, no splash screen, no auto-updater** — out of scope.

## Files to Create / Modify

| File | Action | Purpose |
|------|--------|---------|
| `file-organizer/fileswipper.spec` | Create | PyInstaller spec — bundles Qt xcb libs, styles.qss, hidden imports |
| `build-linux.sh` | Create | Dev/CI build script — venv, pyinstaller, tar.gz output |
| `build-windows.bat` | Create | Windows build script — venv, pyinstaller, zip output |
| `.github/workflows/build.yml` | Create | CI — builds both platforms, uploads artifacts to GitHub Release |
| `run.sh` | Update | Add dev-only comment + auto-install libxcb-cursor0 if missing |
| `file-organizer/README.md` | Update | Fix stale OpenAI references, add Download & Run section |

## Spec File Structure

```
fileswipper.spec
├── Platform detection (sys.platform)
├── datas: [('resources/styles.qss', 'resources')]
├── binaries: collect_dynamic_libs('PyQt6') on Linux (catches libxcb-cursor.so*)
├── hiddenimports: PyQt6.QtCore/QtGui/QtWidgets/sip, google.genai, google.auth,
│                  google.auth.transport, dotenv
└── Analysis → PYZ → EXE → COLLECT
    ├── name='FileSwipper'
    ├── console=False on Windows, True on Linux (for debug)
    └── onedir output to dist/FileSwipper/
```

## GitHub Actions Workflow

Triggers: push to `main` and GitHub Release published.

- **build-linux** on `ubuntu-22.04`:
  1. Install xcb system libs (needed to build; PyInstaller collects them into bundle)
  2. pip install pyinstaller + requirements.txt
  3. Run spec → produces `dist/FileSwipper/`
  4. Archive to `FileSwipper-linux-x86_64.tar.gz`
  5. Upload as workflow artifact; if Release event, upload to the release

- **build-windows** on `windows-latest`:
  1. pip install pyinstaller + requirements.txt
  2. Run spec → produces `dist\FileSwipper\`
  3. Archive to `FileSwipper-windows-x64.zip`
  4. Upload as workflow artifact; if Release event, upload to the release

## README Updates

- Replace all "OpenAI" references with "Google Gemini"
- Replace OpenAI API key instructions with Gemini (get free key at ai.google.dev)
- Replace model references (gpt-4o-mini/gpt-4o → gemini-2.5-flash-lite)
- Add "Download & Run" section near the top:
  - Linux: download tar.gz, extract, run `./FileSwipper`
  - Windows: download zip, extract, run `FileSwipper.exe`
  - Need a Gemini API key (free) — entered in app on first run
  - No Python required

## Verification

After building locally:
1. `dist/FileSwipper/` must contain `libxcb-cursor.so*` (Linux)
2. `./dist/FileSwipper/FileSwipper` launches with no xcb errors
3. Stylesheet loads correctly (UI has correct styling)
