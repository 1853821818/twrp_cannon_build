from pathlib import Path
import sys

path = Path("bootable/recovery/minuitwrp/graphics.cpp")
text = path.read_text()

needle = "static int overscan_percent = OVERSCAN_PERCENT;"
if "#define OVERSCAN_PERCENT" in text:
    print("MINUITWRP_OVERSCAN_ALREADY_DEFINED")
    sys.exit(0)
if needle not in text:
    print("MINUITWRP_OVERSCAN_SOURCE_NOT_FOUND")
    sys.exit(1)

text = text.replace(
    needle,
    "#ifndef OVERSCAN_PERCENT\n"
    "#define OVERSCAN_PERCENT 0\n"
    "#endif\n\n"
    + needle,
    1,
)
path.write_text(text)
print("MINUITWRP_OVERSCAN_PATCHED")
