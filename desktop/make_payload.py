"""
Zips dist/JobAggregator into dist/payload.zip with strong LZMA compression, for
installer_build.spec to bundle as a single compact file instead of copying
hundreds of loose files individually. Run this AFTER build.spec and BEFORE
installer_build.spec:

    pyinstaller build.spec
    python make_payload.py
    pyinstaller installer_build.spec
"""

import os
import zipfile

DESKTOP_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_DIR = os.path.join(DESKTOP_DIR, "dist", "JobAggregator")
OUTPUT_ZIP = os.path.join(DESKTOP_DIR, "dist", "payload.zip")

if not os.path.isdir(SOURCE_DIR):
    raise SystemExit(f"Expected {SOURCE_DIR} to exist — run 'pyinstaller build.spec' first.")

if os.path.exists(OUTPUT_ZIP):
    os.remove(OUTPUT_ZIP)

print("Compressing application payload with LZMA compression...")
with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_LZMA) as zf:
    for root, _, files in os.walk(SOURCE_DIR):
        for filename in files:
            file_path = os.path.join(root, filename)
            arcname = os.path.relpath(file_path, SOURCE_DIR)
            zf.write(file_path, arcname)

print(f"Created {OUTPUT_ZIP} ({os.path.getsize(OUTPUT_ZIP) / (1024 * 1024):.1f} MB)")
