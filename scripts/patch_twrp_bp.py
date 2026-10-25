#!/usr/bin/env python3
"""Patch vendor/twrp/build/soong/Android.bp to remove TWRP kernel vars that
TWRP's android-14 soong doesn't register (causes 'unknown variable' errors).
Keep soong-builtin vars like $(genDir).
"""
import os, re, sys

p = "vendor/twrp/build/soong/Android.bp"
try:
    s = open(p).read()
except Exception as e:
    print("NO_ANDROID_BP:", e)
    sys.exit(1)

for v in ["PATH_OVERRIDE_SOONG", "KERNEL_MAKE_CMD", "KERNEL_MAKE_FLAGS",
          "TARGET_KERNEL_SOURCE", "KERNEL_BUILD_OUT_PREFIX", "KERNEL_ARCH",
          "KERNEL_CROSS_COMPILE", "TARGET_KERNEL_HEADERS_SOURCE"]:
    s = s.replace("$(" + v + ")", "")

open(p, "w").write(s)
left = [x for x in re.findall(r"\$\([A-Z_]+\)", s) if x not in ("$(genDir)",)]
print("REMAINING_TWRP_VARS:", left)
print("PATH_OVERRIDE left:", s.count("PATH_OVERRIDE"))
if left:
    sys.exit(0)  # report but don't fail build
