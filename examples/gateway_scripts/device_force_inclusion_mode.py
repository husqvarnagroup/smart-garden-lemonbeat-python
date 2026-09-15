#!/usr/bin/env python3

# SPDX-FileCopyrightText: GARDENA GmbH
#
# SPDX-License-Identifier: LGPL-2.0-or-later

import time

from lemonbeat import Gateway, Device

DEVICE_ADDRESS = "fc00::6:94bb:ae19:d48e"

gw = Gateway(lemonbeatd_network_key=True)
device = Device(gw, DEVICE_ADDRESS)

# also works after the 3 minutes inclusion timeout
device.include()

time.sleep(10)

# performs a factory reset, device will be in inclusion mode afterwards
device.exclude()
