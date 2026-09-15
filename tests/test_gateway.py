# SPDX-FileCopyrightText: GARDENA GmbH
#
# SPDX-License-Identifier: LGPL-2.0-or-later

# coding=utf-8

"""Lemonbeat Gateway unit tests."""

import logging
import unittest
from unittest.mock import mock_open, patch, Mock

from lemonbeat import Gateway, Service


class PropertyMock(Mock):
    def __get__(self, instance, owner):
        return self()


class TestGateway(unittest.TestCase):
    """Gateway unit tests."""

    def setUp(self):
        self.test_gateway = Gateway(inclusion_message=None, bind_address=("fc00::6:1234:5678:9012", 0, 0, 42))

    def test_get_ipv6_addr(self):
        """Test _interface_bind_address function."""
        proc_net_if_inet6_content_mock = "2a02016820740042deae2a95adc8beaf 03 40 00 00   wlp4s0\n" \
                                         "fe8000000000000040c01524f3cb130c 03 40 20 80   wlp4s0\n" \
                                         "00000000000000000000000000000001 01 80 10 80       lo\n" \
                                         "2a020168207400423e5214c81bcde174 0e 40 00 00     ppp0\n" \
                                         "fe8000000000000001061861c7003616 0e 0a 20 80     ppp0\n" \
                                         "fe8000000000000056ee75fffeadf619 02 40 20 80 enp0s31f6\n"

        fake_file_path = '/proc/net/if_inet6'

        with patch('builtins.open',
                   new=mock_open(read_data=proc_net_if_inet6_content_mock)) as mocked_open:
            gw = Gateway()
            result = gw.bind_address
            mocked_open.assert_called_once_with(fake_file_path)

            self.assertRaises(IOError, lambda: Gateway(interface="ppp1").address)

        expected = ("fe80::106:1861:c700:3616", 0, 0, 14)
        self.assertEqual(expected, result)

    def test_gateway_default_constructor(self):
        """Test Gateway constructor."""
        expected_addr = "fc00::6:1234:5678:9012"
        prop_mock = PropertyMock()
        prop_mock.return_value = ("fc00::6:1234:5678:9012", 0, 0, 42)
        with patch.object(Gateway, '_interface_bind_address', prop_mock):
            gateway = Gateway()
            self.assertEqual(expected_addr, gateway.address)

            # no inclusion message specified, exception should be thrown
            self.assertRaises(Exception, gateway.include)

    def test_gateway_with_address_constructor(self):
        """Test Gateway constructor arguments."""
        prop_mock = PropertyMock()
        prop_mock.return_value = ("fc00::6:1234:5678:9012", 0, 0, 42)
        with patch.object(Gateway, '_interface_bind_address', prop_mock):
            gateway = Gateway(address="fc00::6:1234:5678:9012", inclusion_message="abcd")
        self.assertEqual("ABCD", gateway.inclusion_message)
        self.assertEqual("fc00::6:1234:5678:9012", gateway.address)

    def test_service_listeners_property(self):
        """Test service_listeners property."""
        self.test_gateway.start_service_listener(Service.VALUE, handler=lambda: None)
        self.test_gateway.start_service_listener(Service.DEVICE_DESCRIPTION, handler=lambda: None)
        self.assertEqual({Service.VALUE, Service.DEVICE_DESCRIPTION}, set(self.test_gateway.service_listeners))
        # tear down single test to prevent "address already in use"
        self.test_gateway.stop_service_listener()
        self.assertFalse(self.test_gateway.service_listeners)

    def test_start_service_listener(self):
        """Test warning on multiple starts of single service."""
        self.test_gateway.start_service_listener(Service.VALUE, handler=lambda: None)
        with self.assertLogs(level=logging.WARNING) as asserted_logs:
            self.test_gateway.start_service_listener(Service.VALUE, handler=lambda: None)
            expected_warning = \
                "WARNING:root:service listener already running at [::]:%d" % Service.VALUE.value
            self.assertEqual(expected_warning, asserted_logs.output[0])
        self.assertEqual({Service.VALUE}, set(self.test_gateway.service_listeners))
        self.test_gateway.stop_service_listener(Service.VALUE)
        self.assertFalse(self.test_gateway.service_listeners)
