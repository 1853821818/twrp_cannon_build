#!/usr/bin/env python3
"""给 TeamWin minui 补 ev_sync_sw_state（AOSP healthd charger UI 需要）。"""
from pathlib import Path

HEADER = Path("bootable/recovery/minui/include/minui/minui.h")
EVENTS = Path("bootable/recovery/minui/events.cpp")

h = HEADER.read_text()
if "ev_sync_sw_state" not in h:
    needle = "int ev_sync_key_state(const ev_set_key_callback& set_key_cb);"
    if needle not in h:
        raise SystemExit("SYNC_KEY_DECL_NOT_FOUND")
    h = h.replace(
        needle,
        needle
        + "\n#ifndef TW_USE_MINUI_WITH_DATA\n"
        + "int ev_sync_sw_state(const ev_set_sw_callback& set_sw_cb);\n"
        + "#endif",
        1,
    )
    HEADER.write_text(h)

e = EVENTS.read_text()
if "ev_sync_sw_state" not in e:
    needle = "int ev_sync_key_state(const ev_set_key_callback& set_key_cb) {"
    if needle not in e:
        raise SystemExit("SYNC_KEY_IMPL_NOT_FOUND")
    impl = """#ifndef TW_USE_MINUI_WITH_DATA
int ev_sync_sw_state(const ev_set_sw_callback& set_sw_cb) {
  // Use unsigned long to match ioctl's parameter type.
  unsigned long ev_bits[BITS_TO_LONGS(EV_MAX)];  // NOLINT
  unsigned long sw_bits[BITS_TO_LONGS(SW_MAX)];  // NOLINT

  for (size_t i = 0; i < g_ev_dev_count; ++i) {
    memset(ev_bits, 0, sizeof(ev_bits));
    memset(sw_bits, 0, sizeof(sw_bits));

    if (ioctl(ev_fdinfo[i].fd, EVIOCGBIT(0, sizeof(ev_bits)), ev_bits) == -1) {
      continue;
    }
    if (!test_bit(EV_SW, ev_bits)) {
      continue;
    }
    if (ioctl(ev_fdinfo[i].fd, EVIOCGSW(sizeof(sw_bits)), sw_bits) == -1) {
      continue;
    }

    for (int code = 0; code <= SW_MAX; code++) {
      if (test_bit(code, sw_bits)) {
        set_sw_cb(code, 1);
      }
    }
  }

  return 0;
}
#endif

"""
    e = e.replace(needle, impl + needle, 1)
    EVENTS.write_text(e)

print("MINUI_SW_STATE_PATCHED")
