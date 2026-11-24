#!/usr/bin/env python3
"""Point TeamWin recovery/libtar at AOSP 14's actual security AIDL modules.

TeamWin's android-14 Makefiles still use Android 11-era names such as
android.security.apc-ndk_platform.  AOSP 14's aidl_interface definitions
live in system/security/keystore2/aidl and generate unversioned names for
unstable interfaces plus V3 for keystore2:

    android.security.apc-ndk
    android.security.authorization-ndk
    android.security.maintenance-ndk
    android.system.keystore2-V3-ndk

With the old names, libtar links against non-existent .so paths and fails
at 96%.  Rewrite those Makefile references; also fix the prebuilt list so
the recovery image relink step copies the libraries actually built.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "bootable/recovery")

replacements = {
    "android.security.apc-ndk_platform": "android.security.apc-ndk",
    "android.system.keystore2-V1-ndk_platform": "android.system.keystore2-V3-ndk",
    "android.security.authorization-ndk_platform": "android.security.authorization-ndk",
    "android.security.maintenance-ndk_platform": "android.security.maintenance-ndk",
}

files = ["Android.mk", "libtar/Android.mk", "prebuilt/Android.mk"]
changed_files = []
total = 0
for rel in files:
    p = root / rel
    if not p.exists():
        print(f"TWRP_SECURITY_AIDL_PATCH_FAILED: missing {p}", file=sys.stderr)
        sys.exit(1)
    s = p.read_text()
    n = 0
    for old, new in replacements.items():
        count = s.count(old)
        if count:
            s = s.replace(old, new)
            n += count
    tp = p.with_suffix(p.suffix + ".tmp")
    tp.write_text(s)
    tp.replace(p)
    total += n
    if n:
        changed_files.append(f"{rel}:{n}")

if total == 0:
    print("TWRP_SECURITY_AIDL_ALREADY_PATCHED")
else:
    print("TWRP_SECURITY_AIDL_PATCHED " + ",".join(changed_files))
