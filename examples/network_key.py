# SPDX-FileCopyrightText: GARDENA GmbH
#
# SPDX-License-Identifier: LGPL-2.0-or-later

# coding=utf-8

"""
Example Lemonbeat Network Key.

See https://confluence.dss.husqvarnagroup.com/display/SGS/Lemonbeat+Device+Inclusion for more information.
"""

from lemonbeat.inclusion_message import generate

_NETWORK_KEY = bytes.fromhex("7a571383a14e06fa24322c92bbacc000")
_CONTROLLER_KEY = bytes.fromhex("0102030405060708090a0b0c0d0e0f00")

INCLUSION_MESSAGE = generate(network_key=_NETWORK_KEY, controller_key=_CONTROLLER_KEY)
