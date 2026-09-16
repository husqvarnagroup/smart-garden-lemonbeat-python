# SPDX-FileCopyrightText: GARDENA GmbH
#
# SPDX-License-Identifier: LGPL-2.0-or-later

# coding=utf-8

"""
Lemonbeat memory information definition.
"""

import enum


@enum.unique
class MemoryInformationType(enum.IntEnum):
    """Enum for memory information tags.

    Taken from 'Table 2.14: Memory IDs' in LsDL spec. v. 1.13.
    """
    VALUE = 1
    PARTNER_INFORMATION = 2
    ACTION_ITEMS = 3
    CALCULATION = 4
    TIMER = 5
    CALENDER = 6
    STATEMACHINE = 7
    STATEMACHINE_TRANSACTIONS = 8

    def __repr__(self):
        return str(self)
