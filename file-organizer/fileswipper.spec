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
    upx=False,
    console=(sys.platform != 'win32'),
    disable_windowed_traceback=False,
    argv_emulation=False,       # macOS-only; ignored on Linux/Windows
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
    upx=False,
    name='FileSwipper',
)
