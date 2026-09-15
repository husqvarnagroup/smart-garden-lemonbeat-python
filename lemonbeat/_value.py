# SPDX-FileCopyrightText: GARDENA GmbH
#
# SPDX-License-Identifier: LGPL-2.0-or-later

# coding=utf-8

"""
The Lemonbeat values.
"""

import enum


@enum.unique
class ValueMode(enum.IntEnum):
    """Enum for radio modes."""
    R = 1
    RW = 2
    W = 3

    def __repr__(self):
        return str(self)
