#!/usr/bin/env python3
# coding: utf-8
#
# Copyright 2018 Gardena GmbH
# Andrej Gessel <andrej.gessel@husqvarnagrouop.com> 2018
# SPDX-License-Identifier: LGPL-2.0-or-later

"""
Helper script to update Firmware on Lemonbeat device.
"""

import argparse
import atexit
import logging
import os
import struct
import subprocess
import time
from collections import namedtuple

from crcmod.predefined import mkPredefinedCrcFun

from lemonbeat import Gateway, Device, RequestTimeoutError, MessageFormatError, FirmwareReportStatus, Hex

# Script exit codes
OK = 0
GENERIC_ERROR = 1  # placeholder for Shadoway, uncaught exceptions return with error code '1'
ARGUMENT_ERROR = 2  # argparse.py can also exit with 2
CRC_MISMATCH = 3
PARTNER_REGISTRATION_ERROR = 4
GATEWAY_CANNOT_WAKEUP_DEVICE = 5
CANNOT_PING_DEVICE = 6
CANNOT_START_UPLOAD = 7
CANNOT_UPLOAD_FILE = 8
DATA_DOWNLOAD_INT_ERROR = 9
CANNOT_FLASH_FIRMWARE = 10
DEVICE_TIMEOUT_ERROR = 11
OS_ERROR = 12
INITIALIZED_ONLY = 13  # placeholder for Shadoway

# Retries
MAX_TRIES = 10

# IP Addresses naming
# linux module  <- radio module     -> sensor/actor
# local_ip      <- radio_module_ip  -> remote_device_ip
INTERFACE = "ppp0"
TIMEOUT = 30
MAX_FW_ID = 0xffffffff

DataDownloadInt = namedtuple('DataDownloadInt', [
    'slot_number',
    'content_tag',
])


def retry(function, max_tries=MAX_TRIES, args=None, kwargs=None):
    if args is None:
        args = ()
    if kwargs is None:
        kwargs = {}
    for attempt in range(1, max_tries + 1):
        try:
            return function(*args, **kwargs)
        except (RequestTimeoutError, MessageFormatError) as e:
            if attempt == max_tries:
                logging.error("Operation failed or timed out.")
                raise e
            logging.error("Operation failed or timed out, retrying (%d/%d).", attempt, max_tries)


def _pack_data_download_int(data_download_int):
    return Hex(struct.pack(">I4s", *data_download_int))


def _unpack_data_download_int(buf):
    if len(buf) == 0:
        return None
    try:
        slot_number, content_tag = struct.unpack(">I4s", buf)
    except struct.error as e:
        logging.warning(e)
        return None
    return DataDownloadInt(slot_number, Hex(content_tag))


def report_progress_to_file(device, filename, done, total):
    """Report the firmware uploading progress to a file read by Shadoway."""
    progress = done / total * 100

    # Report progress only at 0%, 100% and in 2% steps between
    if progress not in (0, 100) and progress - report_progress_to_file.reported < 2:
        return
    filename_tmp = filename + '.tmp'
    try:
        with open(filename_tmp, 'w') as status_file:
            status_file.write('GATEWAY_progress\n%s\n%d\n' % (device.address, progress))
        os.rename(filename_tmp, filename)
    except OSError as exception:
        logging.error("Could not write to file '%s': %s", filename, str(exception))
        return
    report_progress_to_file.reported = progress


report_progress_to_file.reported = 0


def main():  # pylint: disable=too-many-statements,too-many-branches

    """Main entry point."""
    parser = argparse.ArgumentParser()
    parser.add_argument('-device',
                        help="IPv6 Address of remote device that will be updated.",
                        dest='remote_device_ip',
                        required=True)
    parser.add_argument('-file',
                        type=argparse.FileType('rb'),
                        required=True,
                        help="Path to firmware file.")
    parser.add_argument('-chunk',
                        type=int,
                        default=256,
                        dest='chunk_size',
                        help="Chunk size, firmware will be split into.")
    parser.add_argument('-converter',
                        help="")
    parser.add_argument('-stayAwake',
                        type=int,
                        default=300000,
                        dest="stay_awake",
                        help="Time device will be awake.")
    parser.add_argument('-tcp',
                        action='store_true',
                        help="for compatibility only.")
    parser.add_argument('-generate',
                        action='store_true',
                        help="Generate <firmware>.checksum file.")
    parser.add_argument('-provide-crc',
                        type=str,
                        dest="provided_crc",
                        help="Provide CRC in Hex. Internally calculated CRC16 is ignored. Still checked against <firmware>.checksum file")
    parser.add_argument('-silent',
                        action='store_true',
                        help="Do not print.")
    parser.add_argument('-delay',
                        type=int,
                        help="Delay between messages.",
                        default=1)
    parser.add_argument('-rssi',
                        type=float,
                        help="Link quality of the target device. (deprecated)")
    parser.add_argument('-wakeup',
                        action='store_true',
                        help="Wakeup device before updating.")
    parser.add_argument('-noping',
                        action='store_true',
                        help="Do not ping device before updating.")
    parser.add_argument('-statusListen',
                        action='store_true',
                        dest='status_listen',
                        help="Listen for status when waking device up.")
    parser.add_argument('-flash',
                        action='store_true',
                        help="Flash firmware to device after upload.")
    parser.add_argument('-pid-file',
                        type=str,
                        help="Write a PID file.")
    parser.add_argument('-progress-file',
                        type=str,
                        help="Write progress to file.")
    parser.add_argument('-firmware-id',
                        type=int,
                        default=1,
                        help="Firmware ID for the current upload.")
    parser.add_argument('-content-tag',
                        type=str,
                        default='00000000',
                        help="Identifier for file content. 32-Bit Hex value.")
    args = parser.parse_args()

    if args.pid_file is not None:
        try:
            # Keep file open during runtime
            pid_file = open(args.pid_file, 'wt')
            atexit.register(os.unlink, args.pid_file)
            pid_file.write(str(os.getpid()))
            pid_file.flush()
        except OSError:
            logging.error("%s could not be created, exiting", args.pid_file)
            exit(OS_ERROR)

    if not args.silent:
        logging.basicConfig(level=logging.DEBUG)

    logging.debug("Program args: %s", args)

    if args.rssi:
        logging.warning("-rssi argument is deprecated. Value will not be used.")

    if args.tcp:
        logging.warning("TCP is not supported, UDP is used")

    if args.status_listen:
        logging.warning("-statusListen is not supported yet")

    if args.converter:
        logging.warning("-converter argument is ignored, library will used instead.")

    if args.stay_awake < 0:
        logging.error("-stayAwake cannot be negative")
        exit(ARGUMENT_ERROR)

    if not (0 <= args.firmware_id <= MAX_FW_ID):
        logging.error("Allowed range for firmwareID is 0 <= id <= %d" % MAX_FW_ID)
        exit(ARGUMENT_ERROR)

    if len(args.content_tag) != 8:
        logging.error("Content-tag must be of length 8.")
        exit(ARGUMENT_ERROR)
    content_tag = None
    try:
        content_tag = Hex(args.content_tag)
    except Exception:
        logging.error("Could not parse Content-tag as Hex.")
        exit(ARGUMENT_ERROR)

    # gw should already be included
    gateway = Gateway(inclusion_message=None, interface=INTERFACE)

    # device should already be included
    device = Device(gateway, args.remote_device_ip)

    firmware = args.file.read()
    firmware_crc16 = (mkPredefinedCrcFun('xmodem'))(firmware)

    checksum_filename = "%s.checksum" % args.file.name
    if args.provided_crc is not None:
        logging.debug("use provided CRC: %x", args.provided_crc)
        firmware_crc = int(args.provided_crc, 16)
    else:
        logging.debug("use default CRC16: %x", firmware_crc16)
        firmware_crc = firmware_crc16

    if args.generate or (not os.path.isfile(checksum_filename)):
        logging.debug("firmware_crc generated/provided: %x", firmware_crc)
        with open(checksum_filename, 'w') as file_checksum:
            file_checksum.write("%x" % firmware_crc)
    else:
        with open(checksum_filename, "r") as file_checksum:
            firmware_crc_check = int(file_checksum.read(), 16)
        logging.debug("firmware_crc read: %x", firmware_crc_check)
        if firmware_crc != firmware_crc_check:
            logging.error("CRC mismatch, CRC of %s: %s, CRC from %s: %s",
                          args.file.name, firmware_crc, checksum_filename, firmware_crc_check)
            exit(CRC_MISMATCH)

    # wakeup works only, if partner_information for device exists in dongle
    if args.wakeup:
        logging.info("Waking up device...")
        try:
            partner_id = gateway.get_partner_id(device.address)
            if partner_id is None:
                logging.warning("Cannot get partner id, try to register new one")
                partner_id = gateway.register_partner(device.address)
                if partner_id is None:
                    logging.error("Cannot register new partner")
                    exit(PARTNER_REGISTRATION_ERROR)
            gateway.wakeup_partner(partner_id=partner_id)
            # TODO: check why device not wake up fast
        except (RequestTimeoutError, MessageFormatError):
            logging.error("Cannot wake up device, Gateway error.")
            exit(GATEWAY_CANNOT_WAKEUP_DEVICE)
        time.sleep(3)

    if not args.noping:
        ping = subprocess.Popen(["ping6", "-I", INTERFACE, "-c", "1", args.remote_device_ip],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        ping.communicate()
        if ping.returncode != 0:
            logging.error("Failed to PING device (%s)", args.remote_device_ip)
            logging.debug("Ping args: %s", ping.args)
            exit(CANNOT_PING_DEVICE)

    file_size = os.fstat(args.file.fileno()).st_size

    if args.firmware_id >= 257:
        try:
            device_value_description = retry(device.get_value_description)
            for vid, v in device_value_description.items():
                if v['name'] == 'data_download_int':
                    logging.info("Set Extra Data")
                    value = DataDownloadInt(args.firmware_id, content_tag)
                    for attempt in range(1, MAX_TRIES + 1):
                        device.set_value(value_id=vid, value=_pack_data_download_int(value))
                        value_ret = _unpack_data_download_int(
                            retry(device.get_value, kwargs={"value_id": vid})[0].value)
                        if value_ret == value:
                            break
                        if attempt == MAX_TRIES:
                            logging.error("Setting value data_download_int failed.")
                            exit(DATA_DOWNLOAD_INT_ERROR)
                        logging.error("Setting value data_download_int failed, retrying (%d/%d).", attempt, MAX_TRIES)
                    break
            else:
                logging.warning("Could not set extra data. 'data_download_int' not in value description.")
        except RequestTimeoutError:
            logging.error("Setting value data_download_int timed out.")
            exit(DEVICE_TIMEOUT_ERROR)
        except MessageFormatError:
            logging.error("Setting value data_download_int failed.")
            exit(DATA_DOWNLOAD_INT_ERROR)

    ret = None
    try:
        ret = retry(device.update_firmware_init, args=(file_size, firmware_crc),
                    kwargs={"timeout": TIMEOUT, "go_to_sleep": args.stay_awake, "firmware_id": args.firmware_id})
    except RequestTimeoutError:
        logging.error("Starting firmware upload timed out: %s", device.address)
        exit(DEVICE_TIMEOUT_ERROR)
    except MessageFormatError:
        logging.error("Cannot start firmware upload: %s", device.address)
        exit(CANNOT_START_UPLOAD)

    status = int(ret[0].attrib['status'])
    if status != FirmwareReportStatus.OK:
        logging.error("Cannot start firmware upload. Status %s: %s", FirmwareReportStatus(status).name, device.address)
        exit(CANNOT_START_UPLOAD)
    elif int(ret[0].attrib['expected_offset']) == file_size:
        # Special case for LONA firmware and data download. If device return an offset equal file size the file already
        # exists, and we can skip downloading the entire firmware and issue flash cmd right away.
        logging.info("File already exists: %s", device.address)
    else:
        logging.info("Start uploading firmware to device: %s", device.address)

        ret = None
        try:
            if args.progress_file is not None:
                ret = device.upload_firmware(args.file, args.chunk_size, delay=args.delay, timeout=TIMEOUT,
                                             progress_callback=lambda progress, total:
                                             report_progress_to_file(device, args.progress_file, progress, total))
            else:
                ret = device.upload_firmware(args.file, args.chunk_size, delay=args.delay, timeout=TIMEOUT)
        except RequestTimeoutError:
            logging.error("Uploading timed out: %s", device.address)
            exit(DEVICE_TIMEOUT_ERROR)
        except MessageFormatError:
            logging.error("Cannot upload firmware to device: %s", device.address)
            exit(CANNOT_UPLOAD_FILE)

        if ret is None:
            logging.error("Cannot upload firmware to device: %s", device.address)
            exit(CANNOT_UPLOAD_FILE)

    # Firmware flashing is normally done by shadoway binary
    # add -flash argument to allow testing
    if args.flash:
        logging.info("Start flashing firmware to device: %s", device.address)
        try:
            device.flash_firmware()
        except RequestTimeoutError:
            logging.error("Flashing timed out: %s", device.address)
            exit(DEVICE_TIMEOUT_ERROR)
        except MessageFormatError:
            logging.error("Cannot flash firmware on device: %s", device.address)
            exit(CANNOT_FLASH_FIRMWARE)


if __name__ == "__main__":
    main()
