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


def lib_dest(root: Path, lib: Path) -> Path:
    if "vendor" in lib.parts:
        return root / "vendor/lib64"
    return root / "system/lib64"


def copy_elf(root: Path, src: Path, dst: Path, index: LibIndex, copied: set[str], missing: list[str]) -> None:
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
        copy_elf(root, lib, lib_dest(root, lib) / need, index, copied, missing)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True, help="out/target/product/cannon")
    ap.add_argument("--bindir", required=True, help="directory holding system/bin binaries")
    ap.add_argument("--init", default="", help="optional explicit init binary")
    ap.add_argument("--search", action="append", default=[], help="extra library search directory")
    ap.add_argument("--fallback-lib", action="append", default=[], help="extra fallback library directory")
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
    search += [Path(p) for p in args.fallback_lib if p]
    index = LibIndex(search)

    # 1. linker64 -----------------------------------------------------------------
    def resolve_linker(c: Path) -> Path | None:
        if c.is_file() and not c.is_symlink():
            return c
        if c.is_symlink():
            real = c.resolve()
            if real.is_file():
                return real
            # Soong installs system/bin/linker64 as a symlink into the runtime APEX:
            # /apex/com.android.runtime/bin/linker64. Resolve that inside the product out tree.
            target = os.readlink(c)
            if target.startswith("/apex/"):
                rel = target.lstrip("/")
                for prod in Path("out/target/product").glob("*"):
                    for base in (prod / "system", prod, prod / "recovery/root"):
                        candidate = base / rel
                        if candidate.is_file():
                            return candidate
        return None

    linker = None
    candidates = list(Path("out/target/product").glob("*/system/bin/linker64"))
    # Android 14 installs the real bootstrap linker under system/bin/bootstrap;
    # system/bin/linker64 is only an absolute symlink into /apex/com.android.runtime.
    candidates += list(Path("out/target/product").glob("*/system/bin/bootstrap/linker64"))
    candidates += list(Path("out/target/product").glob("*/system/apex/com.android.runtime/bin/linker64"))
    candidates += list(Path("out/target/product").glob("*/recovery/root/system/bin/linker64"))
    soong_linker_root = Path("out/soong/.intermediates/bionic/linker")
    if soong_linker_root.is_dir():
        candidates += list(soong_linker_root.rglob("linker64"))
    candidates += [bindir / "bootstrap/linker64", bindir / "linker64", out / "system/bin/linker64"]
    for c in candidates:
        linker = resolve_linker(c)
        if linker is not None:
            break
    if linker is None:
        print("RECOVERY_LINKER64_MISSING", file=sys.stderr)
        return 1
    # init and recovery may use either PT_INTERP: /system/bin/bootstrap/linker64
    # (bootstrap executables) or /system/bin/linker64. Install the same real ELF at both.
    for rel in ("system/bin/linker64", "system/bin/bootstrap/linker64"):
        dst_linker = root / rel
        dst_linker.parent.mkdir(parents=True, exist_ok=True)
        if dst_linker.is_symlink() or dst_linker.exists():
            dst_linker.unlink()
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
    # The product out tree may install system binaries under generic_arm64 rather
    # than cannon. Search all product dirs instead of relying on --bindir.
    bin_dirs = [bindir, out / "system/bin", Path("out/target/product/generic_arm64/system/bin")]
    bin_dirs += [p / "system/bin" for p in Path("out/target/product").glob("*")]
    for name in CORE_BINS:
        src = None
        for d in bin_dirs:
            c = d / name
            if c.is_symlink():
                real = c.resolve()
                if real.is_file():
                    src = real
                    break
            if c.is_file():
                src = c
                break
        if src is None:
            continue
        dst = root / "system/bin" / name
        if dst.exists() and src.samefile(dst):
            copied_bins.append(name)
            continue
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

    # 5. DT_NEEDED closure over the binaries needed by recovery/decrypt --------
    # Important: an existing root library must also be traversed.  Presence in
    # recovery/root does not mean its own NEEDED list is satisfied; e.g. libtar
    # -> libkeymint_support -> keymint-V1-ndk_platform used to slip through.
    missing: list[str] = []
    copied: set[str] = set()
    for libdir in [root / "system/lib64", root / "vendor/lib64", root / "system/lib64/hw", root / "vendor/lib64/hw"]:
        if libdir.is_dir():
            for p in libdir.iterdir():
                if p.is_file():
                    copied.add(p.name)

    def root_lib(name: str) -> Path | None:
        for d in (root / "system/lib64", root / "vendor/lib64",
                  root / "system/lib64/hw", root / "vendor/lib64/hw",
                  root / "system_ext/lib64"):
            p = d / name
            if p.is_file() and not p.is_symlink():
                return p
        return None

    visited: set[str] = set()

    def ensure_deps(elf: Path, label: str) -> None:
        if label in visited:
            return
        visited.add(label)
        for need in elf_needed(elf):
            if need in visited:
                continue
            existing = root_lib(need)
            if existing is not None:
                ensure_deps(existing, need)
                continue
            lib = index.find(need)
            if lib is None:
                missing.append(f"{label}:{need}")
                visited.add(need)
                continue
            dst = lib_dest(root, lib) / need
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists() or dst.is_symlink():
                dst.unlink()
            shutil.copy2(lib, dst)
            copied.add(need)
            ensure_deps(dst, need)

    # Only resolve the closure of binaries genuinely needed by recovery/decrypt.
    # The device-tree recovery/root also ships optional vendor HALs and THH TA
    # blobs whose old proprietary dependencies are absent; failing on those
    # would reject an otherwise bootable recovery.
    seeds = [
        root / "system/bin/init",
        root / "system/bin/linker64",
        root / "system/bin/recovery",
        root / "system/bin/android.hardware.keymaster@4.1-service.beanpod",
        root / "system/bin/android.hardware.gatekeeper@1.0-service",
        root / "system/bin/vendor.mediatek.hardware.keymaster_attestation@1.1-service",
        root / "vendor/bin/teei_daemon",
    ]
    seeds += [root / "system/bin" / name for name in copied_bins]
    for p in seeds:
        if not p.is_file() or p.is_symlink() or not is_elf(p):
            continue
        ensure_deps(p, p.name)

    print(f"RECOVERY_LIBS_COPIED {len(copied)}")
    if missing:
        print("RECOVERY_LIBS_MISSING " + ",".join(sorted(set(missing))))
        return 1

    # 6. sanity checks -------------------------------------------------------------
    required = [
        root / "system/bin/init",
        root / "system/bin/linker64",
        root / "system/bin/bootstrap/linker64",
        root / "system/bin/recovery",
        root / "system/bin/android.hardware.keymaster@4.1-service.beanpod",
        root / "system/bin/android.hardware.gatekeeper@1.0-service",
        root / "vendor/bin/teei_daemon",
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
