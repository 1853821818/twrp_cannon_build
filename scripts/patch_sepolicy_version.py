#!/usr/bin/env python3
"""Pin versioned sepolicy mapping targets to AOSP 14's 34.0.

TeamWin's minimal twrp-14 build/make tree does not populate
PLATFORM_SEPOLICY_VERSION or BOARD_SEPOLICY_VERS into Soong (even when
BOARD_SEPOLICY_VERS is set in BoardConfig.mk), so both
PlatformSepolicyVersion() and BoardSepolicyVers() resolve to an empty
string.  versioned_policy then invokes:

    version_policy -b ... -n  -o ...

and version_policy fails with "Unknown arguments supplied".

Replace "current" and "vendor" version markers inside
se_versioned_policy modules with the AOSP 14 platform policy version
34.0.  Do NOT touch sepolicy_vers: its version property only accepts
"platform" or "vendor" and is validated by Soong.
"""
from pathlib import Path
import re
import sys

p = Path("system/sepolicy/Android.bp")
if not p.exists():
    print(f"SEPOLICY_VERSION_PATCH_FAILED: missing {p}", file=sys.stderr)
    sys.exit(1)

s = p.read_text()

current_count = s.count('version: "current"')
s = s.replace('version: "current"', 'version: "34.0"')

vendor_pattern = re.compile(
    r'(se_versioned_policy\s*\{[^{}]*?version:\s*)"vendor"', re.S
)
vendor_count = len(vendor_pattern.findall(s))
s = vendor_pattern.sub(r'\g<1>"34.0"', s)

if current_count == 0 and vendor_count == 0:
    print("SEPOLICY_VERSION_ALREADY_SET")
    sys.exit(0)

p.write_text(s)
print("SEPOLICY_VERSION_FALLBACK_APPLIED "
      f"current={current_count} vendor={vendor_count}")
