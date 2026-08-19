# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('azra.ico', '.'),
        ('azra-logo.png', '.'),
        ('rafine.ico', '.'),
        ('rafine-logo.jpg', '.'),
        ('emir-logo.jpg', '.'),
        ('emir-video.mp4', '.'),
        ('emir-yıldız.png', '.'),
        ('update_config.json', '.'),
        ('C:/Program Files/Tesseract-OCR', 'tesseract'),
    ],
    hiddenimports=[],
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
    [],
    exclude_binaries=True,
    name='AZRA CONVERTER',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['azra.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AZRA CONVERTER',
)
