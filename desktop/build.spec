# desktop/build.spec
# Build with (run from inside the desktop/ folder):
#   pyinstaller build.spec

import os
from PyInstaller.utils.hooks import collect_data_files

playwright_datas = collect_data_files("playwright")

block_cipher = None

# Check if icon.ico exists in current directory
icon_param = "icon.ico" if os.path.exists("icon.ico") else None

a = Analysis(
    ["desktop_main.py"],
    pathex=[".", "../backend"],
    binaries=[],
    datas=[
        ("../frontend/out", "frontend_out"),
    ] + playwright_datas,
    hiddenimports=[
        "curl_cffi",
        "curl_cffi.requests",
        "playwright",
        "playwright.sync_api",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
    ],
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
    [],
    exclude_binaries=True,
    name="JobAggregator",
    debug=False,
    strip=False,
    upx=True,
    console=True,
    icon=icon_param,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name="JobAggregator",
)
