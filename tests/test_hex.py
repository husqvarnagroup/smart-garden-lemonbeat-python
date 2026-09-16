# SPDX-FileCopyrightText: GARDENA GmbH
#
# SPDX-License-Identifier: LGPL-2.0-or-later

# coding=utf-8

"""Custom Hex value unit tests."""

import unittest

from lemonbeat import Hex


class TestHex(unittest.TestCase):
    """Lemonbeat values unit tests."""

    def test_equal(self):
        self.assertEqual(Hex("00"), Hex("00"))
        self.assertEqual(Hex("00"), Hex(b'\0'))
        self.assertEqual(Hex("00"), b'\0')
        self.assertEqual(Hex("01"), Hex("01"))
        self.assertEqual(Hex("01"), Hex(b'\x01'))
        self.assertEqual(Hex("01"), b'\x01')
        self.assertEqual(Hex("af"), Hex("af"))
        self.assertEqual(Hex("af"), Hex("AF"))
        self.assertEqual(Hex("af"), Hex(b'\xaf'))
        self.assertEqual(Hex("af"), b'\xaf')
        self.assertEqual(Hex(""), Hex(""))
        self.assertEqual(Hex(""), Hex(b''))
        self.assertEqual(Hex(""), b'')

    def test_unequal(self):
        self.assertNotEqual(Hex("01"), Hex("02"))
        self.assertNotEqual(Hex("01"), Hex("0a"))
        self.assertNotEqual(Hex("01"), Hex("0A"))
        self.assertNotEqual(Hex("0001"), Hex("01"))
        self.assertNotEqual(Hex("00af"), Hex("af"))
        self.assertNotEqual(Hex("00AF"), Hex("AF"))
        self.assertNotEqual(Hex("000001"), Hex("0001"))
        self.assertNotEqual(Hex("0000af"), Hex("00af"))
        self.assertNotEqual(Hex("0000AF"), Hex("00AF"))
        self.assertNotEqual(0, Hex("00"))
        self.assertNotEqual(1, Hex("01"))
        self.assertNotEqual(0xaf, Hex("af"))
        self.assertNotEqual(0xaf, Hex("AF"))

    def test_ordering(self):
        self.assertLess(Hex("01"), Hex("02"))
        self.assertLess(Hex("01"), Hex("0a"))
        self.assertLess(Hex("01"), Hex("0A"))

    def test_bool(self):
        self.assertTrue(Hex("01"))
        self.assertTrue(Hex("0a"))
        self.assertTrue(Hex("0A"))
        self.assertTrue(Hex("00"))
        self.assertFalse(Hex(""))

    def test_empty_hex_unequal(self):
        self.assertFalse(Hex("") == "")
        self.assertFalse("" == Hex(""))
        self.assertTrue(Hex("") != "")
        self.assertTrue("" != Hex(""))
        self.assertNotEqual(Hex(""), 0)
        self.assertNotEqual(Hex(""), Hex("00"))
        self.assertNotEqual(0, Hex(""))
        self.assertNotEqual(Hex("00"), Hex(""))

    def test_empty_hex_not_orderable(self):
        with self.assertRaises(TypeError):
            _ = Hex("") < 0
        with self.assertRaises(TypeError):
            _ = Hex("") > 0

    def test_odd_length_hex_fails(self):
        with self.assertRaises(Exception):
            Hex("0")
        with self.assertRaises(Exception):
            Hex("1")
        with self.assertRaises(Exception):
            Hex("a")
        with self.assertRaises(Exception):
            Hex("A")
        with self.assertRaises(Exception):
            Hex("ABC")

    def test_length(self):
        # The length of the hex buffer in bytes, counting
        # the raw data, not the string representation.
        self.assertEqual(0, len(Hex("")))
        self.assertEqual(1, len(Hex("10")))
        self.assertEqual(2, len(Hex("1000")))
        self.assertEqual(1, len(Hex("ab")))
        self.assertEqual(2, len(Hex("abcd")))

    def test_invalid_types(self):
        with self.assertRaises(TypeError):
            Hex(0)
        with self.assertRaises(TypeError):
            Hex(1)
        with self.assertRaises(TypeError):
            Hex(0.0)
        with self.assertRaises(TypeError):
            Hex(1.0)
        with self.assertRaises(TypeError):
            Hex(None)

    def test_invalid_characters(self):
        with self.assertRaises(Exception):
            Hex(" 0")
        with self.assertRaises(Exception):
            Hex(" 1")
        with self.assertRaises(Exception):
            Hex("-0")
        with self.assertRaises(Exception):
            Hex("-1")
        with self.assertRaises(Exception):
            Hex("fg")
        with self.assertRaises(Exception):
            Hex("0x00")
        with self.assertRaises(Exception):
            Hex("0xaf")
        with self.assertRaises(Exception):
            Hex("0.00")
        with self.assertRaises(Exception):
            Hex("1.00")

    def test_repr(self):
        self.assertEqual("Hex('')", repr(Hex("")))
        self.assertEqual("Hex('00')", repr(Hex("00")))
        self.assertEqual("Hex('01')", repr(Hex("01")))
        self.assertEqual("Hex('af')", repr(Hex("af")))
        self.assertEqual("Hex('af')", repr(Hex("AF")))
        self.assertEqual("Hex('0000')", repr(Hex("0000")))
        self.assertEqual("Hex('0001')", repr(Hex("0001")))
        self.assertEqual("Hex('00af')", repr(Hex("00af")))
        self.assertEqual("Hex('00af')", repr(Hex("00AF")))
