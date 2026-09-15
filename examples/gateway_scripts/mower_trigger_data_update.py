#!/usr/bin/env python3

# SPDX-FileCopyrightText: GARDENA GmbH
#
# SPDX-License-Identifier: LGPL-2.0-or-later

from lemonbeat import Gateway, Device
from lemonbeat.value_properties import ValueProperties

DEVICE_ADDRESS = "fc00::6:94bb:ae19:d48e"

gw = Gateway(inclusion_message=None)
mower = Device(gw, DEVICE_ADDRESS)
mower.timeout = 10
mower_values = ValueProperties(mower)

mower_values.command = 21
