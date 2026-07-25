# desktop/installer_build.spec
# Bundles the compiled JobAggregator app folder into payload/ and produces JobAggregatorSetup.exe

import os

block_cipher = None

icon_param = "icon.ico" if os.path.exists("icon.ico") else None

a = Analysis(
    ["installer_gui.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("dist/JobAggregator", "payload"),
    ],
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
    name="JobAggregatorSetup",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=icon_param,
)
