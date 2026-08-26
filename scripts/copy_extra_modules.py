"""Copy extra modules (acoustid, audioread, sounddevice, soundfile) to dist"""

import os
import shutil

internal = r"dist\JM-MusicAnalyzer\_internal"

modules = ["acoustid", "sounddevice", "soundfile"]
for modname in modules:
    try:
        mod = __import__(modname)
        src = mod.__file__
        dst = os.path.join(internal, os.path.basename(src))
        shutil.copy2(src, dst)
        print(f"Copied: {src} -> {dst}")
    except Exception as e:
        print(f"Cannot copy {modname}: {e}")

packages = ["audioread"]
for pkgname in packages:
    try:
        pkg = __import__(pkgname)
        src_dir = os.path.dirname(pkg.__file__)
        dst_dir = os.path.join(internal, pkgname)
        if os.path.exists(dst_dir):
            shutil.rmtree(dst_dir)
        shutil.copytree(src_dir, dst_dir)
        print(f"Copied: {src_dir} -> {dst_dir}")
    except Exception as e:
        print(f"Cannot copy {pkgname}: {e}")
