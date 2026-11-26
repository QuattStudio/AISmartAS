# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_all


ROOT = Path(SPECPATH)
deep_data, deep_binaries, deep_hidden = collect_all("deepface")
retina_data, retina_binaries, retina_hidden = collect_all("retinaface")

a = Analysis(
    [str(ROOT / "app" / "main.py")],
    pathex=[str(ROOT / "app")],
    binaries=deep_binaries + retina_binaries,
    datas=deep_data + retina_data + [
        (str(ROOT / "app" / "frontend" / "templates"), "frontend/templates"),
    ],
    hiddenimports=deep_hidden + retina_hidden + [
        "core.paths",
        "database.database",
        "frontend.app",
        "vision.camera",
        "vision.network",
        "vision.recogination",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="app",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
