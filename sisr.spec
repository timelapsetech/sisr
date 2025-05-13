# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all submodules
hidden_imports = collect_submodules('sisr')

# Add specific imports that might be needed
hidden_imports.extend([
    'PIL',
    'PIL._tkinter_finder',
    'tkinter',
    'tkinter.ttk',
    'tkinter.messagebox',
    'tkinter.filedialog',
])

# Find ffmpeg binary
ffmpeg_path = None
if sys.platform == 'darwin':
    try:
        import subprocess
        ffmpeg_path = subprocess.check_output(['which', 'ffmpeg']).decode().strip()
    except:
        pass

binaries = []
if ffmpeg_path and os.path.exists(ffmpeg_path):
    binaries.append((ffmpeg_path, '.'))

a = Analysis(
    ['sisr/__main__.py'],
    pathex=[os.path.abspath(os.path.dirname('sisr/__main__.py'))],
    binaries=binaries,
    datas=collect_data_files('sisr'),
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SISR',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Set to True temporarily for debugging
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SISR',
)

app = BUNDLE(
    coll,
    name='SISR.app',
    icon='resources/icon.icns',
    bundle_identifier='com.sisr.app',
    info_plist={
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'NSHighResolutionCapable': 'True',
        'LSBackgroundOnly': 'False',
        'NSRequiresAquaSystemAppearance': 'False',
        'NSPrincipalClass': 'NSApplication',
        'CFBundleExecutable': 'SISR',
        'CFBundlePackageType': 'APPL',
        'CFBundleSignature': '????',
    },
) 