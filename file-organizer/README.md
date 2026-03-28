# AI File Organizer

A user-friendly Linux desktop application that helps organize cluttered directories using AI-powered suggestions.

## Features

- **Smart Analysis** - Scans your folder and breaks down files by type
- **AI-Powered Suggestions** - Uses OpenAI to suggest logical folder categories based on your files
- **Visual Review** - Edit, rename, delete, or add folder suggestions before organizing
- **Safe Operations** - Preview all changes before files are moved
- **Undo Support** - Reverse any organization operation with one click
- **Progress Tracking** - Visual progress bar during file organization

## Requirements

- Python 3.8+
- Linux (tested on Ubuntu/Debian)
- OpenAI API key

## Installation

```bash
cd file-organizer
pip install -r requirements.txt
```

## Setup

1. Get an OpenAI API key from [platform.openai.com](https://platform.openai.com/api-keys)
2. Run the application:

```bash
python main.py
```

3. On first launch, you'll be prompted to enter your API key

Alternatively, create a `.env` file:

```bash
cp .env.example .env
# Edit .env and add your API key
```

## Usage

1. **Select Folder** - Click "Browse" to choose a folder to organize
2. **Analyze** - Click "Analyze Files" to scan the directory
3. **Review Suggestions** - The AI suggests folder categories. Edit names, delete suggestions, or add your own
4. **Preview** - Review exactly which files will move where
5. **Organize** - Click "Organize Files" to sort everything into folders
6. **Undo** - Changed your mind? Click "Undo" to reverse the operation

## Settings

Access settings from the File menu to configure:

- OpenAI API key
- AI model (gpt-4o-mini or gpt-4o)
- Number of folder suggestions (3-8)
- Theme (Light/Dark)

## Project Structure

```
file-organizer/
├── main.py              # Application entry point
├── core/                # Business logic
│   ├── analyzer.py      # File analysis
│   ├── ai_suggester.py  # OpenAI integration
│   ├── file_mover.py    # File operations
│   └── undo_manager.py  # Undo tracking
├── gui/                 # PyQt6 interface
│   ├── main_window.py   # Main application window
│   ├── folder_selection.py
│   ├── suggestions.py
│   ├── preview.py
│   ├── progress.py
│   └── dialogs.py
├── utils/               # Utilities
│   ├── file_icons.py    # File type icons
│   └── validators.py    # Input validation
└── resources/
    └── styles.qss       # Qt stylesheet
```

## License

MIT
