# SPDX-FileCopyrightText: GARDENA GmbH
#
# SPDX-License-Identifier: LGPL-2.0-or-later

# coding=utf-8

"""
Lemonbeat device description definition.
"""

import enum


@enum.unique
class DeviceDescriptionType(enum.IntEnum):
    """Enum for device description types.

    Taken from 'Table 2.17: Device description types' in LsDL spec. v. 1.13.
    This list has been extended with information from the file ddk/lemonbeat/doc/api/lsdl.html in the Lemonbeat DDK release 1.6.0.
    """
    DEVICE_TYPE = 1
    DEVICE_MANUFACTURER = 2
    SGTIN = 3
    MAC_ADDRESS = 4
    HARDWARE_VERSION = 5
    BOOTLOADER_VERSION = 6
    STACK_VERSION = 7
    APPLICATION_VERSION = 8
    PROTOCOL = 9
    DEVICE_PRODUCT = 10
    INCLUDED = 11
    NAME = 12
    RADIO_MODE = 13
    WAKEUP_INTERVAL = 14
    WAKEUP_OFFSET = 15
    WAKEUP_CHANNEL = 16
    CHANNEL_MAP = 17
    CHANNEL_SCAN_TIME = 18
    IPV6_ADDRESS = 19
    WAKEUP_NOW = 20
    DIVERSITY_MODE = 21
    UNDOCUMENTED_22 = 22  # Send RSSI
    UNDOCUMENTED_23 = 23  # Receive RSSI
    UNDOCUMENTED_24 = 24  # Receive Timestamp
    TX_POWER = 27
    UPTIME = 49

    def __repr__(self):
        return str(self)


@enum.unique
class RadioMode(enum.IntEnum):
    """Enum for radio modes.

    Taken from 'Table 2.19: Radio Mode' in LsDL spec. v. 1.13.
    """
    ALWAYS_ONLINE = 0
    WAKE_ON_RADIO = 1
    WAKE_ON_EVENT = 2
    TX_ONLY = 3
    RX_ONLY = 4

    def __repr__(self):
        return str(self)
