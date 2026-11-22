#!/usr/bin/env python3
"""Fix TWRP 14.1 gui/partitionlist.cpp -Wmisleading-indentation build error.

The upstream toggle logic is semantically fine but clang treats the declaration
inside the else block as mis-indented. Rewrite the toggle without the else
branch while keeping identical behavior.
"""
from pathlib import Path

p = Path("bootable/recovery/gui/partitionlist.cpp")
lines = p.read_text().splitlines(keepends=True)

old_block = [
    "if (mList.at(item_selected).selected)",
    "mList.at(item_selected).selected = 0;",
    "else {",
    "mList.at(item_selected).selected = 1;",
    "TWPartition* t_part = PartitionManager.Find_Partition_By_Path(mList.at(item_selected).Mount_Point);",
    'DataManager::SetValue("tw_is_slot_part", t_part != NULL ? (int) t_part->SlotSelect : 0);',
    "}",
]

patched = False
for idx, line in enumerate(lines):
    if line.strip() != old_block[0]:
        continue
    block = [x.strip() for x in lines[idx:idx + 7]]
    if block != old_block:
        continue
    indent = line[:len(line) - len(line.lstrip())]
    new_lines = [
        indent + "mList.at(item_selected).selected = !mList.at(item_selected).selected;\n",
        indent + "if (mList.at(item_selected).selected) {\n",
        indent + "\tTWPartition* t_part = PartitionManager.Find_Partition_By_Path(mList.at(item_selected).Mount_Point);\n",
        indent + '\tDataManager::SetValue("tw_is_slot_part", t_part != NULL ? (int) t_part->SlotSelect : 0);\n',
        indent + "}\n",
    ]
    lines[idx:idx + 7] = new_lines
    patched = True
    break

if patched:
    p.write_text("".join(lines))
    print("PARTITIONLIST_INDENT_PATCHED")
else:
    print("PARTITIONLIST_PATTERN_NOT_FOUND")
