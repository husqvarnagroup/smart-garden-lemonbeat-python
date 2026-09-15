# SPDX-FileCopyrightText: GARDENA GmbH
#
# SPDX-License-Identifier: LGPL-2.0-or-later

# coding=utf-8

"""Compare element tree for equality."""


def eq(first, second):
    return (
            first.tag == second.tag and
            first.text == second.text and
            first.tail == second.tail and
            first.attrib == second.attrib and
            len(first) == len(second) and
            all(eq(child_first, child_second) for child_first, child_second in zip(first, second))
    )


def contained_in(element, container):
    return any([eq(e, element) for e in container])
