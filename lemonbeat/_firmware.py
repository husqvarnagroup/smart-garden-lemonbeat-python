# SPDX-FileCopyrightText: GARDENA GmbH
#
# SPDX-License-Identifier: LGPL-2.0-or-later

# coding=utf-8

"""
A Firmware Mixin for the Device class.
"""
import enum
import logging
import math
import time
import warnings
import xml.etree.ElementTree as ETree
from random import random

from ._defines import DEFAULT_TIMEOUT
from ._service import Service
from ._types import RequestTimeoutError, MessageFormatError


@enum.unique
class FirmwareReportStatus(enum.IntEnum):
    OK = 1
    NOT_INITIALIZED = 2
    SIZE_TOO_BIG = 3
    CHECKSUM_ERROR_IN_RECEIVED_DATA = 4
    DATA_OVERFLOW = 5
    WRONG_OFFSET = 6
    CHUNK_SIZE_IS_TOO_BIG = 7
    DATA_IS_MISSING = 8
    CHUNK_SIZE_IS_TOO_SMALL = 9
    BLOCKED_BY_APPLICATION = 10

    def __repr__(self):
        return str(self)


class FirmwareMixin:
    """Firmware Mixin for the Device class."""

    def get_firmware_information_raw(self, timeout=DEFAULT_TIMEOUT):
        """Get firmware information from device."""
        warnings.warn(
            "get_firmware_information_raw is about to be deprecated, "
            "use get_firmware_information instead as soon it is implemented",
            PendingDeprecationWarning)
        return self._send_request(Service.FIRMWARE_UPDATE,
                                  [ETree.Element("firmware_information_get")],
                                  timeout=timeout)

    def update_firmware_init(self, firmware_size, firmware_checksum, timeout=DEFAULT_TIMEOUT,
                             go_to_sleep=300000, firmware_id=1):
        """Send firmware_init packet to device."""
        return self._send_request(Service.FIRMWARE_UPDATE,
                                  [ETree.Element("firmware_init",
                                                 size=str(firmware_size),
                                                 checksum="%04X" % firmware_checksum,
                                                 firmware_id="%d" % firmware_id)],
                                  go_to_sleep=go_to_sleep,
                                  timeout=timeout)

    def upload_firmware(self, firmware, chunk, delay=1, max_retries=10,
                        timeout=DEFAULT_TIMEOUT, go_to_sleep=300000, progress_callback=None):
        """Upload firmware to device."""
        firmware.seek(0, 2)
        firmware_size = firmware.tell()
        firmware.seek(0, 0)

        logging.info("Firmware Upgrade Initialized - %d bytes (%d) frames",
                     firmware_size,
                     math.ceil(firmware_size / chunk))
        repeat = 0
        while firmware.tell() < firmware_size:

            if progress_callback:
                progress_callback(firmware.tell(), firmware_size)

            # read data and pack it into xml structure
            current_offset = firmware.tell()
            firmware_data = ETree.Element("firmware_data", offset=str(current_offset))
            bin_chunk = firmware.read(chunk)
            chunk_xml = ETree.SubElement(firmware_data, "chunk")
            chunk_xml.text = bin_chunk.hex().upper()

            # send data, repeat max_retries per packet, if
            # something goes wrong
            ret = None
            while repeat <= max_retries:
                # sleep 'delay' + x (0 <= x <= 1) seconds to match regulators
                time.sleep(delay + random())
                try:
                    ret = self._send_request(Service.FIRMWARE_UPDATE,
                                             [firmware_data],
                                             go_to_sleep=go_to_sleep,
                                             timeout=timeout)
                except (RequestTimeoutError, MessageFormatError) as e:
                    logging.warning("[%d/%d] cannot send chunk: %d bytes, offset: %d",
                                    repeat,
                                    max_retries,
                                    len(bin_chunk),
                                    current_offset)
                    repeat += 1
                    if repeat > max_retries:
                        raise e
                    # lets repeat last packet
                    continue
                firmware_report = ret[0]
                status = int(firmware_report.get("status"))
                expected_offset = int(firmware_report.get("expected_offset"))

                if status == FirmwareReportStatus.OK:
                    # clear repeat counter, if it was possible to send packet
                    repeat = 0
                    break

                logging.warning("[%d/%d] cannot send chunk(%d): %s",
                                repeat, max_retries, status, FirmwareReportStatus(status))
                # Not Initialized
                if status == FirmwareReportStatus.NOT_INITIALIZED:
                    # TODO: we can resend init packet, but need checksum here
                    return None
                # 3 - Size is too big
                # 4 - Checksum Error in received data
                # 5 - Data Overflow
                # 8 - Data is missing
                if status in (
                        FirmwareReportStatus.SIZE_TOO_BIG,
                        FirmwareReportStatus.CHECKSUM_ERROR_IN_RECEIVED_DATA,
                        FirmwareReportStatus.DATA_OVERFLOW,
                        FirmwareReportStatus.DATA_IS_MISSING):
                    return None
                # 6 - Wrong offset
                if status == FirmwareReportStatus.WRONG_OFFSET:
                    logging.warning("current file offset: %d not match expected offset: %d => set offset to %d",
                                    current_offset, expected_offset, expected_offset)
                    firmware.seek(expected_offset, 0)
                    # we do not need to resend, we need to read new chunk here
                    # break internal while loop
                    repeat += 1
                    break
                # 7 - Chunk size is too big
                if status == FirmwareReportStatus.CHUNK_SIZE_IS_TOO_BIG:
                    # to prevent run with chunk = 0
                    if chunk > 1:
                        chunk = math.ceil(chunk / 2)
                        break
                    else:
                        return None
                # 9 - Chunk size is too small
                if status == 9:
                    if chunk > 0:
                        chunk = math.ceil(chunk * 1.5)
                    break
                # 10 - Firmware Package blocked by Application
                if status == FirmwareReportStatus.BLOCKED_BY_APPLICATION:
                    logging.warning(
                        "Chunk blocked by application. This may be temporary or "
                        "permanent (e.g. if battery is low). So try again")
                    repeat += 1
                continue

            if ret is None or repeat > max_retries:
                logging.error("Cannot send firmware update after %d retries", max_retries)
                return None

        if progress_callback:
            progress_callback(firmware.tell(), firmware_size)

        return True

    def flash_firmware(self, max_retries=3, timeout=30):
        """Start flashing previously uploaded firmware."""
        repeat = 1
        while repeat <= max_retries:
            try:
                ret = self._send_request(Service.FIRMWARE_UPDATE,
                                         [ETree.Element("firmware_update_start")],
                                         timeout=timeout)
            except (RequestTimeoutError, MessageFormatError) as e:
                logging.error("[%d/%d] cannot start firmware flashing", repeat, max_retries)
                repeat += 1
                # lets repeat last packet
                if repeat > max_retries:
                    raise e
                continue
            status = int(ret[0].get("status"))
            if status != FirmwareReportStatus.OK:
                logging.error("[%d/%d] cannot start firmware flashing(%d): %s",
                              repeat, max_retries, status, FirmwareReportStatus(status))
                repeat += 1
                continue
            # there are no errors, we should not resend
            return ret

        raise Exception('Cannot send firmware flash command')
