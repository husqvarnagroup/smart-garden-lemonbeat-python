# SPDX-FileCopyrightText: GARDENA GmbH
#
# SPDX-License-Identifier: LGPL-2.0-or-later

# coding=utf-8

"""Lemonbeat FirmwareMixin unit tests."""

import io
import logging
import unittest
import xml.etree.ElementTree as ETree
from unittest import mock

from crcmod.predefined import mkPredefinedCrcFun

from lemonbeat import Gateway, Service, Device, _firmware, RequestTimeoutError
from . import etree_compare


def _generate_firmware_report(status, expected_offset):
    xml = b'<firmware_report status="%d" expected_offset="%d" />' % (status, expected_offset)
    return ETree.fromstring(xml)


def _generate_firmware_data(offset, chunk_data):
    firmware_data = ETree.Element("firmware_data", offset=str(offset))
    chunk_xml = ETree.SubElement(firmware_data, "chunk")
    chunk_xml.text = chunk_data.hex().upper()
    return ETree.tostring(firmware_data)


class TestFirmware(unittest.TestCase):
    """Gateway unit tests."""

    @classmethod
    def setUpClass(cls):
        cls.gateway = Gateway(inclusion_message=None, bind_address=("fc00::6:1234:5678:9012", 0, 0, 42))
        cls.device = Device(cls.gateway, "fc00::6:9876:5432:1")

        cls.chunk_1 = b'12345'
        cls.chunk_2 = b'67890'
        cls.chunk_3 = b'abcd'
        cls.chunk_size = len(cls.chunk_1)
        cls.file = io.BytesIO(cls.chunk_1 + cls.chunk_2 + cls.chunk_3)
        cls.file_size = cls.file.getbuffer().nbytes
        cls.firmware_id = 1
        cls.firmware_crc16 = (mkPredefinedCrcFun('xmodem'))(cls.file.read())
        cls.firmware_report_first_chunk = [_generate_firmware_report(1, 5)]
        cls.firmware_report_second_chunk = [_generate_firmware_report(1, 10)]
        cls.firmware_report_last_chunk = [_generate_firmware_report(1, 14)]
        cls.firmware_data_expected = [_generate_firmware_data(0, cls.chunk_1),
                                      _generate_firmware_data(5, cls.chunk_2),
                                      _generate_firmware_data(10, cls.chunk_3)]
        cls.progress_callback_expected = [mock.call(0, 14),
                                          mock.call(5, 14),
                                          mock.call(10, 14),
                                          mock.call(14, 14)]

    def _check_progress_and_send_request_calls(self, mocked_progress_callbacks, mocked_calls, go_to_sleep_expected):
        progress_index = 0
        self.assertEqual(len(self.progress_callback_expected), len(mocked_progress_callbacks))
        for progress_expected in self.progress_callback_expected:
            self.assertEqual(mocked_progress_callbacks[progress_index], progress_expected)
            progress_index += 1

        index = 0
        for single_call in mocked_calls:
            self.assertEqual(single_call[1][0], Service.FIRMWARE_UPDATE.value)
            self.assertIn(ETree.tostring(single_call[1][1][0]), self.firmware_data_expected)
            self.assertEqual(go_to_sleep_expected[index], single_call[2].get('go_to_sleep'), "Index: %s" % index)
            self.assertEqual(10, single_call[2].get('timeout'))
            index += 1

    def _test_template_for_specific_error(self, status):
        with mock.patch('lemonbeat.Device._send_request') as mock_send_request:
            mock_send_request.side_effect = [
                self.firmware_report_first_chunk,
                [_generate_firmware_report(status, 5)],
                [_generate_firmware_report(status, 5)],
                [_generate_firmware_report(status, 5)],
                [_generate_firmware_report(status, 5)]
            ]

            mock_callback = mock.MagicMock()
            with self.assertLogs(level=logging.WARNING) as asserted_logs:
                ret = self.device.upload_firmware(self.file, self.chunk_size, delay=0, progress_callback=mock_callback,
                                                  timeout=10, max_retries=3)
                self.assertEqual(9, len(asserted_logs.output))
                # on error ret should be None
                self.assertIsNone(ret)

    def test_update_firmware_init(self):
        """Test update_firmware_init function."""
        with mock.patch('lemonbeat.Device._send_request') as mock_send_request:
            mock_send_request.return_value = [_generate_firmware_report(_firmware.FirmwareReportStatus.OK, 0)]
            firmware_init_call_expected = ETree.fromstring(
                b'<firmware_init checksum="%04X" firmware_id="%d" size="%d" />' %
                (self.firmware_crc16, self.firmware_id, self.file_size))
            ret = self.device.update_firmware_init(self.file_size, self.firmware_crc16, timeout=10,
                                                   firmware_id=self.firmware_id)
            self.assertTrue(etree_compare.eq(mock_send_request.return_value[0], ret[0]))
            self.assertEqual(1, len(mock_send_request.mock_calls))
            args = mock_send_request.mock_calls[0][1]
            self.assertEqual(args[0], Service.FIRMWARE_UPDATE.value)
            self.assertTrue(etree_compare.eq(args[1][0], firmware_init_call_expected))
            options = mock_send_request.mock_calls[0][2]
            self.assertEqual(10, options.get('timeout'))
            self.assertEqual(300000, options.get('go_to_sleep'))

    def test_firmware_flash(self):
        """Test flash_firmware function."""
        with mock.patch('lemonbeat.Device._send_request') as mock_send_request:
            mock_send_request.return_value = [_generate_firmware_report(_firmware.FirmwareReportStatus.OK, 0)]
            firmware_flash_call_expected = ETree.fromstring(b'<firmware_update_start />')
            ret = self.device.flash_firmware(max_retries=2, timeout=10)
            self.assertTrue(etree_compare.eq(mock_send_request.return_value[0], ret[0]))
            self.assertEqual(1, len(mock_send_request.mock_calls))
            args = mock_send_request.mock_calls[0][1]
            self.assertEqual(args[0], Service.FIRMWARE_UPDATE.value)
            self.assertTrue(etree_compare.eq(args[1][0], firmware_flash_call_expected))
            options = mock_send_request.mock_calls[0][2]
            self.assertEqual(10, options.get('timeout'))

    def test_firmware_flash_failed(self):
        """Test flash_firmware function."""
        with mock.patch('lemonbeat.Device._send_request') as mock_send_request:
            mock_send_request.side_effect = RequestTimeoutError
            firmware_flash_call_expected = ETree.fromstring(b'<firmware_update_start />')
            with self.assertLogs(level=logging.WARNING) as asserted_logs:
                with self.assertRaises(Exception):
                    self.device.flash_firmware(max_retries=2, timeout=10)
                self.assertEqual(2, len(asserted_logs.output))
            self.assertEqual(2, len(mock_send_request.mock_calls))
            for single_call in mock_send_request.mock_calls:
                args = single_call[1]
                self.assertEqual(args[0], Service.FIRMWARE_UPDATE.value)
                self.assertTrue(etree_compare.eq(args[1][0], firmware_flash_call_expected))
                options = mock_send_request.mock_calls[0][2]
                self.assertEqual(10, options.get('timeout'))

    def test_upload_firmware_successful(self):
        """Test upload_firmware function without errors."""
        with mock.patch('lemonbeat.Device._send_request') as mock_send_request:
            mock_send_request.side_effect = [self.firmware_report_first_chunk, self.firmware_report_second_chunk,
                                             self.firmware_report_last_chunk]
            # TODO: last go_to_sleep value should be small or 0
            go_to_sleep_expected = [300000, 300000, 300000]

            mock_callback = mock.MagicMock()
            with self.assertLogs(level=logging.INFO) as asserted_logs:
                ret = self.device.upload_firmware(self.file, self.chunk_size, delay=0, progress_callback=mock_callback,
                                                  timeout=10, max_retries=10)
                # on success ret should be true
                self.assertTrue(ret)
                self.assertEqual(1, len(asserted_logs.output))
            # check all calls to _send_request function
            self._check_progress_and_send_request_calls(mock_callback.call_args_list, mock_send_request.mock_calls,
                                                        go_to_sleep_expected)

    def test_upload_firmware_with_error_code_6(self):
        """Test upload_firmware function with error code 6.
            GW:                                         DEVICE:
        1) send first chunk: offset: 0, size: 5         response OK, expected_offset: 5
        2) send second chunk: offset: 5, size: 5        timeout, should be expected_offset: 10
        3) send second chunk again: offset: 5, size: 5  response WRONG_OFFSET, with offset: 10
        4) send third chunk: offset: 10, size: 4        response OK, expected offset: 14

        """
        with mock.patch('lemonbeat.Device._send_request') as mock_send_request:
            mock_send_request.side_effect = [
                self.firmware_report_first_chunk,
                RequestTimeoutError,
                [_generate_firmware_report(_firmware.FirmwareReportStatus.WRONG_OFFSET, 10)],
                self.firmware_report_last_chunk
            ]
            # TODO: last go_to_sleep value should be small or 0
            go_to_sleep_expected = [300000, 300000, 300000, 300000]

            mock_callback = mock.MagicMock()
            with self.assertLogs(level=logging.WARNING) as asserted_logs:
                ret = self.device.upload_firmware(self.file, self.chunk_size, delay=0, progress_callback=mock_callback,
                                                  timeout=10, max_retries=10)
                self.assertEqual(3, len(asserted_logs.output))
                # on success ret should be true
                self.assertTrue(ret)
            # there are fewer callback calls than send_socket_raws calls
            self._check_progress_and_send_request_calls(mock_callback.call_args_list, mock_send_request.mock_calls,
                                                        go_to_sleep_expected)

    def test_upload_firmware_with_error_code_10(self):
        """Test upload_firmware function with error code 10.
            GW:                                         DEVICE:
        1) send first chunk: offset: 0, size: 5         response OK, expected_offset: 5
        2) send second chunk: offset: 5, size: 5        response BLOCKED_BY_APPLICATION, with offset: 5
        3) send second chunk again offset: 5, size: 5   response OK, expected_offset: 10
        4) send third chunk: offset: 10, size: 4        response OK, expected offset: 14

        """
        with mock.patch('lemonbeat.Device._send_request') as mock_send_request:
            mock_send_request.side_effect = [
                self.firmware_report_first_chunk,
                [_generate_firmware_report(_firmware.FirmwareReportStatus.BLOCKED_BY_APPLICATION, 5)],
                self.firmware_report_second_chunk,
                self.firmware_report_last_chunk
            ]
            # TODO: last go_to_sleep value should be small or 0
            go_to_sleep_expected = [300000, 300000, 300000, 300000]

            mock_callback = mock.MagicMock()
            with self.assertLogs(level=logging.WARNING) as asserted_logs:
                ret = self.device.upload_firmware(self.file, self.chunk_size, delay=0, progress_callback=mock_callback,
                                                  timeout=10, max_retries=10)
                self.assertEqual(2, len(asserted_logs.output))
                # on success ret should be true
                self.assertTrue(ret)
            # there are fewer callback calls than send_socket_raws calls
            self._check_progress_and_send_request_calls(mock_callback.call_args_list, mock_send_request.mock_calls,
                                                        go_to_sleep_expected)

    def test_upload_firmware_max_retries_counter_with_error_10(self):
        self._test_template_for_specific_error(_firmware.FirmwareReportStatus.BLOCKED_BY_APPLICATION)

    def test_upload_firmware_max_retries_counter_with_error_6(self):
        self._test_template_for_specific_error(_firmware.FirmwareReportStatus.WRONG_OFFSET)

    def test_upload_firmware_max_retries_counter_with_lost_connection(self):
        with mock.patch('lemonbeat.Device._send_request') as mock_send_request:
            mock_send_request.side_effect = [
                self.firmware_report_first_chunk,
                RequestTimeoutError,
                RequestTimeoutError,
                RequestTimeoutError,
                RequestTimeoutError
            ]

            mock_callback = mock.MagicMock()
            with self.assertLogs(level=logging.WARNING) as asserted_logs:
                with self.assertRaises(RequestTimeoutError):
                    self.device.upload_firmware(self.file, self.chunk_size, delay=0, progress_callback=mock_callback,
                                                timeout=10, max_retries=3)
                self.assertEqual(4, len(asserted_logs.output))

    def test_upload_firmware_repeat_counter_per_packet(self):
        with mock.patch('lemonbeat.Device._send_request') as mock_send_request:
            mock_send_request.side_effect = [
                self.firmware_report_first_chunk,
                RequestTimeoutError,
                self.firmware_report_second_chunk,
                RequestTimeoutError,
                self.firmware_report_last_chunk
            ]
            go_to_sleep_expected = [300000, 300000, 300000, 300000, 300000]

            mock_callback = mock.MagicMock()
            with self.assertLogs(level=logging.WARNING) as asserted_logs:
                ret = self.device.upload_firmware(self.file, self.chunk_size, delay=0, progress_callback=mock_callback,
                                                  timeout=10, max_retries=1)
                self.assertEqual(2, len(asserted_logs.output))
                # on error ret should be None
                self.assertTrue(ret)
                # there are fewer callback calls than send_socket_raws calls
                self._check_progress_and_send_request_calls(mock_callback.call_args_list, mock_send_request.mock_calls,
                                                            go_to_sleep_expected)
