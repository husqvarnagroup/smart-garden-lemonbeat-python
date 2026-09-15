# SPDX-FileCopyrightText: GARDENA GmbH
#
# SPDX-License-Identifier: LGPL-2.0-or-later

# coding=utf-8

"""
Lemonbeat status enums.
"""

import enum
import logging

from ._types import BaseElement


class StatusEnum(enum.IntEnum):
    def __repr__(self):
        return "Status." + str(self)


class StatusCodeEnum(enum.IntEnum):
    def __repr__(self):
        return "Status.Code." + str(self)


class Status:
    @enum.unique
    class Type(StatusEnum):
        """Enum for status types.

        Taken from 'Table 2.52: Status type' in LsDL spec. v. 1.13.
        """
        PUBLIC_KEY = 1
        MEMORY_INFORMATION = 2
        DEVICE_DESCRIPTION = 3
        VALUE_DESCRIPTION = 4
        VALUE = 5
        PARTNER_INFORMATION = 6
        ACTION = 7
        CALCULATION = 8
        TIMER = 9
        CALENDAR = 10
        STATE_MACHINE = 11
        FIRMWARE_UPDATE = 12
        CONFIGURATION = 13
        EXI = 100
        SYSTEM = 101
        APPLICATION = 200

        @classmethod
        def from_id(cls, id_):
            try:
                return cls(id_)
            except ValueError:
                logging.warning("Unknown status type %d", id_)
                return id_

    @enum.unique
    class Level(StatusEnum):
        """Enum for status levels.

        Taken from 'Table 2.53: Status level' in LsDL spec. v. 1.13.
        """
        DISABLED = 0
        FATAL = 1
        ERROR = 2
        WARNING = 3
        INFO = 4
        DEBUG = 5

        @classmethod
        def from_id(cls, id_):
            try:
                return cls(id_)
            except ValueError:
                logging.warning("Unknown status level %d", id_)
                return id_

    class Code:
        @enum.unique
        class DeviceDescription(StatusCodeEnum):
            """Enum for status codes.

            Taken from 'Table 2.54: Status device description code' in LsDL spec. v. 1.13.
            """
            SET_WRONG_ID = 11
            WRONG_SIZE_OF_CHANNEL_MAP = 12
            MISSING_SYNCHRONIZATION_CHANNELS = 13

        @enum.unique
        class ValueDescription(StatusCodeEnum):
            """Enum for status codes.

            Taken from 'Table 2.55: Status value description code' in LsDL spec. v. 1.13.
            """
            GET_WRONG_ID = 1
            SET_WRONG_ID = 2
            DELETE_WRONG_ID = 3
            NOT_SUPPORTED = 11
            INVALID_STEP = 12

        @enum.unique
        class Value(StatusCodeEnum):
            """Enum for status codes.

            Taken from 'Table 2.56: Status value code' in LsDL spec. v. 1.13.
            """
            GET_WRONG_ID = 1
            SET_WRONG_ID = 2
            CHECK_WRONG_ID = 11
            VALUE_INVALID = 12
            WRONG_DATA_TYPE = 13
            INVALID_STEP = 14
            CANNOT_READ_WRITE_ONLY = 15
            CANNOT_WRITE_READ_ONLY = 16

        @enum.unique
        class PartnerInformation(StatusCodeEnum):
            """Enum for status codes.

            Taken from 'Table 2.57: Status partner information code' in LsDL spec. v. 1.13.
            """
            GET_WRONG_ID = 1
            SET_WRONG_ID = 2
            DELETE_WRONG_ID = 3
            WRONG_ID = 11
            FAILED_TO_SEND_TO_PARTNER = 12
            SET_WRONG_TYPE = 13
            GROUP_IN_GROUP_NOT_ALLOWED = 14
            TOO_MANY_PARTNERS_IN_GROUP = 15

        @enum.unique
        class FirmwareUpdate(StatusCodeEnum):
            """Enum for status codes.

            Taken from 'Table 2.63: Status firmware update code' in LsDL spec. v. 1.13.
            """
            FAILED_TO_UPGRADE = 11

        @enum.unique
        class Configuration(StatusCodeEnum):
            """Enum for status codes.

            Taken from 'Table 2.64: Status configuration code' in LsDL spec. v. 1.13.
            """
            TIMEOUT = 11
            INVALID = 12
            STARTED = 13

        @enum.unique
        class System(StatusCodeEnum):
            """Enum for status codes.

            Taken from 'Table 2.65: Status system code' in LsDL spec. v. 1.13.
            """
            NO_NTP = 11
            AWAKE = 12
            HARDWARE_FAIL_DATAFLASH = 20


Status.Code.ENUMS = {
    Status.Type.DEVICE_DESCRIPTION: Status.Code.DeviceDescription,
    Status.Type.VALUE_DESCRIPTION: Status.Code.ValueDescription,
    Status.Type.VALUE: Status.Code.Value,
    Status.Type.PARTNER_INFORMATION: Status.Code.PartnerInformation,
    Status.Type.FIRMWARE_UPDATE: Status.Code.FirmwareUpdate,
    Status.Type.CONFIGURATION: Status.Code.Configuration,
    Status.Type.SYSTEM: Status.Code.System,
}


class ReportStatus(BaseElement):
    """Object used for report_status."""
    _tag = "status_report"
    _int_attributes = ("type_id", "code", "level")
    _hex_attribute = "data"

    def __init__(self, *, type_id, code, level, data=None):
        type_id = Status.Type.from_id(type_id)
        level = Status.Level.from_id(level)
        try:
            code_mapper = Status.Code.ENUMS[type_id]
        except KeyError:
            pass
        else:
            try:
                code = code_mapper(code)
            except ValueError:
                logging.warning("Unknown status code %d for status type %d", code, type_id)

        super().__init__(type_id=type_id, code=code, level=level, data=data)


def _parse_status(etree):
    return [ReportStatus.frometree(s) for s in etree]
