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
