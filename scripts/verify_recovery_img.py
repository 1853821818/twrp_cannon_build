#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify that recovery.img really contains a bootable TWRP recovery root.

This guards against the "CI green but ramdisk stale" failure: the Makefile can
report a successful recoveryimage while reusing an old ramdisk-recovery.img.
"""
import gzip
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

CLOSURE_SEEDS = [
    "system/bin/init",
    "system/bin/recovery",
    "system/bin/twrp",
    "system/bin/android.hardware.keymaster@4.1-service.beanpod",
    "system/bin/android.hardware.gatekeeper@1.0-service",
    "system/bin/hwservicemanager",
    "system/bin/servicemanager",
    "vendor/bin/teei_daemon",
]

REQUIRED = [
    "system/bin/init",
    "system/bin/linker64",
    "system/bin/bootstrap/linker64",
    "system/bin/recovery",
    "system/bin/twrp",
    "system/lib64/libc.so",
    "system/lib64/libbase.so",
    "system/etc/init/hw/init.rc",
    "system/etc/init/hwservicemanager.rc",
    "system/etc/init/servicemanager.rc",
    "init.recovery.service.rc",
    "system/bin/android.hardware.keymaster@4.1-service.beanpod",
    "system/bin/android.hardware.gatekeeper@1.0-service",
    "system/bin/hwservicemanager",
    "system/bin/servicemanager",
    "vendor/bin/teei_daemon",
]


def align(n: int, page: int) -> int:
    return (n + page - 1) // page * page


def parse_cpio(data: bytes):
    entries = {}
    off = 0
    while off + 110 <= len(data):
        hdr = data[off:off + 110]
        if hdr[:6] not in (b"070701", b"070702"):
            nxt = data.find(b"070701", off)
            nxt2 = data.find(b"070702", off)
            cands = [x for x in (nxt, nxt2) if x >= 0]
            if not cands:
                break
            off = min(cands)
            continue
        f = [int(hdr[6 + i * 8:6 + (i + 1) * 8], 16) for i in range(13)]
        mode, filesize, namesize = f[1], f[6], f[11]
        name = data[off + 110:off + 110 + namesize - 1].decode("utf-8", "replace")
        off = align(off + 110 + namesize, 4)
        filepos = off
        off = align(off + filesize, 4)
        if name == "TRAILER!!!":
            break
        if name.startswith("./"):
            name = name[2:]
        entries[name] = (mode, filesize, data[filepos:filepos + filesize])
    return entries


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: verify_recovery_img.py <recovery.img>", file=sys.stderr)
        return 2
    img = Path(sys.argv[1])
    if not img.is_file():
        print(f"IMAGE_MISSING {img}", file=sys.stderr)
        return 1
    data = img.read_bytes()
    if len(data) < 4096 or data[:8] != b"ANDROID!":
        print("BAD_BOOT_MAGIC", file=sys.stderr)
        return 1
    kernel_size = struct.unpack_from("<I", data, 8)[0]
    ramdisk_size = struct.unpack_from("<I", data, 16)[0]
    page_size = struct.unpack_from("<I", data, 36)[0]
    header_version = struct.unpack_from("<I", data, 40)[0]
    if page_size not in (2048, 4096, 8192):
        print(f"BAD_PAGE_SIZE {page_size}", file=sys.stderr)
        return 1
    ramdisk_off = align(align(page_size + kernel_size, page_size), page_size) if header_version >= 1 else align(page_size + kernel_size, page_size)
    # v1/v2: ramdisk starts after kernel, page-aligned; same formula here.
    ramdisk = data[ramdisk_off:ramdisk_off + ramdisk_size]
    if len(ramdisk) != ramdisk_size:
        print(f"RAMDISK_TRUNCATED {len(ramdisk)}/{ramdisk_size}", file=sys.stderr)
        return 1
    try:
        cpio = gzip.decompress(ramdisk)
    except Exception as e:
        print(f"RAMDISK_GZIP_FAILED {e}", file=sys.stderr)
        return 1
    entries = parse_cpio(cpio)
    print(f"IMG_SIZE {len(data)} HEADER_V{header_version} PAGE {page_size} RAMDISK {ramdisk_size} ENTRIES {len(entries)}")

    missing = []
    for name in REQUIRED:
        if name not in entries:
            missing.append(name)
            print(f"MISSING {name}")
        else:
            mode, size, _ = entries[name]
            print(f"OK {name} size={size} mode={oct(mode & 0o7777)}")
    if "system/bin/init" in entries and entries["system/bin/init"][1] < 100000:
        missing.append("system/bin/init:too_small")

    fstab = entries.get("system/etc/recovery.fstab")
    if not fstab:
        print("MISSING system/etc/recovery.fstab")
        missing.append("system/etc/recovery.fstab")
    else:
        text = fstab[2].decode("utf-8", "replace")
        fstab_ok = True
        for token in ("fileencryption", "keydirectory"):
            if token not in text:
                print(f"FSTAB_MISSING {token}")
                missing.append(f"fstab:{token}")
                fstab_ok = False
        if fstab_ok:
            print("FSTAB_OK fileencryption,keydirectory")

    rc = entries.get("init.recovery.mt6853.rc")
    if not rc:
        print("MISSING init.recovery.mt6853.rc")
        missing.append("init.recovery.mt6853.rc")
    else:
        text = rc[2].decode("utf-8", "replace")
        rc_ok = True
        for token in ("keymaster-4-1-beanpod", "gatekeeper-1-0"):
            if token not in text:
                print(f"RC_MISSING {token}")
                missing.append(f"rc:{token}")
                rc_ok = False
        if rc_ok:
            print("KEYMASTER_RC_OK keymaster-4-1-beanpod,gatekeeper-1-0")

    svc_rc = entries.get("init.recovery.service.rc")
    if not svc_rc:
        print("MISSING init.recovery.service.rc")
        missing.append("init.recovery.service.rc")
    else:
        text = svc_rc[2].decode("utf-8", "replace")
        svc_ok = True
        for token in ("hwservicemanager.rc", "servicemanager.rc"):
            if token not in text:
                print(f"SERVICE_MANAGER_RC_MISSING {token}")
                missing.append(f"service-manager-rc:{token}")
                svc_ok = False
        if svc_ok:
            print("SERVICE_MANAGER_RC_OK hwservicemanager,servicemanager")

    if missing:
        print("RECOVERY_IMAGE_VERIFY_FAILED " + ",".join(missing), file=sys.stderr)
        return 1

    # Verify the DT_NEEDED closure of the binaries that must load for boot and
    # decryption.  Presence-only checks miss the case where an existing root
    # library (e.g. libtar.so -> libkeymint_support.so) has a NEEDED entry that
    # was never copied into the image; recovery would fail at dlopen time.
    lib_index = {}
    for name in entries:
        parts = name.split("/")
        if len(parts) == 3 and parts[0] in ("system", "vendor", "system_ext") and parts[1] == "lib64":
            lib_index.setdefault(parts[2], name)

    def elf_needed(name: str, tmp: Path) -> list[str]:
        content = entries[name][2]
        out = tmp / name.replace("/", "_")
        out.write_bytes(content)
        out.chmod(0o755)
        try:
            text = subprocess.check_output(["readelf", "-d", str(out)], stderr=subprocess.DEVNULL, text=True)
        except Exception:
            return []
        deps = []
        for line in text.splitlines():
            if "(NEEDED)" in line and "[" in line:
                deps.append(line.split("[", 1)[1].split("]", 1)[0])
        return deps

    closure_missing = []
    seen = set()
    with tempfile.TemporaryDirectory(prefix="twrp_verify_") as td:
        tmp = Path(td)
        for seed in CLOSURE_SEEDS:
            if seed not in entries:
                continue
            queue = [(seed, entries[seed][2])]
            while queue:
                current, content = queue.pop()
                if current in seen:
                    continue
                seen.add(current)
                for dep in elf_needed(current, tmp):
                    if dep in seen:
                        continue
                    dep_name = lib_index.get(dep)
                    if dep_name is None:
                        closure_missing.append(f"{current}:{dep}")
                        seen.add(dep)
                        continue
                    queue.append((dep_name, entries[dep_name][2]))

    if closure_missing:
        print("ELF_DEP_MISSING " + ",".join(sorted(set(closure_missing))), file=sys.stderr)
        print("RECOVERY_IMAGE_VERIFY_FAILED elf-closure", file=sys.stderr)
        return 1
    print(f"ELF_CLOSURE_OK seeds={len(CLOSURE_SEEDS)} unique={len(seen)}")
    print("RECOVERY_IMAGE_VERIFY_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
