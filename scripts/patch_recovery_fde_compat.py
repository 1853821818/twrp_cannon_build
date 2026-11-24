#!/usr/bin/env python3
"""为 TWRP recovery 的遗留 FDE 调用补最小兼容层。

TeamWin recovery android-14 的 partition.cpp / partitionmanager.cpp 仍保留
旧版 vold 的 FDE API（set_partition_data / cryptfs_check_footer /
cryptfs_get_password_type / delete_crypto_blk_dev），但 TeamWin vold
android-14 的 cryptfs.h 已不再声明、libvold 也不再实现这些符号。
本机是 FBE 设备，实际解密走 Decrypt_User / fscrypt，不需要 FDE；
这里只补声明与安全的 no-op/失败返回实现，保证 recovery 能编译链接，
同时不会伪造 FDE 解密成功。
"""

import re
import sys
from pathlib import Path

ROOT = Path.cwd()
RECOVERY = ROOT / "bootable" / "recovery"
VOLD = ROOT / "system" / "vold"


def fail(msg):
    print(f"RECOVERY_FDE_COMPAT_FAILED: {msg}")
    sys.exit(1)


# 1) partitionmanager.cpp 只需要 CRYPT_TYPE_DEFAULT，原 12.1 头还带 vold 内部 map。
hdr = RECOVERY / "fscrypt-common.h"
if not hdr.exists():
    hdr.write_text(
        "#ifndef TWRP_FSCRYPT_COMMON_COMPAT_H\n"
        "#define TWRP_FSCRYPT_COMMON_COMPAT_H\n"
        "/* 仅保留 TWRP recovery 需要的 FDE 密码类型常量。 */\n"
        "#define CRYPT_TYPE_DEFAULT 1\n"
        "#endif\n"
    )
print("RECOVERY_FSCRYPT_COMMON_HEADER_ADDED")

# 2) 在 TeamWin 14 的 cryptfs.h 末尾补旧 FDE 声明。
cryptfs_h = VOLD / "cryptfs.h"
if not cryptfs_h.exists():
    fail(f"not found: {cryptfs_h}")
text = cryptfs_h.read_text()
if "twrp_fde_compat" not in text:
    marker = "#endif /* ANDROID_VOLD_CRYPTFS_H */"
    if marker not in text:
        fail("cryptfs.h endif marker not found")
    block = r'''
/* twrp_fde_compat: TeamWin recovery android-14 仍引用旧 vold 的 FDE API。
 * 本机使用 FBE，这些符号只用于编译/链接；实现为安全的 no-op/失败返回。 */
extern "C" {
int cryptfs_check_footer(void);
int cryptfs_get_password_type(void);
void set_partition_data(const char* block_device, const char* key_location);
int delete_crypto_blk_dev(const std::string& name);
}
'''
    text = text.replace(marker, block + "\n" + marker, 1)
    cryptfs_h.write_text(text)
print("RECOVERY_CRYPTFS_FDE_DECLS_ADDED")

# 3) libvold 内补兼容实现，recovery 通过 libvold 静态链接拿到符号。
compat_cpp = VOLD / "LegacyFdeCompat.cpp"
compat_cpp.write_text(r'''#include <string>

extern "C" {
int cryptfs_check_footer(void) { return -1; } /* 无旧 FDE footer */
int cryptfs_get_password_type(void) { return 0; } /* 非默认密码，避免误走默认解密 */
void set_partition_data(const char*, const char*) {}
int delete_crypto_blk_dev(const std::string&) { return 0; }
}
''')
print("RECOVERY_LEGACY_FDE_COMPAT_CPP_WRITTEN")

bp = VOLD / "Android.bp"
text = bp.read_text()
if '"LegacyFdeCompat.cpp"' not in text:
    m = re.search(r'name:\s*"libvold"', text)
    if not m:
        fail("libvold block not found")
    start = text.rfind("cc_library_static", 0, m.start())
    if start == -1:
        fail("libvold cc_library_static not found")
    src_m = re.search(r'srcs:\s*\[', text[start:])
    if not src_m:
        fail("libvold srcs not found")
    pos = start + src_m.end()
    text = text[:pos] + '\n        "LegacyFdeCompat.cpp",' + text[pos:]
    bp.write_text(text)
print("RECOVERY_LEGACY_FDE_COMPAT_ADDED_TO_LIBVOLD")
