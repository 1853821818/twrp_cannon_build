#!/usr/bin/env python3
"""Remove ART/DEX dependencies from libdebuggerd.

The bionic linker links libdebuggerd_handler_fallback -> libdebuggerd.  In the
reduced TWRP manifest ART is absent, so the platform libdebuggerd variant fails
with "missing dependencies: libdexfile_support, libdexfile".  Recovery does not
need tombstone DEX symbolization, and libunwindstack is already patched to
no-dex, so drop those two dependencies from libdebuggerd itself.
"""
from __future__ import annotations

import sys
from pathlib import Path

MARKER = 'cc_library_static {\n    name: "libdebuggerd",'


def block_end(text: str, start: int) -> int:
    brace = text.index("{", start)
    depth = 0
    for i in range(brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i + 1
    return -1


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "system/core/debuggerd/Android.bp")
    text = path.read_text()
    start = text.find(MARKER)
    if start < 0:
        print(f"LIBDEBUGGERD_BLOCK_NOT_FOUND {path}", file=sys.stderr)
        return 1
    end = block_end(text, start)
    if end < 0:
        print("LIBDEBUGGERD_BLOCK_UNTERMINATED", file=sys.stderr)
        return 1
    block = text[start:end]

    needles = [
        '        "libdexfile_support",  // libunwindstack dependency\n',
        '    runtime_libs: [\n        "libdexfile",           // libdexfile_support dependency\n    ],\n',
        '''    target: {
        recovery: {
            exclude_static_libs: [
                "libdexfile_support",
            ],
            exclude_runtime_libs: [
                "libdexfile",
            ],
        },
        vendor_ramdisk: {
            exclude_static_libs: [
                "libdexfile_support",
            ],
            exclude_runtime_libs: [
                "libdexfile",
            ],
        },
    },
''',
    ]
    for needle in needles:
        if needle not in block:
            print(f"LIBDEBUGGERD_PATTERN_MISSING {needle.splitlines()[0]}", file=sys.stderr)
            return 1
        block = block.replace(needle, "", 1)

    text = text[:start] + block + text[end:]
    path.write_text(text)
    if "libdexfile" in block:
        print("LIBDEBUGGERD_NODEX_INCOMPLETE", file=sys.stderr)
        return 1
    print("LIBDEBUGGERD_NODEX_PATCHED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
