#!/usr/bin/env python3
"""Fallback: drop recovery's dependency on recovery_sepolicy.

TeamWin's minimal twrp-14 manifest does not provide the Soong
precompiled_sepolicy build rule. Recovery can be built without copying
sepolicy-related files into the recovery ramdisk; TWRP's init does not
require them for basic booting. This script only runs when the normal
build still reports 'precompiled_sepolicy missing and no known rule'.
"""
from pathlib import Path
import re

p = Path("build/make/core/Makefile")
s = p.read_text()
s, n = re.subn(
    r"recovery_sepolicy := \\\n(?:[ \t]+.*\n)+",
    "recovery_sepolicy :=\n",
    s,
    count=1,
)
p.write_text(s)
print("patched recovery_sepolicy blocks:", n)
