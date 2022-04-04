# -*- mode: python -*-
import PyInstaller

block_cipher = None


a = Analysis(
    ["mountain_king.py", "mountain_king.spec"],
    pathex=["/home/pudding/Projects/mountain_king"],
    binaries=None,
    datas=None,
    hiddenimports=PyInstaller.utils.hooks.collect_submodules("pkg_resources"),
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
image_tree = Tree("/home/pudding/Projects/mountain_king/resource", prefix="resource")
shader_tree = Tree("/home/pudding/Projects/mountain_king/drawing", prefix="drawing")

a.datas += image_tree
a.datas += shader_tree

exe = EXE(
    pyz,
    a.scripts,
    # a.binaries,
    # a.zipfiles,
    # a.datas,
    name="mountain_king",
    debug=False,
    strip=False,
    upx=True,
    console=True,
    exclude_binaries=1,
)
dist = COLLECT(exe, a.binaries, a.zipfiles, a.datas, name="mountain_king")
