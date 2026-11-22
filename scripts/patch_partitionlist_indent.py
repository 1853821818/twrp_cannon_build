#!/usr/bin/env python3
"""Fix TWRP 14.1 gui/partitionlist.cpp -Wmisleading-indentation build error.

The upstream toggle logic is semantically fine but clang treats the declaration
inside the else block as mis-indented. Rewrite the toggle without the else
branch while keeping identical behavior.
"""
from pathlib import Path

p = Path("bootable/recovery/gui/partitionlist.cpp")
s = p.read_text()

old = """\t\t\t\tif (mList.at(item_selected).selected)
\t\t\t\t\tmList.at(item_selected).selected = 0;
\t\t\t\telse {
\t\t\t\t\tmList.at(item_selected).selected = 1;
\t\t\t\t\tTWPartition* t_part = PartitionManager.Find_Partition_By_Path(mList.at(item_selected).Mount_Point);
\t\t\t\t\tDataManager::SetValue("tw_is_slot_part", t_part != NULL ? (int) t_part->SlotSelect : 0);
\t\t\t\t}
"""

new = """\t\t\t\tmList.at(item_selected).selected = !mList.at(item_selected).selected;
\t\t\t\tif (mList.at(item_selected).selected) {
\t\t\t\t\tTWPartition* t_part = PartitionManager.Find_Partition_By_Path(mList.at(item_selected).Mount_Point);
\t\t\t\t\tDataManager::SetValue("tw_is_slot_part", t_part != NULL ? (int) t_part->SlotSelect : 0);
\t\t\t\t}
"""

if old in s:
    p.write_text(s.replace(old, new, 1))
    print("PARTITIONLIST_INDENT_PATCHED")
else:
    print("PARTITIONLIST_PATTERN_NOT_FOUND")
