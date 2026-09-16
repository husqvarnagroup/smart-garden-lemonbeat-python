# coding=utf-8

# Copyright 2022 Gardena GmbH
# Adrian Friedli <adrian.friedli@husqvarnagroup.com>
#
# SPDX-License-Identifier: LGPL-2.0-or-later

"""
Helper functions for the GARDENA smart mowers.
"""

__version__ = "0.1.0"

__all__ = [
    "is_mower",
    "DecodedApplicationStatus",
    "decode_status_report",
    "unpack_timestamp",
    "unpack_date",
    "pack_date",
    "Task",
    "unpack_schedule",
    "pack_schedule",
    "ScheduleState",
    "ScheduleStateEnum",
    "unpack_schedule_states",
    "pack_schedule_states",
    "ScheduleStateControlSkip",
    "pack_schedule_states_control_skip",
    "unpack_schedule_states_control_skip",
    "ScheduleStateControlShorten",
    "unpack_schedule_states_control_shorten",
    "pack_schedule_states_control_shorten",
    "StartingPoint",
    "unpack_starting_points",
    "pack_starting_points",
    "Position",
    "unpack_position",
    "unpack_lona_mcu_fw_version",
    "DataDownload",
    "unpack_data_download",
    "DataDownloadInt",
    "unpack_data_download_int",
    "pack_data_download_int",
    "Settings",
    "SensorControlEnum",
    "SecurityLevelEnum",
    "unpack_settings",
    "pack_settings_control",
    "unpack_lona_control",
    "pack_lona_control",
    "LonaStatus",
    "HeadingSourceEnum",
    "unpack_lona_status",
    "DecodedValue",
    "decode_value_report",
    "html_format_value_report",
]

import datetime
import enum
import struct
from collections import namedtuple
from decimal import Decimal
from functools import reduce
from operator import or_

from lemonbeat import Hex, DeviceDescriptionType, Status

MOWER_DEVICE_TYPES = [3, 9, 10]  # CBT2, CBTG, CBTL


class MappingIntEnum(enum.IntEnum):
    @classmethod
    def basic_from_id(cls, id_):
        """Map ID to a basic type. If mapping succeeds return a string, else convert to int."""
        id_ = int(id_)
        try:
            return cls(id_).name
        except ValueError:
            return id_


def is_mower(device_description):
    return device_description[DeviceDescriptionType.DEVICE_TYPE] in MOWER_DEVICE_TYPES


_STATUS_LONA_ERROR_DATA_CODE_NAMES = {
    1: 'ZONEIMPORTER_NO_RT_MAP',
    2: 'ZONEIMPORTER_ZONES_FILE_OPEN_STAT_ERROR',
    3: 'ZONEIMPORTER_ZONES_TOO_LARGE',
    4: 'ZONEIMPORTER_ZONES_FILE_OPEN_ERROR',
    5: 'ZONEIMPORTER_ZONES_FILE_READ_ERROR',
    6: 'ZONEIMPORTER_ZONES_FILE_HEADER_ERROR',
    7: 'ZONEIMPORTER_ZONES_FB_INVALID',
    8: 'ZONEIMPORTER_NO_ZONES',
    9: 'ZONEIMPORTER_POLYGON_ERROR',
    10: 'ZONEIMPORTER_INVALID_CS_STAY_IN',
    11: 'ZONEIMPORTER_TOO_MANY_STARTING_POINTS',
    12: 'ZONEIMPORTER_INVALID_STAY_IN_IDX',
    13: 'ZONEIMPORTER_INVALID_RT_MAP',
}


def _decode_status_data_uninitialized_value_requested(status, value_description):
    data_code = int.from_bytes(status.data, 'big')
    vd = value_description.get(data_code)
    if vd is not None:
        return vd['name']
    else:
        return status.data


def _decode_status_data_lona_error(status, value_description):
    data_code = int.from_bytes(status.data, 'big')
    return _STATUS_LONA_ERROR_DATA_CODE_NAMES.get(data_code, status.data)


DecodedApplicationStatus = namedtuple('DecodedApplicationStatus', ['code', 'level', 'data'])
_STATUS_APPLICATION_CODE_NAMES = {
    0: 'OK',
    1: 'BROWN_OUT_RESET',
    2: 'WATCHDOG_RESET',
    3: 'SOFT_RESET',
    6: 'SLEEP_MODE_ERROR',
    7: 'SLEEP_MODE_TIMEOUT',
    8: 'EEPROM_ERROR',
    9: 'INTERNAL_COMMUNICATION_ERROR',
    10: 'UNINITIALIZED_VALUE_REQUESTED',
    18: 'EEPROM_TIMEOUT',
    22: 'ADC_BROKEN',
    23: 'ADC_INVOKE_TIMEOUT',
    32: 'SECONDARY_MCU_FW_VERSION_PARSE_ERROR',
    40: 'CUSTOM_HEX_VALUE_ERROR',
    41: 'SCHEDULE_CONFIG_ERROR',
    43: 'VALUE_REPORTING_QUEUE_FULL',
    44: 'COMMUNICATION_BUSY',
    45: 'VALUE_REPORTING_SEND_ERROR',
    51: 'SETTINGS_FAIL',
    52: 'INITIALIZATION_TIMEOUT',
    53: 'VALUE_OVERFLOW',
    54: 'INTERNAL_ERROR_QUEUE_FULL',
    55: 'FOTA_COMMON_TRIGGER_ERROR',
    56: 'FOTA_DATA_DOWNLOAD_INT_ERROR',
    57: 'FOTA_FILE_HANDLING_ERROR',
    58: 'FOTA_RENAME_UPDATE_FILE_ERROR',
    59: 'FOTA_LONA_MCU_FLASHING_FAILED',
    60: 'EXTERNAL_FLASH_ERASE_FAILED',
    63: 'LONA_ERROR',
}

_DECODE_STATUS_DATA_FUNCTIONS = {
    10: _decode_status_data_uninitialized_value_requested,
    63: _decode_status_data_lona_error,
}


def _decode_status(status, value_description):
    if status.type_id != Status.Type.APPLICATION:
        return status

    code = _STATUS_APPLICATION_CODE_NAMES.get(status.code, status.code)
    decode_data_fn = _DECODE_STATUS_DATA_FUNCTIONS.get(status.code)
    if decode_data_fn is not None:
        data = decode_data_fn(status, value_description)
    else:
        data = status.data

    return DecodedApplicationStatus(code, status.level, data)


def decode_status_report(status_report, value_description):
    return [_decode_status(s, value_description) for s in status_report]


def unpack_timestamp(hex_timestamp):
    if len(hex_timestamp) == 0:
        return None
    return datetime.datetime.utcfromtimestamp(struct.unpack('>I', hex_timestamp)[0])


def unpack_date(hex_date):
    if len(hex_date) == 0:
        return None
    return datetime.datetime(*struct.unpack('<HBBBB', hex_date))


def pack_date(date_time):
    return Hex(struct.pack('<HBBBB', *date_time.timetuple()[:5]))


Task = namedtuple('Task', ['id', 'weekdays', 'start', 'duration', 'a_id'])


def _parse_task(t):
    return Task(t[0], f"{t[1]:07b}", datetime.time(*t[2:4]), datetime.timedelta(minutes=t[4]), t[5])


def _pack_task(t):
    return Hex(struct.pack('<BBBBHB', t.id, int(t.weekdays, base=2), t.start.hour, t.start.minute,
                           int(t.duration / datetime.timedelta(minutes=1)), t.a_id))


def unpack_schedule(schedule):
    # Uninitialized value is special value 0xFF.
    if schedule == b'\xff':
        return None
    return [_parse_task(v) for v in struct.iter_unpack('<BBBBHB', schedule)]


def pack_schedule(schedule):
    return Hex(b''.join([_pack_task(t) for t in schedule]))


ScheduleState = namedtuple('ScheduleState', ['id', 'state', 'update'])


@enum.unique
class ScheduleStateEnum(MappingIntEnum):
    idle = 0
    scheduled = 1
    will_start = 2
    skipped = 3
    shorten_duration = 4
    running = 5
    stopped = 6
    error = 7
    overwritten = 8
    done = 9
    will_continue = 10


def _parse_schedule_state(sst):
    return ScheduleState(sst[0], ScheduleStateEnum.basic_from_id(int(ord(sst[1]))), sst[2])


def _pack_schedule_state(sst):
    return Hex(struct.pack('<BBB', sst.id, int(sst.state), sst.update))


def unpack_schedule_states(schedule_states):
    if len(schedule_states) == 0:
        return None
    return [_parse_schedule_state(v) for v in struct.iter_unpack('<Bs?', schedule_states)]


def pack_schedule_states(schedule_states):
    return Hex(b''.join([_pack_schedule_state(t) for t in schedule_states]))


ScheduleStateControlSkip = namedtuple('ScheduleStateControlSkip', ['id'])


def _parse_schedule_state_control_skip(sstcsk):
    return ScheduleStateControlSkip(sstcsk[0])


def _pack_schedule_state_control_skip(sstcsk):
    return Hex(struct.pack('<B', sstcsk.id))


def unpack_schedule_states_control_skip(schedule_states_control_skip):
    if len(schedule_states_control_skip) == 0:
        return None
    return [_parse_schedule_state_control_skip(v) for v in struct.iter_unpack('<B', schedule_states_control_skip)]


def pack_schedule_states_control_skip(schedule_states_control_skip):
    return Hex(b''.join([_pack_schedule_state_control_skip(t) for t in schedule_states_control_skip]))


ScheduleStateControlShorten = namedtuple('ScheduleStateControlShorten', ['id', 'duration'])


def _parse_schedule_state_control_shorten(sstcsh):
    return ScheduleStateControlShorten(sstcsh[0], datetime.timedelta(minutes=sstcsh[1]))


def _pack_schedule_state_control_shorten(sstcsh):
    return Hex(struct.pack('<BH', sstcsh.id, int(sstcsh.duration / datetime.timedelta(minutes=1))))


def unpack_schedule_states_control_shorten(schedule_states_control_shorten):
    if len(schedule_states_control_shorten) == 0:
        return None
    return [_parse_schedule_state_control_shorten(v) for v in
            struct.iter_unpack('<BH', schedule_states_control_shorten)]


def pack_schedule_states_control_shorten(schedule_states_control_shorten):
    return Hex(b''.join([_pack_schedule_state_control_shorten(t) for t in schedule_states_control_shorten]))


StartingPoint = namedtuple('StartingPoint', ['loop_wire', 'distance', 'proportion', 'enabled', 'corridor_cut'])


def _parse_starting_point(sp):
    cc = None
    if len(sp) == 5:
        cc = bool(sp[4])
    return StartingPoint(*sp[:3], bool(sp[3]), cc)


def _pack_starting_point(sp):
    data = Hex(struct.pack('<BHBBB', *sp[:4], bool(sp[4])))
    if sp[4] is None:
        data = data[:5]
    return data


def unpack_starting_points(starting_points):
    if len(starting_points) == 0:
        return None
    fmt = '<BHBB'
    if len(starting_points) % 6 == 0:
        fmt += 'B'
    return [_parse_starting_point(v) for v in struct.iter_unpack(fmt, starting_points)]


def pack_starting_points(starting_points):
    return Hex(b''.join([_pack_starting_point(sp) for sp in starting_points]))


Position = namedtuple('Position', [
    'gnssLatitude',
    'gnssLongitude',
    'gnssHorizontalAccuracy',
    'realTimeLatitude',
    'realTimeLongitude',
    'realTimeHeading',
    'realTimeIsReady',
    'compassHeading',
    'compassIsCalibrated',
])


def unpack_position(buf):
    if len(buf) == 0:
        return None
    elif len(buf) == 25:
        raw = Position(*struct.unpack(">2iI2ih?h", buf), None)
    elif len(buf) == 26:
        raw = Position(*struct.unpack(">2iI2ih?h?", buf))
    else:
        raise ValueError(f"Invalid position buffer length {len(buf)}.")
    return Position(
        Decimal(raw.gnssLatitude) / Decimal(10000000),
        Decimal(raw.gnssLongitude) / Decimal(10000000),
        Decimal(raw.gnssHorizontalAccuracy) / Decimal(1000),
        Decimal(raw.realTimeLatitude) / Decimal(10000000),
        Decimal(raw.realTimeLongitude) / Decimal(10000000),
        Decimal(raw.realTimeHeading) / Decimal(10),
        raw.realTimeIsReady,
        Decimal(raw.compassHeading) / Decimal(10),
        raw.compassIsCalibrated,
    )


def unpack_lona_mcu_fw_version(buf):
    if len(buf) == 0:
        return None
    major, minor, patch, dev, git = struct.unpack('BBB?4s', buf)
    if dev:
        gits = git.hex()[:7]
        dirty = bool(git[3] & 0x0f)
        devs = f"-dev-g{gits}{'-dirty' if dirty else ''}"
    else:
        devs = ''
    return f"{major}.{minor}.{patch}{devs}"


DataDownload = namedtuple('DataDownload', [
    'slot_number',
    'content_tag',
    'size',
    'checksum',
    'status',
])


def _unpack_data_download(slot_number, content_tag, size, checksum, status):
    return DataDownload(slot_number, Hex(content_tag), size, Hex(checksum), status)


def unpack_data_download(buf):
    if len(buf) == 0:
        return None
    return [_unpack_data_download(*v) for v in struct.iter_unpack(">I4sI2sB", buf)]


DataDownloadInt = namedtuple('DataDownloadInt', [
    'slot_number',
    'content_tag',
])


def unpack_data_download_int(buf):
    if len(buf) == 0:
        return None
    slot_number, content_tag = struct.unpack(">I4s", buf)
    return DataDownloadInt(slot_number, Hex(content_tag))


def pack_data_download_int(data_download_int):
    return Hex(struct.pack(">I4s", *data_download_int))


Settings = namedtuple('Settings', [
    'starting_distance',
    'drive_past_wire',
    'sensor_control',
    'mower_house',
    'security_level',
    'eco_mode',
    'frost',
    'zone_generator',
], defaults=(None,) * 8)


@enum.unique
class SensorControlEnum(MappingIntEnum):
    disabled = 0
    reserved_1 = 1
    low_cutting_time = 2
    medium = 3
    high_cutting_time = 4
    reserved_5 = 5


@enum.unique
class SecurityLevelEnum(MappingIntEnum):
    low = 3
    medium = 7
    high = 63


def unpack_settings(buf):
    if len(buf) == 0:
        return None
    mask_format = ">HBBBBBB"
    raw_format = ">HBB?B??"
    if len(buf) >= 18:
        mask_format += "B"
        raw_format += "?"
    mask = Settings(*struct.unpack(mask_format, buf[:len(buf) // 2]))
    raw = Settings(*struct.unpack(raw_format, buf[len(buf) // 2:]))
    return Settings(
        raw.starting_distance if mask.starting_distance == 0xffff else None,
        raw.drive_past_wire if mask.drive_past_wire == 0xff else None,
        SensorControlEnum.basic_from_id(raw.sensor_control) if mask.sensor_control == 0xff else None,
        raw.mower_house if mask.mower_house == 0xff else None,
        SecurityLevelEnum.basic_from_id(raw.security_level) if mask.security_level == 0xff else None,
        raw.eco_mode if mask.eco_mode == 0xff else None,
        raw.frost if mask.frost == 0xff else None,
        raw.zone_generator if mask.zone_generator == 0xff else None,
    )


def pack_settings_control(settings):
    """Encode settings to Hex.

    :param settings: Settings named tuple with unchanged values set to None
    :return: Hex object of length 16

    Values which shouldn't be changed can be set to None in the settings
    parameter, the mask in the returned Hex object will be set
    accordingly. For simplicity the named tuple Settings has a
    default value of None for unset values.

    Example for setting only two values and leaving the rest unchanged:
    ```
    pack_settings_control(Settings(starting_distance=42, sensor_control='medium'))
    ```
    """
    mask = [0xffff if settings[0] is not None else 0]
    mask += [0xff if x is not None else 0 for x in settings[1:]]
    settings = [x if x is not None else 0 for x in settings]
    if isinstance(settings[2], str):
        settings[2] = SensorControlEnum.__members__[settings[2]]
    if isinstance(settings[4], str):
        settings[4] = SecurityLevelEnum.__members__[settings[4]]
    return Hex(struct.pack(">HBBBBBBBHBB?B???", *(mask + settings)))


LonaControl = namedtuple('LonaControl', [
    'global_enable',
    'data_collection',
    'debug_events',
    'debug_data_collection',
    'sensor_position_mapping',
])


def unpack_lona_control(buf):
    if type(buf) is float:
        return int(buf)
    if len(buf) == 0:
        return None
    buf = bytes(8 - len(buf)) + buf
    flags = struct.unpack(">7xB", buf)[0]
    return LonaControl(*[bool(flags & (1 << i)) for i in range(5)])


def pack_lona_control(lona_control):
    flags = reduce(or_, [1 << i for i, v in enumerate(lona_control) if v], 0)
    return Hex(struct.pack(">7xB", flags))


LonaStatus = namedtuple('LonaStatus', [
    'last_lona_error_code',
    'active_zones',
    'active_map',
    # LONA state
    'rt_position_ready',
    'zones_active',
    'heading_source',
    'stay_in_ignored',
    # Sensor state
    'gnss_ready',
    'imu_ready',
    'compass_ready',
    'wheels_sensor_ready',
    'loop_sensor_ready',
])


@enum.unique
class LonaErrorCodeEnum(MappingIntEnum):
    no_error = 0
    lonanavigator_trapped_in_zone = 1
    unused_2 = 2
    lonanavigator_no_local_position = 3
    lonanavigator_outside_working_area_not_ready = 4
    lonanavigator_outside_working_area_stop_following = 5


@enum.unique
class HeadingSourceEnum(MappingIntEnum):
    compass = 0
    gnss = 1


def unpack_lona_status(buf):
    if len(buf) == 0:
        return None
    raw = struct.unpack(">xB4s4sBB", buf)
    return LonaStatus(
        LonaErrorCodeEnum.basic_from_id(raw[0]),
        Hex(raw[1]),
        Hex(raw[2]),
        *[bool(raw[3] & (1 << i)) for i in range(2)],
        HeadingSourceEnum.basic_from_id((raw[3] >> 2) & 1),
        bool(raw[3] & (1 << 3)),
        *[bool(raw[4] & (1 << i)) for i in range(5)],
    )


DecodedValue = namedtuple('DecodedValue', ['value_id', 'name', 'value', 'timestamp'])
_DECODE_VALUE_FUNCTIONS = {
    'timestamp_next_start': unpack_timestamp,
    'action_paused_until_1': unpack_date,
    'schedule_config': unpack_schedule,
    'starting_points': unpack_starting_points,
    'timestamp_last_error_code': unpack_timestamp,
    # legacy CBT2 only
    'override_end_time': unpack_timestamp,
    # LONA
    'position': unpack_position,
    'lona_mcu_fw_version': unpack_lona_mcu_fw_version,
    'lona_mcu_boot_fw_version': unpack_lona_mcu_fw_version,
    'data_download': unpack_data_download,
    'data_download_int': unpack_data_download_int,
    'settings_control': unpack_settings,
    'settings_report': unpack_settings,
    'lona_control': unpack_lona_control,
    'lona_status': unpack_lona_status,
    # TSS
    'schedule_state': unpack_schedule_states,
    'schedule_state_control_skip': unpack_schedule_states_control_skip,
    'schedule_state_control_shorten': unpack_schedule_states_control_shorten,
}


def _decode_value(value, value_description):
    vd = value_description.get(value.value_id)
    name = None if vd is None else vd['name']

    def default_decode(x):
        if vd is None:
            return x
        try:
            return vd['type'](x)
        except ValueError:
            # NaN cannot be converted to int
            return x

    decoded_value = _DECODE_VALUE_FUNCTIONS.get(name, default_decode)(value.value)
    return DecodedValue(value_id=value.value_id, name=name, value=decoded_value, timestamp=value.timestamp)


def decode_value_report(value_report, value_description):
    return [_decode_value(v, value_description) for v in value_report]


def html_format_value_report(decoded_value_report):
    html = '<table><tr><th>Value ID</th><th>Value Name</th><th style="text-align:left">Value</th></tr>'
    value_style = 'style="text-align:left; font-family:monospace; font-size:small;"'

    for value in decoded_value_report:
        if value.name in ['schedule_config', 'starting_points'] and value.value is not None:
            rowspan = f'rowspan="{len(value.value) + 2}"'
            html += f'<tr><td {rowspan}>{value.value_id}</td><td {rowspan}>{value.name}</td></tr><tr></tr>'
            for vi in value.value:
                html += f'<tr><td {value_style}>{vi!r}</td></tr>'
        else:
            html += f'<tr><td>{value.value_id}</td><td>{value.name}</td><td {value_style}>{value.value!r}</td></tr>'

    html += '</table>'
    return html
