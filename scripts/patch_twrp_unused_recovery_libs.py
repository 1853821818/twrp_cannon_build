#!/usr/bin/env python3
"""Drop crypto shared libs that are not built in this minimal twrp-14 tree.

TeamWin's Android.mk adds android.hardware.authsecret@1.0,
android.hardware.oemlock@1.0 and libandroidicu.recovery to recovery's
crypto build.  Recovery's C++ sources do not reference any of them; they
are leftovers from a full AOSP build.  This manifest prunes the
authsecret/oemlock interface directories and does not build an ICU
recovery variant, so the recovery executable link dies at 99% with
"no such file or directory" for exactly those three .so paths.
"""
from pathlib import Path
import re
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "bootable/recovery")
android_mk = root / "Android.mk"
prebuilt_mk = root / "prebuilt/Android.mk"
for p in (android_mk, prebuilt_mk):
    if not p.exists():
        print(f"TWRP_UNUSED_LIBS_PATCH_FAILED: missing {p}", file=sys.stderr)
        sys.exit(1)

changed = []

s = android_mk.read_text()

# Exact crypto shared-library block emitted by TeamWin android-14.
old_block = (
    "    LOCAL_SHARED_LIBRARIES += android.frameworks.stats@1.0 android.hardware.authsecret@1.0 \\\n"
    "\tandroid.security.authorization-ndk_platform \\\n"
    "        android.hardware.oemlock@1.0 libf2fs_sparseblock libbinder libbinder_ndk \\\n"
    "        libandroidicu.recovery \\\n"
)
new_block = (
    "    LOCAL_SHARED_LIBRARIES += android.frameworks.stats@1.0 \\\n"
    "\tandroid.security.authorization-ndk_platform \\\n"
    "        libf2fs_sparseblock libbinder libbinder_ndk \\\n"
)
if old_block in s:
    s = s.replace(old_block, new_block, 1)
    changed.append("shared-libs-block")
else:
    # Fallback for whitespace drift: remove each token, then repair any
    # dangling "\ <rest-of-line>" continuation created inside a list.
    for lib in (
        "android.hardware.authsecret@1.0",
        "android.hardware.oemlock@1.0",
        "libandroidicu.recovery",
    ):
        n_before = s.count(lib)
        if n_before:
            s = re.sub(rf"\s*{re.escape(lib)}\b", "", s)
            changed.append(f"{lib}:{n_before}")
    s = re.sub(r"\\\s+(?=[^\n]*\n)", "\\\\\n        ", s)

# TWRP_REQUIRED_MODULES still asks the build to provide an ICU recovery
# library that does not exist in this tree.
n_req = len(re.findall(r"^\s*libandroidicu\.recovery\s*\\\s*\n", s, re.M))
if n_req:
    s = re.sub(r"^\s*libandroidicu\.recovery\s*\\\s*\n", "", s, flags=re.M)
    changed.append(f"required-libandroidicu:{n_req}")
android_mk.write_text(s)

p = prebuilt_mk.read_text()
n_pre = 0
for lib in ("android.hardware.authsecret@1.0", "android.hardware.oemlock@1.0"):
    line_re = re.compile(
        rf"^\s*RECOVERY_LIBRARY_SOURCE_FILES \+= \$\(TARGET_OUT_SHARED_LIBRARIES\)/{re.escape(lib)}\.so\s*\n",
        re.M,
    )
    n = len(line_re.findall(p))
    if n:
        p = line_re.sub("", p)
        n_pre += n
if n_pre:
    prebuilt_mk.write_text(p)
    changed.append(f"prebuilt-copy:{n_pre}")

if not changed:
    print("TWRP_UNUSED_LIBS_ALREADY_PATCHED")
else:
    print("TWRP_UNUSED_LIBS_PATCHED " + ",".join(changed))
