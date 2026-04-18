# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# PyInstaller defines SPEC; resolve paths so builds work from any cwd (e.g. CI).
_spec_dir = os.path.dirname(os.path.abspath(SPEC))
_main_script = os.path.join(_spec_dir, "sisr", "__main__.py")

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
    'imageio_ffmpeg',
])

# Always bundle the imageio-ffmpeg static binary (drawtext, consistent codecs).
ffmpeg_path = None
try:
    import imageio_ffmpeg
    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    pass

binaries = []
if ffmpeg_path and os.path.exists(ffmpeg_path):
    binaries.append((ffmpeg_path, '.'))

# Icons and other static assets live in repo-root ``resources/`` (not under ``sisr/``).
_datas = list(collect_data_files('sisr'))
_resources = os.path.join(_spec_dir, 'resources')
if os.path.isdir(_resources):
    _datas.append((_resources, 'resources'))

a = Analysis(
    [_main_script],
    pathex=[_spec_dir],
    binaries=binaries,
    datas=_datas,
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

_icon = os.path.join(_spec_dir, 'resources', 'icon.icns')
_bundle_kwargs = dict(
    name='SISR.app',
    bundle_identifier='com.sisr.app',
    info_plist={
        'CFBundleShortVersionString': '0.4.1',
        'CFBundleVersion': '0.4.1',
        'NSHighResolutionCapable': 'True',
        'LSBackgroundOnly': 'False',
        'NSRequiresAquaSystemAppearance': 'False',
        'NSPrincipalClass': 'NSApplication',
        'CFBundleExecutable': 'SISR',
        'CFBundlePackageType': 'APPL',
        'CFBundleSignature': '????',
    },
)
if os.path.isfile(_icon):
    _bundle_kwargs['icon'] = _icon

app = BUNDLE(coll, **_bundle_kwargs)