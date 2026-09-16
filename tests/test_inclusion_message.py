# SPDX-FileCopyrightText: GARDENA GmbH
#
# SPDX-License-Identifier: LGPL-2.0-or-later

from lemonbeat.inclusion_message import generate, generate_random_key


def test_generate_inclusion_message():
    assert generate(
        network_key=(bytes.fromhex("7a571383a14e06fa24322c92bbacc000")),
        controller_key=(bytes.fromhex("0102030405060708090a0b0c0d0e0f00"))
    ) == "096B44D32AE0A17554221DC38EF5BCFE2F70A23389D91DB374C220C21F9A1E9B" \
         "85705AFE3D31F6C2C68E12D9DA097773450CF042963D5C2C6C769F11F050606C"


def test_generate_random_inclusion_messages():
    messages = set()
    for _ in range(100):
        message = generate()
        assert len(message) == 128
        assert message not in messages
        messages.add(message)


def test_generate_random_keys():
    keys = set()
    for _ in range(100):
        key = generate_random_key()
        assert len(key) == 16
        assert key not in keys
        keys.add(key)
