# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec za Dentaland desktop aplikaciju (DENT-IMPROVE-009).

Build se pokreće iz korijena repoa (ili bilo gdje — putanje su vezane za
lokaciju ovog spec fajla preko ``SPEC`` global):

    pyinstaller packaging/dentaland.spec

Rezultat: ``dist/Dentaland/Dentaland.exe`` (onedir, GUI bez konzole).
Pakuje se SAMO desktop app (Faza 0) — backend i web/ javna forma nisu u
obimu (vidi Task Contract).
"""

from pathlib import Path

# SPEC = apsolutna putanja do ovog .spec fajla (PyInstaller global).
# repo root = packaging/.. = parents[1].
ROOT = Path(SPEC).resolve().parents[1]

a = Analysis(
    [str(ROOT / "desktop" / "app.py")],
    # ``dentaland`` paket živi u src/, ``desktop`` u korijenu — oba moraju
    # biti na path-u da bi PyInstaller analizirao importe.
    pathex=[str(ROOT), str(ROOT / "src")],
    binaries=[],
    datas=[
        # Layout se poklapa sa paths.resource_path() (_MEIPASS grana):
        #   resource_path("web", "assets", "logo.png")
        #       -> <_internal>/web/assets/logo.png
        #   resource_path("desktop", "assets", "doctors", "ljubo.png")
        #       -> <_internal>/desktop/assets/doctors/ljubo.png
        (str(ROOT / "web" / "assets"), "web/assets"),
        (str(ROOT / "desktop" / "assets" / "doctors"), "desktop/assets/doctors"),
    ],
    hiddenimports=[],
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
    name="Dentaland",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(ROOT / "web" / "assets" / "dentaland.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Dentaland",
)
