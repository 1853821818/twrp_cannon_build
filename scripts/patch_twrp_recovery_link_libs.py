#!/usr/bin/env python3
"""Add transitive static link deps omitted by TeamWin's Make-based recovery link.

Soong builds each static library with its own dependencies, but TeamWin's
legacy Android.mk final link only receives the static libraries listed in
LOCAL_STATIC_LIBRARIES.  As a result the recovery executable reaches 99%
with unresolved symbols from libvold/libsnapshot_nobinder/librecovery_utils/libtwrpinstall.
Add the AOSP-14 provider libraries explicitly, matching the source-of-truth
Android.bp definitions.
"""
from pathlib import Path
import sys

p = Path(sys.argv[1] if len(sys.argv) > 1 else "bootable/recovery/Android.mk")
if not p.exists():
    print(f"TWRP_RECOVERY_LINKS_PATCH_FAILED: missing {p}", file=sys.stderr)
    sys.exit(1)

text = p.read_text()
changed = []

static_old = (
    "LOCAL_STATIC_LIBRARIES += libavb libtwrpinstall libminadbd_services "
    "libinit libsnapshot_nobinder update_metadata-protos librecovery_utils "
    "libhealthhalutils"
)
static_new = static_old + (
    " libotautil libscrypt_static libsnapshot_cow libbrotli liblz4 "
    "libhealthshim android.hardware.health-translate-ndk"
)
if static_old in text and "libscrypt_static" not in text:
    text = text.replace(static_old, static_new, 1)
    changed.append("static-deps")
elif "libscrypt_static" not in text:
    # Fallback: append to the first recovery static list.
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("LOCAL_STATIC_LIBRARIES += libavb"):
            lines[i] = line + (
                " libotautil libscrypt_static libsnapshot_cow libbrotli liblz4 "
                "libhealthshim android.hardware.health-translate-ndk"
            )
            text = "\n".join(lines) + "\n"
            changed.append("static-deps-fallback")
            break

shared_old = (
    "LOCAL_SHARED_LIBRARIES += libfs_mgr libhardware android.hardware.boot@1.0 "
    "android.hardware.boot@1.1 android.hardware.boot@1.2 libprotobuf-cpp-lite "
    "liblp libutils libhidlbase android.hardware.health@2.0"
)
shared_new = shared_old + (
    " libboot_control_client android.hardware.health-V2-ndk "
    "android.hardware.health-V3-ndk android.hardware.health@1.0"
)
if shared_old in text and "libboot_control_client" not in text:
    text = text.replace(shared_old, shared_new, 1)
    changed.append("shared-deps")
elif "libboot_control_client" not in text:
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("LOCAL_SHARED_LIBRARIES += libfs_mgr"):
            lines[i] = line + (
                " libboot_control_client android.hardware.health-V2-ndk "
                "android.hardware.health-V3-ndk android.hardware.health@1.0"
            )
            text = "\n".join(lines) + "\n"
            changed.append("shared-deps-fallback")
            break

if changed:
    p.write_text(text)
    print("TWRP_RECOVERY_LINKS_PATCHED " + ",".join(changed))
else:
    print("TWRP_RECOVERY_LINKS_ALREADY_PATCHED")
