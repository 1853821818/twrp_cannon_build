#!/usr/bin/env python3
"""Ensure TWRP gui has a default theme when TW_THEME is not exported to Soong."""
p = "bootable/recovery/gui/libguitwrp_defaults.go"
s = open(p).read()
needle = '\tvar theme = determineTheme(ctx)\n'
insert = '\tvar theme = determineTheme(ctx)\n\tif theme == "" {\n\t\ttheme = "portrait_hdpi"\n\t}\n'
if 'if theme == ""' not in s:
    if needle not in s:
        raise SystemExit("theme needle not found")
    s = s.replace(needle, insert, 1)
    open(p, "w").write(s)
    print("patched theme fallback: portrait_hdpi")
else:
    print("theme fallback already present")
