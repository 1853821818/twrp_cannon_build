#!/usr/bin/env python3
"""Convert remaining K&R-style definitions in TeamWin libtar to ANSI C.

TeamWin android-14's libtar still contains pre-ANSI definitions such as:

    char *
    openbsd_basename(path)
        const char *path;
    {

Clang r487747c (Android 14) promotes -Wdeprecated-non-prototype to an
error in this build (libtar uses -Wall -Werror), so compilation stops at
basename.c.  dirname.c and strmode.c use the same style and would fail
next.  Rewrite those three definitions with real prototypes; behaviour
is unchanged.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "bootable/recovery") / "libtar"

patches = {
    "basename.c": (
        "char *\nopenbsd_basename(path)\n\tconst char *path;",
        "char *openbsd_basename(const char *path)",
    ),
    "dirname.c": (
        "char *\nopenbsd_dirname(path)\n\tconst char *path;",
        "char *openbsd_dirname(const char *path)",
    ),
    "strmode.c": (
        "void\nstrmode(mode, p)\n\tregister mode_t mode;\n\tregister char *p;",
        "void strmode(mode_t mode, char *p)",
    ),
}

changed = []
for name, (old, new) in patches.items():
    p = root / name
    if not p.exists():
        print(f"LIBTAR_KNR_PATCH_FAILED: missing {p}", file=sys.stderr)
        sys.exit(1)
    s = p.read_text()
    if old in s:
        p.write_text(s.replace(old, new, 1))
        changed.append(name)
    elif new in s:
        continue
    else:
        print(f"LIBTAR_KNR_PATCH_FAILED: no legacy definition in {p}", file=sys.stderr)
        sys.exit(1)

if changed:
    print("LIBTAR_KNR_PATCHED " + ",".join(changed))
else:
    print("LIBTAR_KNR_ALREADY_PATCHED")
