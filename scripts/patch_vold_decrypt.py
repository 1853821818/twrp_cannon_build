#!/usr/bin/env python3
"""把 TWRP 的 FBE 解密实现接回 AOSP 14 的 system/vold。

AOSP 14 的 system/vold 删除了 TeamWin recovery 仍在调用的
android::keystore::{copySqliteDb,Get_Password_Type,Decrypt_DE,Decrypt_User}。
这些函数在 TeamWin 的 vold 分支里对应 Decrypt.cpp / HashPassword.cpp /
KeystoreInfo.cpp / Weaver1.cpp。这里把这组兼容源码复制进 system/vold，
并把它们加入 libvold 的源文件和依赖，避免 recovery 编译到 91% 后卡在
'Decrypt.h' file not found，链接阶段又缺 Decrypt_* 符号。
"""

import re
import shutil
import sys
from pathlib import Path

ROOT = Path.cwd()
SKILL_SRC = Path(__file__).resolve().parent / "decrypt_compat"
DEST = ROOT / "system" / "vold"


def fail(msg):
    print(f"VOLD_DECRYPT_PATCH_FAILED: {msg}")
    sys.exit(1)


def insert_before_array_close(text, marker, block_start, new_lines):
    """在 block_start 之后的第一个 marker: [ ... ] 的 ] 前插入行。"""
    m = re.search(re.escape(marker) + r"\s*:\s*\[", text[block_start:])
    if not m:
        return None
    start = block_start + m.end()
    end = text.find("]", start)
    if end == -1:
        return None
    insertion = "".join(f'\n        "{line}",' for line in new_lines)
    return text[:end] + insertion + text[end:]


if not DEST.exists():
    fail(f"not found: {DEST}")

copied = []
for name in [
    "Decrypt.h",
    "Decrypt.cpp",
    "HashPassword.h",
    "HashPassword.cpp",
    "KeystoreInfo.hpp",
    "KeystoreInfo.cpp",
    "Weaver1.h",
    "Weaver1.cpp",
]:
    src = SKILL_SRC / name
    if not src.exists():
        fail(f"missing source {src}")
    shutil.copy2(src, DEST / name)
    copied.append(name)
print("VOLD_DECRYPT_SOURCES_COPIED " + " ".join(copied))

bp = DEST / "Android.bp"
text = bp.read_text()
if '"Decrypt.cpp"' in text:
    print("VOLD_DECRYPT_ALREADY_PATCHED")
    sys.exit(0)

# 定位 libvold 的 cc_library_static 块
libvold_m = re.search(r'name:\s*"libvold"', text)
if not libvold_m:
    fail("libvold block not found")
block_start = text.rfind("cc_library_static", 0, libvold_m.start())
if block_start == -1:
    fail("cc_library_static before libvold not found")

# 1) 补源码
src_names = ["Decrypt.cpp", "HashPassword.cpp", "Weaver1.cpp"]
result = insert_before_array_close(text, "srcs", block_start, src_names)
if result is None:
    fail("libvold srcs array not found")
text = result

# 2) 补 scrypt 静态库：Decrypt.cpp 使用 crypto_scrypt()
#    libscrypt_static 由 external/scrypt 定义（AOSP 14 PDK 组），export include dir
if 'name: "libvold"' in text and 'libscrypt_static' not in text:
    # 在 libvold 的 shared_libs: [ 前插入 static_libs
    shared_m = re.search(r'shared_libs:\s*\[', text[block_start:])
    if not shared_m:
        fail("libvold shared_libs not found")
    pos = block_start + shared_m.start()
    text = text[:pos] + 'static_libs: ["libscrypt_static"],\n    ' + text[pos:]

# 3) 补 shared_libs：keystore/gatekeeper/keymaster/weaver/confirmationui 等
extra_libs = [
    "android.hardware.confirmationui@1.0",
    "android.hardware.gatekeeper@1.0",
    "android.hardware.keymaster@4.1",
    "android.hardware.security.keymint-V1-ndk_platform",
    "android.hardware.weaver@1.0",
    "android.security.apc-ndk_platform",
    "android.security.authorization-ndk_platform",
    "android.system.keystore2-V1-ndk_platform",
    "libbinder",
    "libbinder_ndk",
    "libgatekeeper",
    "libgatekeeper_aidl",
    "libkeymaster4_1support",
    "libkeystore-attestation-application-id",
    "libkeystoreinfo",
    "libkeyutils",
]
result = insert_before_array_close(text, "shared_libs", block_start, extra_libs)
if result is None:
    fail("libvold shared_libs array not found")
text = result

# 4) 补 include dirs（KeystoreInfo.hpp 的 sqlite3.h 已由 libkeystoreinfo module 处理）
inc_m = re.search(r'include_dirs:\s*\[', text[block_start:])
if not inc_m:
    # 没有 include_dirs 时，在 srcs 前插入
    src_m = re.search(r'srcs:\s*\[', text[block_start:])
    if not src_m:
        fail("libvold srcs marker missing")
    pos = block_start + src_m.start()
    text = text[:pos] + 'include_dirs: ["system/core/gatekeeperd/include", "external/scrypt/lib/crypto"],\n    ' + text[pos:]
else:
    start = block_start + inc_m.end()
    end = text.find("]", start)
    text = text[:end] + '\n        "external/scrypt/lib/crypto",' + text[end:]

# 5) 追加 libkeystoreinfo 模块（recovery 的 Android.mk 已显式链接 libkeystoreinfo.recovery）
if 'name: "libkeystoreinfo"' not in text:
    text += r'''

cc_library {
    name: "libkeystoreinfo",
    host_supported: true,
    cflags: [
        "-Wno-unused-parameter",
        "-Wno-unused-variable",
    ],
    include_dirs: [
        "external/sqlite/dist/",
        "system/vold",
    ],
    recovery_available: true,
    srcs: [
        "KeystoreInfo.cpp",
    ],
    shared_libs: [
        "libsqlite",
    ],
    system_shared_libs: [
        "libc",
        "libdl",
    ],
}
'''

bp.write_text(text)
print("VOLD_DECRYPT_PATCHED")
