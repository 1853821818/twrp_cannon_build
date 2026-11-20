#!/usr/bin/env python3
"""Ensure TWRP gui has a default theme when TW_THEME is not exported to Soong.

The previous patch only covered copyThemeResources(), but copyTheme() calls
determineTheme() separately and still failed with "TW_THEME: not set".
Patch determineTheme()'s final return so both callers get a usable theme.
"""
p = "bootable/recovery/gui/libguitwrp_defaults.go"
s = open(p).read()

needle = '\treturn getMakeVars(ctx, "TW_THEME")\n'
insert = (
    '\ttheme := getMakeVars(ctx, "TW_THEME")\n'
    '\tif theme == "" {\n'
    '\t\ttheme = "portrait_hdpi"\n'
    '\t}\n'
    '\treturn theme\n'
)

if needle in s:
    s = s.replace(needle, insert, 1)
    open(p, "w").write(s)
    print("patched determineTheme fallback: portrait_hdpi")
elif 'theme := getMakeVars(ctx, "TW_THEME")' in s:
    print("determineTheme fallback already present")
else:
    raise SystemExit("determineTheme return needle not found")
