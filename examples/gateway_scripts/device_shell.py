#!/usr/bin/env python3

# SPDX-FileCopyrightText: GARDENA GmbH
#
# SPDX-License-Identifier: LGPL-2.0-or-later

import pdb

from lemonbeat import Gateway, Device, RequestTimeoutError
from lemonbeat.value_properties import ValueProperties

DEVICE_ADDRESS = "fc00::6:94bb:ae19:d48e"

gw = Gateway(lemonbeatd_network_key=True)
device = Device(gw, DEVICE_ADDRESS)
device.timeout = 10

try:
    device_values = ValueProperties(device)
except RequestTimeoutError:
    print("Timeout while requesting value description. Is device included?")

pdb.set_trace()
