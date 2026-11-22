#!/usr/bin/env python3
"""Fix TWRP gui/partitionlist.cpp -Wmisleading-indentation build error.

TWRP android-14 branch has an if/else without braces followed by two
over-indented statements, which both triggers clang -Wmisleading-indentation
and leaves the slot-part lookup outside the else. Rewrite the toggle without
the else branch so the behavior matches the intended braced logic.
"""
from pathlib import Path

p = Path("bootable/recovery/gui/partitionlist.cpp")
lines = p.read_text().splitlines(keepends=True)

IF = "if (mList.at(item_selected).selected)"
SET_ZERO = "mList.at(item_selected).selected = 0;"
SET_ONE = "mList.at(item_selected).selected = 1;"
FIND = "TWPartition* t_part = PartitionManager.Find_Partition_By_Path(mList.at(item_selected).Mount_Point);"
SET_SLOT = 'DataManager::SetValue("tw_is_slot_part", t_part != NULL ? (int) t_part->SlotSelect : 0);'

# android-14: if/else without braces; android-14.1: else with braces.
patterns = [
    [IF, SET_ZERO, "else", SET_ONE, FIND, SET_SLOT],
    [IF, SET_ZERO, "else {", SET_ONE, FIND, SET_SLOT, "}"],
]

patched = False
for idx, line in enumerate(lines):
    if line.strip() != IF:
        continue
    used = None
    for pattern in patterns:
        block = [x.strip() for x in lines[idx:idx + len(pattern)]]
        if block == pattern:
            used = pattern
            break
    if used is None:
        continue
    indent = line[:len(line) - len(line.lstrip())]
    new_lines = [
        indent + "mList.at(item_selected).selected = !mList.at(item_selected).selected;\n",
        indent + "if (mList.at(item_selected).selected) {\n",
        indent + "\t" + FIND + "\n",
        indent + "\t" + SET_SLOT + "\n",
        indent + "}\n",
    ]
    lines[idx:idx + len(used)] = new_lines
    patched = True
    break

if patched:
    p.write_text("".join(lines))
    print("PARTITIONLIST_INDENT_PATCHED")
else:
    print("PARTITIONLIST_PATTERN_NOT_FOUND")
