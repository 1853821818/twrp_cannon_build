#!/usr/bin/env python3
"""Pin every versioned sepolicy mapping target to AOSP 14's 34.0.

TeamWin's minimal twrp-14 build/make tree does not populate
PLATFORM_SEPOLICY_VERSION or BOARD_SEPOLICY_VERS into Soong (even when
BOARD_SEPOLICY_VERS is set in BoardConfig.mk), so both
PlatformSepolicyVersion() and BoardSepolicyVers() resolve to an empty
string.  versioned_policy then invokes:

    version_policy -b ... -n  -o ...

and version_policy fails with "Unknown arguments supplied".

Replace all "current" and "vendor" version markers in the top-level
system/sepolicy/Android.bp with the AOSP 14 platform policy version
34.0, which is the version this recovery build targets.  microdroid
sepolicy is not built for TWRP and is left untouched.
"""
from pathlib import Path
import sys

p = Path("system/sepolicy/Android.bp")
if not p.exists():
    print(f"SEPOLICY_VERSION_PATCH_FAILED: missing {p}", file=sys.stderr)
    sys.exit(1)

s = p.read_text()
counts = {}
for marker, target in (('"current"', '"34.0"'), ('"vendor"', '"34.0"')):
    old = f'version: {marker}'
    count = s.count(old)
    counts[marker.strip('"')] = count
    s = s.replace(old, f'version: {target}')

if not any(counts.values()):
    print("SEPOLICY_VERSION_ALREADY_SET")
    sys.exit(0)

p.write_text(s)
print("SEPOLICY_VERSION_FALLBACK_APPLIED "
      f"current={counts['current']} vendor={counts['vendor']}")
