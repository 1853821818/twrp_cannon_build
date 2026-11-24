#!/usr/bin/env python3
"""Complete TWRP recovery root after the minimal-manifest Make build.

TeamWin's relink_libraries/relink_binaries phony packages are silently skipped
under ALLOW_MISSING_DEPENDENCIES because many optional source modules do not
exist in the reduced manifest.  The resulting recovery.img contains the
recovery binary but no init, linker or shared libraries, so it cannot boot.

This script:
  1. copies init / linker64 / core binaries from the product out tree;
  2. resolves the DT_NEEDED closure of every ELF already in recovery/root and
     copies the shared libraries from out/target/product/*/{system,vendor}/lib64;
  3. installs TeamWin's init.rc and init.recovery.*.rc files expected by init.
It is intentionally read-only with respect to the source tree and idempotent.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

NEEDED_RE = re.compile(r"\(NEEDED\)\s+Shared library: \[([^\]]+)\]")
SKIP_LIBS = {"libc.so", "libm.so", "libdl.so", "libstdc++.so", "libc++.so", "libc++abi.so"}

CORE_BINS = [
    "init", "ueventd", "adbd", "charger", "sh", "toybox", "toolbox",
    "mke2fs", "e2fsck", "fsck.f2fs", "make_f2fs", "sload_f2fs",
    "simg2img", "recovery", "twrp", "resetprop",
    "android.hardware.keymaster@4.1-service.beanpod",
    "android.hardware.gatekeeper@1.0-service",
]


def elf_needed(path: Path) -> list[str]:
    try:
        out = subprocess.check_output(["readelf", "-d", str(path)], stderr=subprocess.DEVNULL, text=True)
    except Exception:
        return []
    return NEEDED_RE.findall(out)


def is_elf(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            return f.read(4) == b"\x7fELF"
    except Exception:
        return False


class LibIndex:
    def __init__(self, roots: list[Path]):
        self.by_name: dict[str, list[Path]] = {}
        for root in roots:
            if not root.is_dir():
                continue
            for dirpath, _, filenames in os.walk(root):
                for fn in filenames:
                    p = Path(dirpath) / fn
                    if p.is_file() and not p.is_symlink():
                        self.by_name.setdefault(fn, []).append(p)

    def find(self, name: str) -> Path | None:
        cands = self.by_name.get(name)
        if not cands:
            return None
        # Prefer non-bootstrap, then shorter path.
        cands = sorted(cands, key=lambda p: ("bootstrap" in str(p), len(str(p))))
        return cands[0]


def copy_elf(src: Path, dst: Path, index: LibIndex, copied: set[str], missing: list[str]) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() or dst.is_symlink():
        dst.unlink()
    shutil.copy2(src, dst)
    copied.add(dst.name)
    for need in elf_needed(dst):
        if need in copied:
            continue
        lib = index.find(need)
        if lib is None:
            missing.append(f"{dst.name}:{need}")
            continue
        target = dst.parent / need
        copy_elf(lib, target, index, copied, missing)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True, help="out/target/product/cannon")
    ap.add_argument("--bindir", required=True, help="directory holding system/bin binaries")
    ap.add_argument("--init", default="", help="optional explicit init binary")
    ap.add_argument("--search", action="append", default=[], help="extra library search directory")
    args = ap.parse_args()

    root = Path(args.root)
    out = Path(args.out)
    bindir = Path(args.bindir)
    if not root.is_dir():
        print(f"RECOVERY_ROOT_MISSING {root}", file=sys.stderr)
        return 1

    search = [
        out / "system/lib64", out / "system/lib64/hw", out / "system/lib64/bootstrap",
        out / "vendor/lib64", out / "vendor/lib64/hw", out / "system_ext/lib64",
        out / "recovery/root/system/lib64",
        Path("out/target/product/generic_arm64/system/lib64"),
        Path("out/target/product/generic_arm64/system/lib64/bootstrap"),
    ]
    search += [Path(p) for p in args.search if p]
    index = LibIndex(search)

    # 1. linker64 -----------------------------------------------------------------
    linker = None
    candidates = list(Path("out/target/product").glob("*/system/bin/linker64"))
    candidates += [bindir / "linker64", out / "system/bin/linker64"]
    for c in candidates:
        if c.is_file():
            linker = c
            break
    if linker is None:
        print("RECOVERY_LINKER64_MISSING", file=sys.stderr)
        return 1
    dst_linker = root / "system/bin/linker64"
    dst_linker.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(linker, dst_linker)
    print(f"RECOVERY_LINKER64 {linker} -> {dst_linker}")

    # 2. init ---------------------------------------------------------------------
    init_src = Path(args.init) if args.init else None
    if not init_src or not init_src.is_file():
        for c in [out / "system/bin/init", bindir / "init"] + list(Path("out/target/product").glob("*/system/bin/init")):
            if c.is_file():
                init_src = c
                break
    if not init_src or not init_src.is_file():
        print("RECOVERY_INIT_MISSING", file=sys.stderr)
        return 1
    dst_init = root / "system/bin/init"
    shutil.copy2(init_src, dst_init)
    print(f"RECOVERY_INIT {init_src} -> {dst_init}")

    # 3. core binaries ------------------------------------------------------------
    copied_bins = []
    for name in CORE_BINS:
        src = bindir / name
        if src.is_symlink():
            real = src.resolve()
            if not real.is_file():
                continue
            src = real
        if src.is_file():
            dst = root / "system/bin" / name
            shutil.copy2(src, dst)
            copied_bins.append(name)
    print("RECOVERY_CORE_BINS " + ",".join(copied_bins))

    # 4. init.rc and recovery rc files -------------------------------------------
    init_rc = Path("bootable/recovery/etc/init.rc")
    if init_rc.is_file():
        dst = root / "system/etc/init/hw/init.rc"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(init_rc, dst)
        print(f"RECOVERY_INIT_RC {init_rc} -> {dst}")
    else:
        print("RECOVERY_INIT_RC_SOURCE_MISSING", file=sys.stderr)
        return 1

    rc_dir = Path("bootable/recovery/etc")
    if rc_dir.is_dir():
        for src in rc_dir.glob("init.recovery.*.rc"):
            name = src.name
            if name == "init.recovery.service22.rc":
                name = "init.recovery.service.rc"
            elif name.startswith("init.recovery.hlthchrg"):
                name = "init.recovery.hlthchrg.rc"
            dst = root / name
            shutil.copy2(src, dst)
            print(f"RECOVERY_RC {src.name} -> {dst.name}")

    # ueventd.rc
    ueventd_rc = Path("system/core/rootdir/ueventd.rc")
    if ueventd_rc.is_file():
        dst = root / "system/etc/ueventd.rc"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ueventd_rc, dst)

    # ld.config.txt (A12 fallback content is enough for recovery namespace)
    ldconfig = Path("system/core/rootdir/etc/ld.config.txt")
    if not ldconfig.is_file():
        ldconfig = Path("scripts/recovery_root_compat/ld.config.txt")
    if ldconfig.is_file():
        dst = root / "system/etc/ld.config.txt"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ldconfig, dst)

    # ueventd symlink
    ueventd = root / "system/bin/ueventd"
    if not ueventd.exists():
        try:
            ueventd.symlink_to("init")
        except OSError:
            pass

    # 5. DT_NEEDED closure over every ELF in the root -----------------------------
    missing: list[str] = []
    copied: set[str] = set()
    # seed with current root libs so we don't copy them again
    for libdir in [root / "system/lib64", root / "vendor/lib64", root / "system/lib64/hw", root / "vendor/lib64/hw"]:
        if libdir.is_dir():
            for p in libdir.iterdir():
                if p.is_file():
                    copied.add(p.name)
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            p = Path(dirpath) / fn
            if p.is_file() and not p.is_symlink() and is_elf(p):
                for need in elf_needed(p):
                    if need in copied:
                        continue
                    lib = index.find(need)
                    if lib is None:
                        missing.append(f"{p.relative_to(root)}:{need}")
                        continue
                    # vendor libs go to vendor/lib64, others to system/lib64
                    dst_dir = root / ("vendor/lib64" if "/vendor/" in str(lib) or str(lib).startswith("vendor/") else "system/lib64")
                    copy_elf(lib, dst_dir / need, index, copied, missing)

    print(f"RECOVERY_LIBS_COPIED {len(copied)}")
    if missing:
        print("RECOVERY_LIBS_MISSING " + ",".join(sorted(set(missing))))
        return 1

    # 6. sanity checks -------------------------------------------------------------
    required = [
        root / "system/bin/init",
        root / "system/bin/linker64",
        root / "system/bin/recovery",
        root / "system/lib64/libc.so",
        root / "system/lib64/libbase.so",
        root / "system/etc/init/hw/init.rc",
    ]
    for p in required:
        if not p.exists():
            print(f"RECOVERY_ROOT_CHECK_FAILED {p}", file=sys.stderr)
            return 1
    print("RECOVERY_ROOT_FIXED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
