#!/usr/bin/env python3

# SPDX-FileCopyrightText: GARDENA GmbH
#
# SPDX-License-Identifier: LGPL-2.0-or-later

import inspect
import os
import sys

from IPython.lib.pretty import pretty

# In order to make this example usable out of the box, extend Python's module
# search path, such that the lemonbeat module will be found in the parent
# directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))))
from lemonbeat.mower_helpers import unpack_schedule


def main():
    """ Unpack schedules in hexstring format
    usage: mower_unpack_schedules.py 000E0B1E3C0000 ...
    """
    for hex_input in sys.argv[1:]:
        print(pretty(unpack_schedule(bytes.fromhex(hex_input))))


if __name__ == '__main__':
    main()
