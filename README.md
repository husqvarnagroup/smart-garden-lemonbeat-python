# Python Library for Lemonbeat

This repository contains a Python library for interaction with Lemonbeat
devices either via a Lemonbeat dongle or directly on a GARDENA smart Gateway.

# Installation

If you want to use this library anywhere in a script, you may install it by running:

```bash
pip3 install .
```

## PPP setup

See https://confluence-husqvarna.riada.se/display/SGS/BNW+Testing+Hardware+Lemonbeat+Dongle

## Interactive Use

Example usage in ipython3:

```python
## Optional, set up logging
## use logging.DEBUG for debug output
# import logging
# logging.basicConfig(level=logging.INFO)

from lemonbeat import *
from lemonbeat import config_file

gw, _ = config_file.load_or_create()
gw.include()

# Test if the dongle is reachable
gw.get_device_description()

# Start a service listener for retrieving the IPv6 addresses of unincluded devices
gw.start_service_listener(Service.DEVICE_DESCRIPTION, handler=lambda a, x: print(f"{a[0]} : {x}"))

# Stop all service listeners
gw.stop_service_listener()

# Interacting with a device
import time
time.sleep(5)
d = Device(gw, "fc00::6:e21b:edb8:7461")
d.include()
time.sleep(10)

# Note: ValueProperties only work for always-on devices.
# Currently a wake-on-radio device has to be manually woken before it can accessed.
# See further below on how to wake a device.
from lemonbeat.value_properties import ValueProperties
v = ValueProperties(d)
v.rf_link_quality

# Wake up device for an hour (2 being the partner id)
gw.set_partner_information(2, d.address)
gw.wakeup_partner(2, wakeup_now=3600000)

# Note: A hex value encodes a byte data buffer, the buffer length is
# implicitly encoded in the string used to construct the buffer.
# The string has to be of even length. Alternatively you can pass a
# Python bytes object.
gw.set_value(1, Hex("02"))
gw.get_value(1)
gw.set_value(1, Hex(b'foo'))
gw.get_value(1)
```

## Remote Gateway and SSH

See [remote_gateway_ssh.md](remote_gateway_ssh.md).

## Run Tests

Run all tests:
```bash
pytest-3
```

## Dependencies

To install the required Python libraries from Debian run:

```bash
sudo apt install python3-crcmod python3-pycryptodome python3-ipython python3-pytest python3-toml python3-xdg
```
