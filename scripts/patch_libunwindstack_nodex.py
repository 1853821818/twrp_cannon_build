#!/usr/bin/env python3
"""关闭 libunwindstack 的 DEX/ART 依赖。

TWRP recovery 不需要 Java/DEX unwind，但 libunwindstack 的默认 platform
变体会编译 DexFile.cpp 并依赖 libdexfile_support / libdexfile（ART APEX）。
精简 manifest 没有 ART，导致 70% 处的 toc 校验直接失败。

这里只改 libunwindstack 主模块，把它变成 no-dex 版本：
- 从 srcs 去掉 DexFile.cpp
- 去掉 -DDEXFILE_SUPPORT，改为 -UDEXFILE_SUPPORT
- 去掉 libdexfile_support / libdexfile
- 清掉各 target 变体里对应的 exclude 行，避免 Soong 校验不存在项
"""

import sys
from pathlib import Path

MARKER = 'cc_library {\n    name: "libunwindstack",'


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "system/unwinding/libunwindstack/Android.bp")
    text = path.read_text()

    start = text.find(MARKER)
    if start < 0:
        print(f"LIBUNWINDSTACK_BLOCK_NOT_FOUND {path}", file=sys.stderr)
        return 1

    brace = text.index("{", start)
    depth = 0
    end = -1
    for i in range(brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end < 0:
        print("LIBUNWINDSTACK_BLOCK_UNTERMINATED", file=sys.stderr)
        return 1

    old = text[start:end]

    replacements = [
        ('        "DexFile.cpp",\n', ""),
        ('    cflags: ["-DDEXFILE_SUPPORT"],\n', '    cflags: ["-UDEXFILE_SUPPORT"],\n'),
        ('    static_libs: ["libdexfile_support"],\n', ""),
        ('    runtime_libs: ["libdexfile"], // libdexfile_support dependency\n', ""),
    ]
    for needle, repl in replacements:
        if needle not in old:
            print(f"LIBUNWINDSTACK_PATTERN_MISSING {needle.strip()}", file=sys.stderr)
            return 1
        old = old.replace(needle, repl, 1)

    # target 变体里的 exclude 行也一并移除；主模块已不再包含这些源/库。
    for needle in (
        '            cflags: ["-UDEXFILE_SUPPORT"],\n',
        '            exclude_srcs: ["DexFile.cpp"],\n',
        '            exclude_static_libs: ["libdexfile_support"],\n',
        '            exclude_runtime_libs: ["libdexfile"],\n',
    ):
        old = old.replace(needle, "")

    text = text[:start] + old + text[end:]
    path.write_text(text)

    block = old
    if "DexFile.cpp" in block or "libdexfile" in block:
        print("LIBUNWINDSTACK_NODEX_INCOMPLETE", file=sys.stderr)
        return 1
    print("LIBUNWINDSTACK_NODEX_PATCHED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
