#!/usr/bin/env python3
"""Switch TWRP's libsqlite to the no-ICU variant.

The TWRP minimal manifest does not carry external/icu, so libsqlite's
libandroidicu dependency cannot be resolved. AOSP already ships
libsqlite3_android_noicu; use it and drop the ICU shared libraries/flags.
"""

from pathlib import Path

DIST = Path("external/sqlite/dist/Android.bp")
ANDROID = Path("external/sqlite/android/Android.bp")


def add_recovery_available(text, module_name, path):
    marker = f'name: "{module_name}",'
    if marker not in text:
        raise SystemExit(f"missing module {module_name} in {path}")
    idx = text.index(marker)
    window = text[idx:idx + 300]
    if "recovery_available" in window:
        return text
    return text[:idx + len(marker)] + "\n    recovery_available: true," + text[idx + len(marker):]

if not DIST.exists():
    raise SystemExit(f"missing {DIST}")

text = DIST.read_text()

old_android = '''            shared_libs: [
                "libdl",
                "liblog",
                "libandroidicu",
            ],
            cflags: ["-DSQLITE_ENABLE_ICU"],

            // include android specific methods
            whole_static_libs: ["libsqlite3_android"],
'''
new_android = '''            shared_libs: [
                "libdl",
                "liblog",
            ],

            // include android specific methods
            whole_static_libs: ["libsqlite3_android_noicu"],
'''

old_not_windows = '''        not_windows: {
            shared_libs: [
                "libicui18n",
                "libicuuc",
            ],

            // include android specific methods
            whole_static_libs: ["libsqlite3_android"],
        },
'''
new_not_windows = '''        not_windows: {
            // include android specific methods
            whole_static_libs: ["libsqlite3_android_noicu"],
        },
'''

old_binary = '''            shared_libs: [
                "libsqlite",
                "libandroidicu",
                "liblog",
                "libutils",
            ],
'''
new_binary = '''            shared_libs: [
                "libsqlite",
                "liblog",
                "libutils",
            ],
'''

for old, new, label in (
    (old_android, new_android, "libsqlite/android"),
    (old_not_windows, new_not_windows, "libsqlite/not_windows"),
    (old_binary, new_binary, "sqlite3/binary"),
):
    if old not in text:
        raise SystemExit(f"sqlite patch anchor missing: {label}")
    text = text.replace(old, new, 1)

DIST.write_text(
    add_recovery_available(text, "libsqlite", str(DIST))
)

if not ANDROID.exists():
    raise SystemExit(f"missing {ANDROID}")
android_text = ANDROID.read_text()
ANDROID.write_text(
    add_recovery_available(android_text, "libsqlite3_android_noicu", str(ANDROID))
)

for target in (DIST, ANDROID):
    if "recovery_available: true" not in target.read_text():
        raise SystemExit(f"recovery_available not added to {target}")

for line in DIST.read_text().splitlines():
    if "libandroidicu" in line and "exclude_shared_libs" not in line:
        raise SystemExit(f"libandroidicu still active in external/sqlite/dist/Android.bp: {line.strip()}")
print("SQLITE_NOICU_PATCHED")
print("SQLITE_RECOVERY_VARIANTS_ADDED libsqlite libsqlite3_android_noicu")
