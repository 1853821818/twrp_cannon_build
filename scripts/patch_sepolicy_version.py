#!/usr/bin/env python3
"""Fill the empty platform sepolicy version used by se_versioned_policy.

The TWRP minimal manifest's build/make tree does not populate
PLATFORM_SEPOLICY_VERSION (TeamWin's build/make lacks the AOSP 14
sepolicy_major_vers/sepolicy_minor_vers calculation), so Soong passes
an empty string after -n to version_policy and the build stops at
plat_mapping_file.  Pin the current-version mapping modules to AOSP 14's
platform policy version (34.0) explicitly.
"""
from pathlib import Path
import sys

p = Path("system/sepolicy/Android.bp")
if not p.exists():
    print(f"SEPOLICY_VERSION_PATCH_FAILED: missing {p}", file=sys.stderr)
    sys.exit(1)

s = p.read_text()
old = 'version: "current"'
new = 'version: "34.0"'
count = s.count(old)
if count == 0:
    print("SEPOLICY_VERSION_ALREADY_SET")
    sys.exit(0)

s = s.replace(old, new)
p.write_text(s)
print(f"SEPOLICY_VERSION_FALLBACK_APPLIED {count}")
