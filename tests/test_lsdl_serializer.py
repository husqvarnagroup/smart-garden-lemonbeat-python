# SPDX-FileCopyrightText: GARDENA GmbH
#
# SPDX-License-Identifier: LGPL-2.0-or-later

# coding=utf-8

"""LSDL serializer unit tests."""

import threading
import unittest

from lemonbeat import lsdl_serializer, Service


class TestLsdlSerializer(unittest.TestCase):
    """LSDL serializer unit tests."""

    def test_get_version(self):
        """Test get version."""
        self.assertEqual('0.2.8', lsdl_serializer.get_version())

    def test_compress(self):
        """Test simple compression."""
        xml = b'<network version="1" xmlns="urn:valuexsd"><device version="1"><value_get /></device></network>'
        expected = b'\x80\x00\x50\x08\x62'
        self.assertEqual(expected, lsdl_serializer.compress(Service.VALUE.value, xml))

    def test_decompress(self):
        """Test simple decompression."""
        exi = b'\x80\x00\x50\x08\x62'
        expected = b'<network xmlns="urn:valuexsd" version="1"><device version="1"><value_get></value_get></device>' \
                   b'</network>'
        self.assertEqual(expected, lsdl_serializer.decompress(Service.VALUE.value, exi))

    def assertRoundTripConversion(self, port, xml_input, msg=None):
        exi = lsdl_serializer.compress(port, xml_input)
        xml_output = lsdl_serializer.decompress(port, exi)
        self.assertEqual(xml_input, xml_output, msg)

    def test_number_zero(self):
        """Test compression and decompression of a number 0 value."""
        self.assertRoundTripConversion(
            Service.VALUE.value,
            b'<network xmlns="urn:valuexsd" version="1"><device version="1">'
            b'<value_set number="0.0" timestamp="0" value_id="42"></value_set></device></network>'
        )

        self.assertRoundTripConversion(
            Service.VALUE.value,
            b'<network xmlns="urn:valuexsd" version="1"><device device_id="1" version="1">'
            b'<value_report number="0.0" timestamp="517276800" value_id="23"></value_report></device></network>'
        )

    def test_number_negative_zero(self):
        """Test compression of a number -0 results in a 0 value when decompressed."""
        xml_input = b'<network xmlns="urn:valuexsd" version="1"><device version="1">' \
                    b'<value_set number="-0.0" timestamp="0" value_id="42"></value_set></device></network>'
        xml_output_expected = b'<network xmlns="urn:valuexsd" version="1"><device version="1">' \
                              b'<value_set number="0.0" timestamp="0" value_id="42"></value_set></device></network>'
        exi = lsdl_serializer.compress(Service.VALUE.value, xml_input)
        xml_output = lsdl_serializer.decompress(Service.VALUE.value, exi)
        self.assertEqual(xml_output_expected, xml_output)

        xml_input = b'<network xmlns="urn:valuexsd" version="1"><device device_id="1" version="1">' \
                    b'<value_report number="-0.0" timestamp="517276800" value_id="23"></value_report></device>' \
                    b'</network>'
        xml_output_expected = b'<network xmlns="urn:valuexsd" version="1"><device device_id="1" version="1">' \
                              b'<value_report number="0.0" timestamp="517276800" value_id="23"></value_report>' \
                              b'</device></network>'
        exi = lsdl_serializer.compress(Service.VALUE.value, xml_input)
        xml_output = lsdl_serializer.decompress(Service.VALUE.value, exi)
        self.assertEqual(xml_output_expected, xml_output)

    def test_number(self):
        """Test compression and decompression of a positive number value."""
        self.assertRoundTripConversion(
            Service.VALUE.value,
            b'<network xmlns="urn:valuexsd" version="1"><device version="1">'
            b'<value_set number="23.25" timestamp="0" value_id="13"></value_set></device></network>'
        )

        self.assertRoundTripConversion(
            Service.VALUE.value,
            b'<network xmlns="urn:valuexsd" version="1"><device device_id="1" version="1">'
            b'<value_report number="23.25" timestamp="517276800" value_id="17"></value_report></device></network>'
        )

    def test_negative_number(self):
        """Test compression and decompression of a negative number value."""
        self.assertRoundTripConversion(
            Service.VALUE.value,
            b'<network xmlns="urn:valuexsd" version="1"><device version="1">'
            b'<value_set number="-23.25" timestamp="0" value_id="13"></value_set></device></network>'
        )

        self.assertRoundTripConversion(
            Service.VALUE.value,
            b'<network xmlns="urn:valuexsd" version="1"><device device_id="1" version="1">'
            b'<value_report number="-23.25" timestamp="517276800" value_id="17"></value_report></device></network>'
        )

    def test_number_nan(self):
        """Test compression and decompression of a NaN value."""
        self.assertRoundTripConversion(
            Service.VALUE.value,
            b'<network xmlns="urn:valuexsd" version="1"><device version="1">'
            b'<value_set number="NaN" timestamp="0" value_id="42"></value_set></device></network>'
        )

        self.assertRoundTripConversion(
            Service.VALUE.value,
            b'<network xmlns="urn:valuexsd" version="1"><device device_id="1" version="1">'
            b'<value_report number="NaN" timestamp="517276800" value_id="23"></value_report></device></network>'
        )

    def test_number_inf(self):
        """Test compression and decompression of an INF value."""
        self.assertRoundTripConversion(
            Service.VALUE.value,
            b'<network xmlns="urn:valuexsd" version="1"><device version="1">'
            b'<value_set number="INF" timestamp="0" value_id="42"></value_set></device></network>'
        )

        self.assertRoundTripConversion(
            Service.VALUE.value,
            b'<network xmlns="urn:valuexsd" version="1"><device device_id="1" version="1">'
            b'<value_report number="INF" timestamp="517276800" value_id="23"></value_report></device></network>'
        )

    def test_number_negative_inf(self):
        """Test compression and decompression of a -INF value."""
        self.assertRoundTripConversion(
            Service.VALUE.value,
            b'<network xmlns="urn:valuexsd" version="1"><device version="1">'
            b'<value_set number="-INF" timestamp="0" value_id="42"></value_set></device></network>'
        )

        self.assertRoundTripConversion(
            Service.VALUE.value,
            b'<network xmlns="urn:valuexsd" version="1"><device device_id="1" version="1">'
            b'<value_report number="-INF" timestamp="517276800" value_id="23"></value_report></device></network>'
        )

    def test_empty_hex(self):
        """Test compression and decompression of an empty hex value."""
        self.assertRoundTripConversion(
            Service.VALUE.value,
            b'<network xmlns="urn:valuexsd" version="1"><device version="1">'
            b'<value_set hexBinary="" timestamp="0" value_id="42"></value_set></device></network>'
        )

        self.assertRoundTripConversion(
            Service.VALUE.value,
            b'<network xmlns="urn:valuexsd" version="1"><device device_id="1" version="1">'
            b'<value_report hexBinary="" timestamp="517276800" value_id="23"></value_report></device></network>'
        )

    def test_hex(self):
        """Test compression and decompression of a hex value."""
        self.assertRoundTripConversion(
            Service.VALUE.value,
            b'<network xmlns="urn:valuexsd" version="1"><device version="1">'
            b'<value_set hexBinary="AD11" timestamp="0" value_id="13"></value_set></device></network>'
        )

        self.assertRoundTripConversion(
            Service.VALUE.value,
            b'<network xmlns="urn:valuexsd" version="1"><device device_id="1" version="1">'
            b'<value_report hexBinary="F000" timestamp="517276800" value_id="17"></value_report></device></network>'
        )

    def test_hex_is_converted_to_uppercase(self):
        """Test compression and decompression of a lowercase hex value results in an uppercase hex value."""
        xml_input = b'<network xmlns="urn:valuexsd" version="1"><device version="1">' \
                    b'<value_set hexBinary="abcdef" timestamp="0" value_id="13">' \
                    b'</value_set></device></network>'
        xml_output_expected = b'<network xmlns="urn:valuexsd" version="1"><device version="1">' \
                              b'<value_set hexBinary="ABCDEF" timestamp="0" value_id="13">' \
                              b'</value_set></device></network>'
        exi = lsdl_serializer.compress(Service.VALUE.value, xml_input)
        xml_output = lsdl_serializer.decompress(Service.VALUE.value, exi)
        self.assertEqual(xml_output_expected, xml_output)

        xml_input = b'<network xmlns="urn:valuexsd" version="1"><device device_id="1" version="1">' \
                    b'<value_report hexBinary="fedcba" timestamp="517276800" value_id="17">' \
                    b'</value_report></device></network>'
        xml_output_expected = b'<network xmlns="urn:valuexsd" version="1"><device device_id="1" version="1">' \
                              b'<value_report hexBinary="FEDCBA" timestamp="517276800" value_id="17">' \
                              b'</value_report></device></network>'
        exi = lsdl_serializer.compress(Service.VALUE.value, xml_input)
        xml_output = lsdl_serializer.decompress(Service.VALUE.value, exi)
        self.assertEqual(xml_output_expected, xml_output)

    def test_empty_string(self):
        """Test compression and decompression of empty string value."""
        self.assertRoundTripConversion(
            Service.VALUE.value,
            b'<network xmlns="urn:valuexsd" version="1"><device version="1">'
            b'<value_set string="" timestamp="0" value_id="42"></value_set></device></network>'
        )

        self.assertRoundTripConversion(
            Service.VALUE.value,
            b'<network xmlns="urn:valuexsd" version="1"><device device_id="1" version="1">'
            b'<value_report string="" timestamp="517276800" value_id="23"></value_report></device></network>'
        )

    def test_string(self):
        """Test compression and decompression of a string value."""
        self.assertRoundTripConversion(
            Service.VALUE.value,
            b'<network xmlns="urn:valuexsd" version="1"><device version="1">'
            b'<value_set string="miau" timestamp="0" value_id="13"></value_set></device></network>'
        )

        self.assertRoundTripConversion(
            Service.VALUE.value,
            b'<network xmlns="urn:valuexsd" version="1"><device device_id="1" version="1">'
            b'<value_report string="wuff" timestamp="517276800" value_id="17"></value_report></device></network>'
        )

    def test_mixed_cases_string(self):
        self.assertRoundTripConversion(
            Service.VALUE.value,
            b'<network xmlns="urn:valuexsd" version="1"><device version="1">'
            b'<value_set string="MiXed CaSe" timestamp="0" value_id="13"></value_set></device></network>'
        )

        self.assertRoundTripConversion(
            Service.VALUE.value,
            b'<network xmlns="urn:valuexsd" version="1"><device device_id="1" version="1">'
            b'<value_report string="UpPer AnD lOwEr CasE" timestamp="517276800" value_id="17">'
            b'</value_report></device></network>'
        )

    def test_newline_and_tab_string(self):
        self.assertRoundTripConversion(
            Service.VALUE.value,
            b'<network xmlns="urn:valuexsd" version="1"><device version="1">'
            b'<value_set string="hallo\nhi\r\n:-)\n\rxx\tx" timestamp="0" value_id="13"></value_set></device></network>'
        )

        self.assertRoundTripConversion(
            Service.VALUE.value,
            b'<network xmlns="urn:valuexsd" version="1"><device device_id="1" version="1">'
            b'<value_report string="asdf\nyy\r\n:-D\n\rzz\tz" timestamp="517276800" value_id="17">'
            b'</value_report></device></network>'
        )

    def test_xml_entities_string(self):
        self.assertRoundTripConversion(
            Service.VALUE.value,
            b'<network xmlns="urn:valuexsd" version="1"><device version="1">'
            b'<value_set string="foo&quot;bar\'baz&amp;blubb" timestamp="0" value_id="13"></value_set></device>'
            b'</network>'
        )

        self.assertRoundTripConversion(
            Service.VALUE.value,
            b'<network xmlns="urn:valuexsd" version="1"><device device_id="1" version="1">'
            b'<value_report string="quux&quot;quuz\'quuuuz&amp;blubbber" timestamp="517276800" value_id="17">'
            b'</value_report></device></network>'
        )

    def test_multiple_values_per_report(self):
        self.assertRoundTripConversion(
            Service.VALUE.value,
            b'<network xmlns="urn:valuexsd" version="1"><device device_id="1" version="1">'
            b'<value_report number="23.25" timestamp="517276800" value_id="17"></value_report>'
            b'<value_report hexBinary="F000" timestamp="517276800" value_id="17"></value_report>'
            b'<value_report string="wuff" timestamp="517276800" value_id="17"></value_report>'
            b'</device></network>'
        )

    def test_parallel_stress(self):
        def run():
            t = threading.currentThread()
            try:
                while getattr(t, 'do_run', True):
                    self.assertRoundTripConversion(
                        Service.VALUE.value,
                        b'<network xmlns="urn:valuexsd" version="1"><device version="1">'
                        b'<value_set number="23.25" timestamp="0" value_id="13"></value_set></device></network>'
                    )
            except BaseException as e:
                t.exception = e

        thread = threading.Thread(target=run)
        thread.start()

        for i in range(20000):
            if not thread.is_alive():
                break
            self.assertRoundTripConversion(
                Service.VALUE.value,
                b'<network xmlns="urn:valuexsd" version="1"><device device_id="1" version="1">'
                b'<value_report number="42.0" timestamp="517276800" value_id="17"></value_report></device></network>'
            )

        thread.do_run = False
        thread.join()
        thread_exception = getattr(thread, 'exception', None)
        if thread_exception is not None:
            raise thread_exception
