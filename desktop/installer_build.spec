# desktop/installer_build.spec
# Bundles payload (compressed payload.zip or dist/JobAggregator folder) into JobAggregatorSetup.exe

import os

block_cipher = None

icon_param = "icon.ico" if os.path.exists("icon.ico") else None

payload_is_zip = os.path.exists("dist/payload.zip")
payload_src = "dist/payload.zip" if payload_is_zip else "dist/JobAggregator"
payload_dst_name = "." if payload_is_zip else "payload"

a = Analysis(
    ["installer_gui.py"],
    pathex=["."],
    binaries=[],
    datas=[
        (payload_src, payload_dst_name),
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
