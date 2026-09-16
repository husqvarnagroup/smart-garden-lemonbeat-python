# SPDX-FileCopyrightText: GARDENA GmbH
#
# SPDX-License-Identifier: LGPL-2.0-or-later

# coding=utf-8

"""
Lemonbeat service description definition.
"""

import enum


@enum.unique
class Service(enum.IntEnum):
    """Enum for port numbers of services.

    Taken from 'Table 2.1: List of services and port numbers' in LsDL spec. v. 1.13.
    """
    VALUE = 20000
    DEVICE_DESCRIPTION = 20001
    PUBLIC_KEY = 20002
    NETWORK_MANAGEMENT = 20003
    VALUE_DESCRIPTION = 20004
    SERVICE_DESCRIPTION = 20005
    MEMORY_INFORMATION = 20006
    PARTNER_INFORMATION = 20007
    ACTION = 20008
    CALCULATION = 20009
    TIMER = 20010
    CALENDAR = 20011
    STATE_MACHINE = 20012
    FIRMWARE_UPDATE = 20013
    CHANNEL_SCAN = 20014
    STATUS = 20015
    CONFIGURATION = 20016

    def __repr__(self):
        return str(self)

    @property
    def xmlns(self):
        """XML namespace used for this service."""
        # pylint is wrong here.
        return "urn:%sxsd" % self.name.lower()  # pylint: disable=no-member


@enum.unique
class ServiceDescriptionType(enum.IntEnum):
    """Enum for service description tags.

    Taken from 'Table 2.11: Service description types' in LsDL spec. v. 1.13.
    """
    PUBLIC_KEY = 1
    MEMORY_INFORMATION = 2
    DEVICE_DESCRIPTION = 3
    VALUE_DESCRIPTION = 4
    VALUE = 5
    PARTNER_INFORMATION = 6
    ACTION = 7
    CALCULATION = 8
    TIMER = 9
    CALENDAR = 10
    STATE_MACHINE = 11
    FIRMWARE_UPDATE = 12
    CHANNEL_SCAN = 13
    STATUS = 14
    CONFIGURATION = 15

    def __repr__(self):
        return str(self)
