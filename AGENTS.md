# AGENTS.md

## Cursor Cloud specific instructions

### Overview

FileSwipper is a **single PyQt6 desktop application** (not a monorepo) that uses Google Gemini AI to suggest folder categories for files, then organizes them with undo support. The source lives under `file-organizer/`.

### Running the application

- Development launch: `./run.sh` from repo root (creates venv, installs deps, launches GUI).
- Manual: `cd file-organizer && source venv/bin/activate && python main.py`
- The app requires a display server. On headless VMs use `DISPLAY=:1` (the cloud VM desktop) or `xvfb-run`.
- System dependency required on Linux: `libxcb-cursor0`, `libegl1`, `libgl1`, and other xcb libraries (see `build-linux.sh` header for full list). These are pre-installed in the VM snapshot.

### API key

- The app prompts for a Gemini API key on first launch. Without one, the "Use Basic Sorting" fallback categorizes files by extension (no AI).
- To supply a key, either set the `GEMINI_API_KEY` secret or create `file-organizer/.env` from `.env.example`.

### Testing

- There are **no automated tests** in this repository (no test framework or `tests/` directory).
- Manual testing: launch the app, browse to a folder with mixed file types, click "Analyze Files", then use "Use Basic Sorting" (or AI if a key is configured) to verify categorization.

### Building

- `./build-linux.sh` produces a distributable tarball via PyInstaller (not needed for development).

### Dependencies

- Python packages: see `file-organizer/requirements.txt` (PyQt6, google-genai, python-dotenv).
- The venv lives at `file-organizer/venv/` and is created by `run.sh` on first run.
