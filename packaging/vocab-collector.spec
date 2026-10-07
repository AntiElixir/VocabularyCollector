# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onedir spec: no UPX, no console, config/ and data/ beside the exe."""

import os

ROOT = os.path.abspath(os.path.join(SPECPATH, os.pardir))

a = Analysis(
    [os.path.join(ROOT, "scripts", "run_app.py")],
    pathex=[os.path.join(ROOT, "src")],
    binaries=[],
    datas=[],
    hiddenimports=[
        "pynput.keyboard._win32",
        "pynput.mouse._win32",
        "pynput._util.win32",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="VocabularyCollector",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="VocabularyCollector",
)