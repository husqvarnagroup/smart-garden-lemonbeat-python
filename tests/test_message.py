# SPDX-FileCopyrightText: GARDENA GmbH
#
# SPDX-License-Identifier: LGPL-2.0-or-later

# coding=utf-8

"""Lemonbeat Message unit tests."""

import logging
import socket
import unittest
import xml.etree.ElementTree as ETree
from unittest.mock import Mock

from lemonbeat import Gateway, Service, Device, _message, lsdl_serializer


class TestMessage(unittest.TestCase):
    """Message unit tests."""

    def setUp(self):
        self.raw_firmware_update_init = (
            b'<network version="1" xmlns="urn:firmware_updatexsd"><device go_to_sleep="300000" version="1">'
            b'<firmware_init checksum="0315" firmware_id="1" size="123456" /></device></network>'
        )
        self.exi_firmware_update_init = lsdl_serializer.compress(Service.FIRMWARE_UPDATE, self.raw_firmware_update_init)

        self.raw_firmware_update_init_report = (
            b'<network version="1" xmlns="urn:firmware_updatexsd"><device version="1">'
            b'<firmware_report status="1" expected_offset="0" /></device></network>'
        )

        self.gateway = Gateway(inclusion_message=None, bind_address=("fc00::6:1234:5678:9012", 0, 0, 42))
        self.device = Device(self.gateway, "fc00::6:9876:5432:1")

    def test_send(self):
        """Test _send function."""
        mock_select = Mock()
        mock_socket = Mock()
        mock_socket.return_value.__enter__ = Mock()
        mock_socket.return_value.__exit__ = Mock()
        self.gateway.select.select = mock_select
        self.gateway.socket.socket = mock_socket
        mock_ancdata = [(socket.IPPROTO_IPV6, socket.IPV6_TCLASS, (0x1c,))]
        mock_socket.return_value.__enter__.return_value.recvmsg.return_value = (
            lsdl_serializer.compress(Service.FIRMWARE_UPDATE, self.raw_firmware_update_init_report), mock_ancdata, 0,
            (self.device.address, Service.FIRMWARE_UPDATE.value, 0, 0))
        ret = self.device.update_firmware_init(123456, 789, timeout=3)[0]
        mock_socket.assert_called_once_with(socket.AF_INET6, socket.SOCK_DGRAM | socket.SOCK_NONBLOCK)
        mock_socket.return_value.__enter__.assert_called_once()
        mock_socket.return_value.__enter__.return_value.bind.assert_called_once_with((self.gateway.address, 0, 0, 42))
        mock_socket.return_value.__enter__.return_value.sendto.assert_called_once_with(
            self.exi_firmware_update_init,
            (self.device.address, Service.FIRMWARE_UPDATE.value))
        mock_socket.return_value.__exit__.assert_called_once()
        status = int(ret.get("status"))
        expected_offset = int(ret.get("expected_offset"))
        self.assertEqual(0, expected_offset)
        self.assertEqual(1, status)
        mock_select.assert_called_once_with((mock_socket.return_value.__enter__.return_value.fileno(),), (), (), 3)

    def test_pretty(self):
        """Test _pretty function."""
        # Different Python versions order attributes differently, so testing with only one attribute per tag.
        self.assertEqual(
            '<?xml version="1.0" ?>\n'
            '<network xmlns="urn:firmware_updatexsd">\n'
            '    <device device_id="1">\n'
            '        <firmware_report status="1"/>\n'
            '    </device>\n'
            '</network>\n',
            _message._pretty(
                '<?xml version="1.0" ?><network xmlns="urn:firmware_updatexsd">'
                '<device device_id="1"><firmware_report status="1"/></device></network>'
            ))

    def test_etree_eq(self):
        xml_firmware_update_init_report = ETree.fromstring(b'<firmware_report status="1" expected_offset="0" />')
        xml_firmware_update_init_report_diff = ETree.fromstring(b'<firmware_report status="6" expected_offset="0" />')

        self.assertTrue(_message._etree_eq(xml_firmware_update_init_report, xml_firmware_update_init_report))
        self.assertFalse(_message._etree_eq(xml_firmware_update_init_report, xml_firmware_update_init_report_diff))

    def test_verify_conversion(self):
        raw_firmware_update_init_report_diff = (
            b'<network version="1" xmlns="urn:firmware_updatexsd"><device version="1">'
            b'<firmware_report status="6" expected_offset="0" /></device></network>'
        )
        exi_firmware_update_init_report_diff = lsdl_serializer.compress(Service.FIRMWARE_UPDATE,
                                                                        raw_firmware_update_init_report_diff)

        with self.assertLogs(level=logging.WARNING) as asserted_logs:
            _message._verify_conversion(self.exi_firmware_update_init,
                                        Service.FIRMWARE_UPDATE.value,
                                        self.raw_firmware_update_init)
            self.assertEqual(0, len(asserted_logs.output))
            _message._verify_conversion(self.exi_firmware_update_init, Service.FIRMWARE_UPDATE.value,
                                        raw_firmware_update_init_report_diff)
            self.assertEqual(1, len(asserted_logs.output))
            _message._verify_conversion(exi_firmware_update_init_report_diff,
                                        Service.FIRMWARE_UPDATE.value,
                                        self.raw_firmware_update_init_report)
            self.assertEqual(2, len(asserted_logs.output))
