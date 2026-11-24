#!/usr/bin/env python3
"""从 libaosprecovery 移除 TeamWin 分支中已失效的 AOSP install 源码。

TeamWin android-14 分支的 install/install.cpp 与 install/adb_install.cpp 来自
较新的 AOSP/Lineage 实现，但同分支的 install.h / otautil/package.h 仍是旧版：
- InstallPackage 调用多传 device 参数；
- CreateMemoryPackage 调用多传进度回调；
- adb_install.cpp 仍使用旧 install_file 签名，却引用未定义的 device；
这些源码没有被 TWRP 实际安装路径使用（TWRP 使用 libtwrpinstall/twrp_sideload），
保留只会造成编译错误。这里仅从 libaosprecovery 的 srcs 中移除这两个文件，
不改变 TWRP 的安装实现。
"""

import re
import sys
from pathlib import Path

bp = Path("bootable/recovery/Android.bp")
if not bp.exists():
    print("DROP_AOSP_INSTALL_FAILED: bootable/recovery/Android.bp not found")
    sys.exit(1)

text = bp.read_text()
for src in ("install/adb_install.cpp", "install/install.cpp"):
    # 只移除 libaosprecovery 块内的条目，避免误删其他模块。
    m = re.search(r'name:\s*"libaosprecovery"', text)
    if not m:
        print("DROP_AOSP_INSTALL_FAILED: libaosprecovery block not found")
        sys.exit(1)
    start = text.rfind("cc_library_shared", 0, m.start())
    end = text.find("\n}", m.end())
    if start == -1 or end == -1:
        print("DROP_AOSP_INSTALL_FAILED: libaosprecovery block bounds not found")
        sys.exit(1)
    block = text[start:end]
    line = f'        "{src}",'
    if line in block:
        block = block.replace(line + "\n", "", 1)
        text = text[:start] + block + text[end:]

bp.write_text(text)
for src in ("install/adb_install.cpp", "install/install.cpp"):
    if f'"{src}"' in bp.read_text():
        print(f"DROP_AOSP_INSTALL_FAILED: {src} still present")
        sys.exit(1)
print("AOSP_INSTALL_SOURCES_DROPPED")
