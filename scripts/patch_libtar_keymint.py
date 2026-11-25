#!/usr/bin/env python3
"""Drop libtar's unnecessary libkeymint_support dependency.

TeamWin android-14's libtar/Android.mk lists libkeymint_support in the
TW_INCLUDE_CRYPTO_FBE block, but libtar sources never reference keymint
symbols.  On a trimmed AOSP 14 tree the runtime dependency
android.hardware.security.keymint-V1-ndk_platform.so is not built, so the
final recovery image can contain libkeymint_support.so with an unresolved
NEEDED entry and recovery fails to load.

Removing this one entry keeps the tar/crypto functionality that libtar
actually uses (vold, keymaster, gatekeeper, keystore2 AIDL) and removes the
only path that pulls the absent keymint V1 platform library.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "bootable/recovery")
p = root / "libtar/Android.mk"
if not p.exists():
    print(f"LIBTAR_KEYMINT_PATCH_FAILED: missing {p}", file=sys.stderr)
    sys.exit(1)

lines = p.read_text().splitlines(True)
kept = [line for line in lines if "libkeymint_support" not in line]
if len(kept) == len(lines):
    print("LIBTAR_KEYMINT_ALREADY_PATCHED")
else:
    p.write_text("".join(kept))
    print(f"LIBTAR_KEYMINT_PATCHED {p}: removed {len(lines)-len(kept)} line(s)")
