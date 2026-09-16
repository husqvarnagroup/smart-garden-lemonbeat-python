#!/usr/bin/env python3

# SPDX-FileCopyrightText: GARDENA GmbH
#
# SPDX-License-Identifier: LGPL-2.0-or-later

import inspect
import os
import sys

# In order to make this example usable out of the box, extend Python's module
# search path, such that the lemonbeat module will be found in the parent
# directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))))
from lemonbeat.mower_helpers import unpack_schedule, Task


def schedule_to_canonical(schedule):
    combined = {}
    for task in schedule:
        if task.weekdays != '0000000':
            wd = [i for i, w in enumerate(task.weekdays) if w != '0']
            combined.setdefault((task.start, task.duration, task.a_id), set()).update(wd)
    result = set()
    for (start, duration, a_id), wd in combined.items():
        weekdays = ''.join(['1' if d in wd else '0' for d in range(7)])
        result.add(Task(None, weekdays, start, duration, a_id))
    return result


def compare_hex_schedules(hex_schedule1, hex_schedule2):
    canonical1 = schedule_to_canonical(unpack_schedule(bytes.fromhex(hex_schedule1)))
    canonical2 = schedule_to_canonical(unpack_schedule(bytes.fromhex(hex_schedule2)))
    return canonical1 == canonical2


def main():
    if compare_hex_schedules(sys.argv[1], sys.argv[2]):
        print("Identical")
    else:
        print("Mismatch")


if __name__ == '__main__':
    main()


def test_compare_hex_schedules():
    input1 = unpack_schedule(bytes.fromhex("002A0700B40000"))
    input2 = unpack_schedule(bytes.fromhex("00020700B4000001080700B4000002200700B40000"))
    assert schedule_to_canonical(input1) == schedule_to_canonical(input2)

    input3 = unpack_schedule(bytes.fromhex("002A0800B40000"))
    input4 = unpack_schedule(bytes.fromhex(
        "00010800940200010208009402000204080094020003080800940200041008009402000520080094020006400800940200"))
    assert schedule_to_canonical(input3) != schedule_to_canonical(input4)
