# desktop/uninstaller_build.spec
#
# Builds uninstall.exe — a standalone, single-file executable containing the
# uninstall wizard from uninstaller_gui.py.
#
# BUILD ORDER MATTERS. This must be built and copied into dist/JobAggregator/
# (the main app's onedir output from build.spec) BEFORE running
# installer_build.spec, so that uninstall.exe travels inside the installer's
# payload and ends up sitting in the installed application folder — which is
# where installer_gui.py's register_uninstaller() points Windows' "Uninstall"
# entry to.
#
# Full build sequence, run in this order from inside desktop/:
#   1. pyinstaller build.spec                       -> dist/JobAggregator/JobAggregator.exe
#   2. pyinstaller uninstaller_build.spec            -> dist/uninstall.exe
#   3. copy dist/uninstall.exe  dist/JobAggregator/uninstall.exe
#   4. pyinstaller installer_build.spec              -> dist/JobAggregatorSetup.exe
#
# Onefile mode is used here deliberately, unlike the main app's onedir build —
# the uninstaller has minimal dependencies (just tkinter and the standard
# library), so onefile packaging risk is low, and a single self-contained exe
# is what makes the "delete my own folder, including myself" trick in
# uninstaller_gui.py's schedule_self_delete() simple: there's exactly one file
# to account for, not a whole folder of DLLs and dependencies.

import os

block_cipher = None
icon_param = "icon.ico" if os.path.exists("icon.ico") else None

a = Analysis(
    ["uninstaller_gui.py"],
    pathex=["."],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="uninstall",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,     # no console window for the uninstall wizard
    icon=icon_param,
)
