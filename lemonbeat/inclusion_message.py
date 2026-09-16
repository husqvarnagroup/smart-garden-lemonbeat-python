# coding=utf-8

# Copyright 2019 Gardena GmbH
# Adrian Friedli <adrian.friedli@husqvarnagroup.com>
#
# SPDX-License-Identifier: LGPL-2.0-or-later

"""
Utility functions for generating the inclusion message and random keys.
"""

__version__ = "0.1.0"

__all__ = [
    "generate",
    "generate_random_key",
]

import random

from Cryptodome.Cipher import AES
from crcmod.predefined import mkPredefinedCrcFun

_DEFAULT_PUBLIC_KEY = (
    # pylint: disable=line-too-long
    544707154624265008293115003105252727119040163562979127814065552874241070617335139097638779009662600671942632638047851873648163272789081193108015117548459,
    65537,
)


def generate(network_key=None, *, controller_key=None, public_key=_DEFAULT_PUBLIC_KEY):
    """Generate an inclusion message for given network key.

    :param network_key: network key, unique for each network, defaults
           to a randomly generated key
    :param controller_key: controller key, can be randomly chosen
           (default), even for subsequent inclusions in the same network
    :param public_key: RSA public key tuple
    :return: inclusion message
    """
    if network_key is None:
        network_key = generate_random_key()
    if controller_key is None:
        controller_key = generate_random_key()
    encrypted_network_key = AES.new(controller_key, AES.MODE_ECB).encrypt(network_key)
    message = controller_key + encrypted_network_key
    message = message + (mkPredefinedCrcFun("xmodem")(message)).to_bytes(2, byteorder='big')
    inclusion_message = _rsa_encrypt(int.from_bytes(message, 'big'), public_key).to_bytes(64, 'big')
    return inclusion_message.hex().upper()


def generate_random_key():
    """Generate a random key

    :return: random key
    """
    return bytes([random.randint(0, 255) for _ in range(16)])


def _rsa_encrypt(plaintext, rsa_components):
    n, e = rsa_components
    if not 0 <= plaintext < n:
        raise ValueError("Plaintext too large")
    return pow(plaintext, e, n)
