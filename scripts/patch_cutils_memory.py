#!/usr/bin/env python3
"""Restore android_memset16/32 for TWRP libpixelflinger.

AOSP 14 system/core removed the libcutils memset helpers, but TeamWin's
libpixelflinger still calls them.  Provide header-only C implementations so
no libcutils source/Android.bp changes are needed.
"""

from pathlib import Path

HEADER = Path("system/core/libcutils/include/cutils/memory.h")
MARKER = "TWRP_CUTILS_MEMSET_COMPAT"

COMPAT = """
/* TWRP_CUTILS_MEMSET_COMPAT: AOSP 14 removed these libcutils helpers.
 * size is in bytes and must be a multiple of 2/4 respectively. */
static inline void android_memset16(uint16_t* dst, uint16_t value, size_t size) {
    while (size >= 2) {
        *dst++ = value;
        size -= 2;
    }
}

static inline void android_memset32(uint32_t* dst, uint32_t value, size_t size) {
    while (size >= 4) {
        *dst++ = value;
        size -= 4;
    }
}
"""

text = HEADER.read_text()
if MARKER not in text:
    anchor = '#ifdef __cplusplus\nextern "C" {\n#endif\n'
    if anchor not in text:
        raise SystemExit("cutils/memory.h anchor not found")
    text = text.replace(anchor, anchor + COMPAT, 1)
    HEADER.write_text(text)

if "android_memset16" not in HEADER.read_text():
    raise SystemExit("android_memset16 patch failed")
print("CUTILS_MEMSET_COMPAT_OK")
