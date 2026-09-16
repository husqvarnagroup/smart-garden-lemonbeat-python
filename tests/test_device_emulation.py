# SPDX-FileCopyrightText: GARDENA GmbH
#
# SPDX-License-Identifier: LGPL-2.0-or-later

import copy
from unittest import mock
from xml.etree import ElementTree as ETree

import pytest

from lemonbeat import DeviceDescriptionType, Hex, ValueMode, Service, Device, ReportValue
from lemonbeat._device_emulation_types import ReportDeviceDescription, ReportServiceDescription, \
    ReportMemoryInformation, ReportPartnerInformation, SetPartnerInformation, ReportValueDescription, FirmwareData
from lemonbeat.device_emulation import DeviceEmulation, RadioModuleEmulation


def assert_etree_equal(first, second):
    assert first.tag == second.tag

    text_first = "" if first.text is None else first.text.strip()
    text_second = "" if second.text is None else second.text.strip()
    assert text_first == text_second

    tail_first = "" if first.tail is None else first.tail.strip()
    tail_second = "" if second.tail is None else second.tail.strip()
    assert tail_first == tail_second

    assert first.attrib == second.attrib
    assert len(first) == len(second)

    for child_first, child_second in zip(first, second):
        assert_etree_equal(child_first, child_second)


def strip_etree(etree):
    if etree.text is not None:
        etree.text = etree.text.strip()
    if etree.tail is not None:
        etree.tail = etree.tail.strip()
    for et in etree:
        strip_etree(et)


def patch_send_message(mock_device: DeviceEmulation):
    msm = mock.Mock()
    mock_device._send_message = msm

    def assert_sent_message_once(service, etrees, sock_addr):
        assert msm.call_count == 1
        assert msm.call_args[0][0] == service
        assert len(msm.call_args[0][1]) == len(etrees)
        for actual, expected in zip(msm.call_args[0][1], etrees):
            assert_etree_equal(actual, expected)
        assert msm.call_args[0][2] == sock_addr
        assert msm.call_args[1] == {}

    mock_device.assert_sent_message_once = assert_sent_message_once


@pytest.fixture
def mock_rm():
    dd = {
        DeviceDescriptionType.SGTIN: Hex('3034f8ee90155b400000a6fd'),
        DeviceDescriptionType.MAC_ADDRESS: Hex('94bbae033fe4'),
    }
    mock_device = RadioModuleEmulation(address=None, controller_address=None, device_description=dd)
    mock_device.partner_information = {
        1: {
            DeviceDescriptionType.RADIO_MODE: 0,
            DeviceDescriptionType.CHANNEL_MAP: Hex('10080804'),
            DeviceDescriptionType.IPV6_ADDRESS: Hex('fe80000000000000010694bbae033fe4'),
            DeviceDescriptionType.UNDOCUMENTED_22: 0,
            DeviceDescriptionType.UNDOCUMENTED_23: 0,
            DeviceDescriptionType.UNDOCUMENTED_24: 0,
        },
        2: {
            DeviceDescriptionType.RADIO_MODE: 0,
            DeviceDescriptionType.CHANNEL_MAP: Hex('10080804'),
            DeviceDescriptionType.IPV6_ADDRESS: Hex('fc0000000000000000062aeae10f4b36'),
            DeviceDescriptionType.UNDOCUMENTED_22: 0,
            DeviceDescriptionType.UNDOCUMENTED_23: 0,
            DeviceDescriptionType.UNDOCUMENTED_24: 0,
        },
    }

    patch_send_message(mock_device)

    return mock_device


@pytest.fixture
def mock_mower():
    dd = {
        DeviceDescriptionType.DEVICE_TYPE: 10,
        DeviceDescriptionType.SGTIN: Hex('00000000000000003f33841c'),
        DeviceDescriptionType.MAC_ADDRESS: Hex('2f453f33841c'),
        DeviceDescriptionType.APPLICATION_VERSION: '0.2.3',
        DeviceDescriptionType.NAME: 'SG Mower LONA MOCK',
        DeviceDescriptionType.DIVERSITY_MODE: 1,
    }
    vd = {
        1: {'mode': ValueMode.R, 'name': 'battery_level', 'persistent': False, 'type_id': 17, 'max': 100, 'min': 0,
            'step': 1, 'unit': '%', 'type': int},
        2: {'mode': ValueMode.R, 'name': 'rf_link_quality', 'persistent': False, 'type_id': 17, 'max': 100, 'min': 0,
            'step': 1, 'unit': '%', 'type': int},
        3: {'mode': ValueMode.R, 'name': 'manual_operation', 'persistent': False, 'type_id': 17, 'max': 1, 'min': 0,
            'step': 1, 'unit': '', 'type': int},
        4: {'mode': ValueMode.R, 'name': 'status', 'persistent': False, 'type_id': 17, 'max': 18, 'min': 0, 'step': 1,
            'unit': '', 'type': int},
        5: {'mode': ValueMode.R, 'name': 'timestamp_next_start', 'persistent': False, 'type_id': 17, 'max_length': 4,
            'type': Hex},
        6: {'mode': ValueMode.R, 'name': 'source_for_next_start', 'persistent': False, 'type_id': 17, 'max': 5,
            'min': 0, 'step': 1, 'unit': '', 'type': int},
        7: {'mode': ValueMode.RW, 'name': 'command', 'persistent': False, 'type_id': 17, 'max': 42, 'min': 0, 'step': 1,
            'unit': '', 'type': int},
        8: {'mode': ValueMode.RW, 'name': 'mower_timer', 'persistent': False, 'type_id': 17, 'max': 16777216,
            'min': -16777215, 'step': 1, 'unit': 's', 'type': int},
        9: {'mode': ValueMode.RW, 'name': 'action_paused_until_1', 'persistent': True, 'type_id': 17, 'max_length': 6,
            'type': Hex},
        10: {'mode': ValueMode.RW, 'name': 'start_delay_ms', 'persistent': True, 'type_id': 17, 'max': 59999, 'min': 0,
             'step': 1, 'unit': 'ms', 'type': int},
        11: {'mode': ValueMode.RW, 'name': 'schedule_config', 'persistent': False, 'type_id': 17, 'max_length': 98,
             'type': Hex},
        12: {'mode': ValueMode.R, 'name': 'mmi_version', 'persistent': False, 'type_id': 17, 'max_length': 10,
             'type': str},
        13: {'mode': ValueMode.R, 'name': 'mainboard_version', 'persistent': False, 'type_id': 17, 'max_length': 10,
             'type': str},
        14: {'mode': ValueMode.R, 'name': 'device_type', 'persistent': False, 'type_id': 17, 'max_length': 4,
             'type': str},
        15: {'mode': ValueMode.R, 'name': 'device_variant', 'persistent': False, 'type_id': 17, 'max_length': 4,
             'type': str},
        16: {'mode': ValueMode.R, 'name': 'running_time', 'persistent': False, 'type_id': 17, 'max': 65535, 'min': 0,
             'step': 1, 'unit': '', 'type': int},
        17: {'mode': ValueMode.R, 'name': 'cutting_time', 'persistent': False, 'type_id': 17, 'max': 65535, 'min': 0,
             'step': 1, 'unit': '', 'type': int},
        18: {'mode': ValueMode.R, 'name': 'charging_cycles', 'persistent': False, 'type_id': 17, 'max': 65535, 'min': 0,
             'step': 1, 'unit': '', 'type': int},
        19: {'mode': ValueMode.R, 'name': 'collisions', 'persistent': False, 'type_id': 17, 'max': 65535, 'min': 0,
             'step': 1, 'unit': '', 'type': int},
        20: {'mode': ValueMode.R, 'name': 'last_error_code', 'persistent': False, 'type_id': 17, 'max': 65535, 'min': 0,
             'step': 1, 'unit': '', 'type': int},
        21: {'mode': ValueMode.R, 'name': 'timestamp_last_error_code', 'persistent': False, 'type_id': 17,
             'max_length': 4, 'type': Hex},
        22: {'mode': ValueMode.RW, 'name': 'starting_points', 'persistent': False, 'type_id': 17, 'max_length': 18,
             'type': Hex},
        23: {'mode': ValueMode.R, 'name': 'supported_wires', 'persistent': False, 'type_id': 17, 'max': 255, 'min': 0,
             'step': 1, 'unit': '', 'type': int},
        24: {'mode': ValueMode.R, 'name': 'supported_starting_points', 'persistent': False, 'type_id': 17, 'max': 3,
             'min': 1, 'step': 1, 'unit': '', 'type': int},
        25: {'mode': ValueMode.R, 'name': 'serial_number', 'persistent': False, 'type_id': 17, 'max_length': 10,
             'type': str},
        26: {'mode': ValueMode.R, 'name': 'internal_connection_state', 'persistent': False, 'type_id': 17, 'max': 5,
             'min': 0, 'step': 1, 'unit': '', 'type': int},
        27: {'mode': ValueMode.R, 'name': 'onboard_temperature', 'persistent': False, 'type_id': 17, 'max': 225.0,
             'min': -50.0, 'step': 0.100000001, 'unit': '°C', 'type': float},
        28: {'mode': ValueMode.RW, 'name': 'settings_control', 'persistent': False, 'type_id': 17, 'max_length': 32,
             'type': Hex},
        29: {'mode': ValueMode.R, 'name': 'settings_report', 'persistent': False, 'type_id': 17, 'max_length': 16,
             'type': Hex},
        30: {'mode': ValueMode.R, 'name': 'position', 'persistent': False, 'type_id': 17, 'max_length': 25,
             'type': Hex},
        31: {'mode': ValueMode.R, 'name': 'gnss', 'persistent': False, 'type_id': 17, 'max_length': 31, 'type': Hex},
        32: {'mode': ValueMode.RW, 'name': 'position_timer', 'persistent': False, 'type_id': 17, 'max': 3600, 'min': 0,
             'step': 1, 'unit': 's', 'type': int},
        33: {'mode': ValueMode.RW, 'name': 'position_update_interval', 'persistent': True, 'type_id': 17,
             'max': 3600000, 'min': 1, 'step': 1, 'unit': 'ms', 'type': int},
        34: {'mode': ValueMode.RW, 'name': 'stop_and_turn', 'persistent': False, 'type_id': 17, 'max': 180, 'min': -180,
             'step': 1, 'unit': 'deg', 'type': int},
        35: {'mode': ValueMode.RW, 'name': 'lona_control', 'persistent': True, 'type_id': 17, 'max': 1, 'min': 0,
             'step': 1, 'unit': '', 'type': int},
        36: {'mode': ValueMode.R, 'name': 'lona', 'persistent': False, 'type_id': 17, 'max_length': 512, 'type': Hex},
        37: {'mode': ValueMode.R, 'name': 'lona_mcu_fw_version', 'persistent': False, 'type_id': 17, 'max_length': 8,
             'type': Hex},
        38: {'mode': ValueMode.R, 'name': 'lona_mcu_boot_fw_version', 'persistent': False, 'type_id': 17,
             'max_length': 8, 'type': Hex},
        39: {'mode': ValueMode.R, 'name': 'data_download', 'persistent': False, 'type_id': 17, 'max_length': 105,
             'type': Hex},
        40: {'mode': ValueMode.RW, 'name': 'data_download_int', 'persistent': False, 'type_id': 17, 'max_length': 8,
             'type': Hex},
    }
    mock_device = DeviceEmulation(address=None, controller_address=None, device_description=dd, value_description=vd)
    mock_device.partner_information = {
        1: {
            DeviceDescriptionType.RADIO_MODE: 0,
            DeviceDescriptionType.CHANNEL_MAP: Hex('10080804'),
            DeviceDescriptionType.IPV6_ADDRESS: Hex('fc000000000000000006010000000000'),
            DeviceDescriptionType.UNDOCUMENTED_22: 71,
            DeviceDescriptionType.UNDOCUMENTED_23: 32,
            DeviceDescriptionType.UNDOCUMENTED_24: 1596613111,
        },
    }

    patch_send_message(mock_device)

    return mock_device


@pytest.fixture
def mower_client(mock_mower):
    def add_ns_prefix(service, etrees):
        ns_prefix = f"{{{service.xmlns}}}"
        for e in etrees:
            if not e.tag.startswith(ns_prefix):
                e.tag = ns_prefix + e.tag

    def send_message(service, etrees):
        add_ns_prefix(service, etrees)
        mock_mower.service_handler_map[service](None, [etrees])

    def send_request(service, etrees):
        add_ns_prefix(service, etrees)
        sock_addr = object()
        msm = mock_mower._send_message
        assert isinstance(msm, mock.Mock)
        old_call_count = msm.call_count
        mock_mower.service_handler_map[service](sock_addr, [etrees])
        assert msm.call_count == old_call_count + 1
        assert msm.call_args[0][0] == service
        assert msm.call_args[0][2] == sock_addr
        assert msm.call_args[1] == {}
        return msm.call_args[0][1]

    mower_client = Device(None, None)
    mower_client._send_message = send_message
    mower_client._send_request = send_request
    return mower_client


@pytest.fixture
def rm_partner_info_et():
    xml = """
        <partner_information_report>
            <partner partner_id="1">
                <info type_id="13" number="0"/>
                <info type_id="17" hex="10080804"/>
                <info type_id="19" hex="FE80000000000000010694BBAE033FE4"/>
                <info type_id="22" number="0"/>
                <info type_id="23" number="0"/>
                <info type_id="24" number="0"/>
            </partner>
            <partner partner_id="2">
                <info type_id="13" number="0"/>
                <info type_id="17" hex="10080804"/>
                <info type_id="19" hex="FC0000000000000000062AEAE10F4B36"/>
                <info type_id="22" number="0"/>
                <info type_id="23" number="0"/>
                <info type_id="24" number="0"/>
            </partner>
        </partner_information_report>
    """
    et = ETree.fromstring(xml)
    strip_etree(et)
    return et


# noinspection DuplicatedCode
def test_rm_device_description_report(mock_rm):
    rm_dd_et = ETree.Element("device_description_report")
    #             <!-- Type -->
    rm_dd_et.append(ETree.Element("info", type_id="1", number="1"))
    #             <!-- Manufacturer -->
    rm_dd_et.append(ETree.Element("info", type_id="2", number="2"))
    #             <!-- Sgtin -->
    rm_dd_et.append(ETree.Element("info", type_id="3", hex="3034F8EE90155B400000A6FD"))
    #             <!-- Mac Address -->
    rm_dd_et.append(ETree.Element("info", type_id="4", hex="94BBAE033FE4"))
    #             <!-- Hardware Version -->
    rm_dd_et.append(ETree.Element("info", type_id="5", string="1"))
    #             <!-- Bootloader Version -->
    rm_dd_et.append(ETree.Element("info", type_id="6", string="4.1.0"))
    #             <!-- Stack Version -->
    rm_dd_et.append(ETree.Element("info", type_id="7", string="1.5.3"))
    #             <!-- Application Version -->
    rm_dd_et.append(ETree.Element("info", type_id="8", string="1.5.3"))
    #             <!-- Protocol -->
    rm_dd_et.append(ETree.Element("info", type_id="9", number="1"))
    #             <!-- Product -->
    rm_dd_et.append(ETree.Element("info", type_id="10", number="1"))
    #             <!-- Included -->
    rm_dd_et.append(ETree.Element("info", type_id="11", number="0"))
    #             <!-- Name -->
    rm_dd_et.append(ETree.Element("info", type_id="12", string="DONGLE"))
    #             <!-- Radio Mode -->
    rm_dd_et.append(ETree.Element("info", type_id="13", number="0"))
    #             <!-- Wakeup Interval -->
    rm_dd_et.append(ETree.Element("info", type_id="14", number="0"))
    #             <!-- Wakeup Offset -->
    rm_dd_et.append(ETree.Element("info", type_id="15", number="0"))
    #             <!-- Wakeup Channel -->
    rm_dd_et.append(ETree.Element("info", type_id="16", number="3"))
    #             <!-- Channel Map -->
    rm_dd_et.append(ETree.Element("info", type_id="17", hex="10080804"))
    #             <!-- Channel Scan Time -->
    rm_dd_et.append(ETree.Element("info", type_id="18", number="10000"))
    #             <!-- TX Power -->
    rm_dd_et.append(ETree.Element("info", type_id="27", number="14"))

    rm_dd = ReportDeviceDescription(mock_rm.device_description)
    assert ETree.tostring(rm_dd.toetree()) == ETree.tostring(rm_dd_et)


# noinspection DuplicatedCode
def test_mower_device_description_report(mock_mower):
    mower_dd_et = ETree.Element("device_description_report")
    #             <!-- Type -->
    mower_dd_et.append(ETree.Element("info", type_id="1", number="10"))
    #             <!-- Manufacturer -->
    mower_dd_et.append(ETree.Element("info", type_id="2", number="3"))
    #             <!-- Sgtin -->
    mower_dd_et.append(ETree.Element("info", type_id="3", hex="00000000000000003F33841C"))
    #             <!-- Mac Address -->
    mower_dd_et.append(ETree.Element("info", type_id="4", hex="2F453F33841C"))
    #             <!-- Hardware Version -->
    mower_dd_et.append(ETree.Element("info", type_id="5", string="1.0.0"))
    #             <!-- Bootloader Version -->
    mower_dd_et.append(ETree.Element("info", type_id="6", string="4.0.0"))
    #             <!-- Stack Version -->
    mower_dd_et.append(ETree.Element("info", type_id="7", string="1.5.3"))
    #             <!-- Application Version -->
    mower_dd_et.append(ETree.Element("info", type_id="8", string="0.2.3"))
    #             <!-- Protocol -->
    mower_dd_et.append(ETree.Element("info", type_id="9", number="1"))
    #             <!-- Product -->
    mower_dd_et.append(ETree.Element("info", type_id="10", number="2"))
    #             <!-- Included -->
    mower_dd_et.append(ETree.Element("info", type_id="11", number="0"))
    #             <!-- Name -->
    mower_dd_et.append(ETree.Element("info", type_id="12", string="SG Mower LONA MOCK"))
    #             <!-- Radio Mode -->
    mower_dd_et.append(ETree.Element("info", type_id="13", number="0"))
    #             <!-- Wakeup Interval -->
    mower_dd_et.append(ETree.Element("info", type_id="14", number="333"))
    #             <!-- Wakeup Offset -->
    mower_dd_et.append(ETree.Element("info", type_id="15", number="0"))
    #             <!-- Wakeup Channel -->
    mower_dd_et.append(ETree.Element("info", type_id="16", number="3"))
    #             <!-- Channel Map -->
    mower_dd_et.append(ETree.Element("info", type_id="17", hex="10080804"))
    #             <!-- Channel Scan Time -->
    mower_dd_et.append(ETree.Element("info", type_id="18", number="10000"))
    #             <!-- IPv6 Address -->
    mower_dd_et.append(ETree.Element("info", type_id="19"))
    #             <!-- Wakeup Now -->
    mower_dd_et.append(ETree.Element("info", type_id="20"))
    #             <!-- Diversity Mode -->
    mower_dd_et.append(ETree.Element("info", type_id="21", number="1"))
    #             <!-- TX Power -->
    mower_dd_et.append(ETree.Element("info", type_id="27", number="14"))

    mower_dd = ReportDeviceDescription(mock_mower.device_description)
    assert ETree.tostring(mower_dd.toetree()) == ETree.tostring(mower_dd_et)


def test_rm_service_description_report(mock_rm):
    expected_xml = """
        <service_description_report>
            <!-- Memory information -->
            <service service_id="2" version="1"/>
            <!-- Device Description -->
            <service service_id="3" version="1"/>
            <!-- Value Description -->
            <service service_id="4" version="1"/>
            <!-- Value -->
            <service service_id="5" version="1"/>
            <!-- Partner Information -->
            <service service_id="6" version="1"/>
            <!-- Status -->
            <service service_id="14" version="1"/>
            <!-- Configuration -->
            <service service_id="15" version="1"/>
            <!-- Channel Scan -->
            <service service_id="13" version="1"/>
        </service_description_report>
    """
    expected_et = ETree.fromstring(expected_xml)

    rm_sd = ReportServiceDescription(mock_rm.service_description)
    assert_etree_equal(rm_sd.toetree(), expected_et)


def test_mower_service_description_report(mock_mower):
    expected_xml = """
        <service_description_report>
            <!-- Memory information -->
            <service service_id="2" version="1"/>
            <!-- Device Description -->
            <service service_id="3" version="1"/>
            <!-- Value Description -->
            <service service_id="4" version="1"/>
            <!-- Value -->
            <service service_id="5" version="1"/>
            <!-- Partner Information -->
            <service service_id="6" version="1"/>
            <!-- Action -->
            <service service_id="7" version="1"/>
            <!-- Calculation -->
            <service service_id="8" version="1"/>
            <!-- Timer -->
            <service service_id="9" version="1"/>
            <!-- Calendar -->
            <service service_id="10" version="1"/>
            <!-- Statemachine -->
            <service service_id="11" version="1"/>
            <!-- Firmware Update -->
            <service service_id="12" version="1"/>
            <!-- Status -->
            <service service_id="14" version="1"/>
            <!-- Configuration -->
            <service service_id="15" version="1"/>
        </service_description_report>
    """
    expected_et = ETree.fromstring(expected_xml)

    mower_sd = ReportServiceDescription(mock_mower.service_description)
    assert_etree_equal(mower_sd.toetree(), expected_et)


def test_rm_memory_information(mock_rm):
    rm_memory_info_et = ETree.Element("memory_information_report")
    #             <!-- Value -->
    rm_memory_info_et.append(
        ETree.Element("memory_information", memory_id="1", count="1", free_count="0"))
    #             <!-- Partner Information -->
    rm_memory_info_et.append(
        ETree.Element("memory_information", memory_id="2", count="70", free_count="68"))

    rm_memory_info = ReportMemoryInformation(mock_rm.memory_information)
    assert ETree.tostring(rm_memory_info.toetree()) == ETree.tostring(rm_memory_info_et)


def test_mower_memory_information(mock_mower):
    mower_memory_info_et = ETree.Element("memory_information_report")
    #             <!-- Value -->
    mower_memory_info_et.append(
        ETree.Element("memory_information", memory_id="1", count="40", free_count="0"))
    #             <!-- Partner Information -->
    mower_memory_info_et.append(
        ETree.Element("memory_information", memory_id="2", count="1", free_count="0"))
    #             <!-- Action Item -->
    mower_memory_info_et.append(
        ETree.Element("memory_information", memory_id="3", count="1", free_count="1"))
    #             <!-- Calculation -->
    mower_memory_info_et.append(
        ETree.Element("memory_information", memory_id="4", count="1", free_count="1"))
    #             <!-- Timer -->
    mower_memory_info_et.append(
        ETree.Element("memory_information", memory_id="5", count="1", free_count="1"))
    #             <!-- Calendar -->
    mower_memory_info_et.append(
        ETree.Element("memory_information", memory_id="6", count="1", free_count="1"))
    #             <!-- Statemachine -->
    mower_memory_info_et.append(
        ETree.Element("memory_information", memory_id="7", count="1", free_count="1"))
    #             <!-- Statemachine Transaction -->
    mower_memory_info_et.append(
        ETree.Element("memory_information", memory_id="8", count="1", free_count="1"))

    mower_memory_info = ReportMemoryInformation(mock_mower.memory_information)
    assert ETree.tostring(mower_memory_info.toetree()) == ETree.tostring(mower_memory_info_et)


def test_rm_partner_information_report(mock_rm, rm_partner_info_et):
    rm_partner_info = ReportPartnerInformation(mock_rm.partner_information)
    assert ETree.tostring(rm_partner_info.toetree()) == ETree.tostring(rm_partner_info_et)


def test_mower_partner_information_report(mock_mower):
    mower_partner1_et = ETree.Element("partner", partner_id="1")
    #                 <!-- Radio Mode -->
    mower_partner1_et.append(ETree.Element("info", type_id="13", number="0"))
    #                 <!-- Channel Map -->
    mower_partner1_et.append(ETree.Element("info", type_id="17", hex="10080804"))
    #                 <!-- IPv6 Address -->
    mower_partner1_et.append(ETree.Element("info", type_id="19", hex="FC000000000000000006010000000000"))
    #                 <!-- Send RSSI -->
    mower_partner1_et.append(ETree.Element("info", type_id="22", number="71"))
    #                 <!-- Reseive RSSI -->
    mower_partner1_et.append(ETree.Element("info", type_id="23", number="32"))
    #                 <!-- Receive Timestamp -->
    mower_partner1_et.append(ETree.Element("info", type_id="24", number="1596613111"))

    mower_partner_info_et = ETree.Element("partner_information_report")
    mower_partner_info_et.append(mower_partner1_et)

    mower_partner_info = ReportPartnerInformation(mock_mower.partner_information)
    assert ETree.tostring(mower_partner_info.toetree()) == ETree.tostring(mower_partner_info_et)


def test_parse_partner_information_set():
    xml = """
    <partner_information_set>
        <partner partner_id="1">
            <info number="0" type_id="13"/>
            <info number="0" type_id="14"/>
            <info number="0" type_id="15"/>
            <info number="3" type_id="16"/>
            <info hex="10080804" type_id="17"/>
            <info hex="FE80000000000000010694BBAE033FE4" type_id="19"/>
        </partner>
        <partner partner_id="2">
            <info number="0" type_id="13"/>
            <info number="333" type_id="14"/>
            <info number="0" type_id="15"/>
            <info number="0" type_id="16"/>
            <info hex="10080804" type_id="17"/>
            <info hex="FC0000000000000000062AEAE10F4B36" type_id="19"/>
        </partner>
    </partner_information_set>
    """

    et = ETree.fromstring(xml)
    p = SetPartnerInformation.frometree(et)

    assert_etree_equal(p.toetree(), et)

    expected = {
        1: {
            DeviceDescriptionType.RADIO_MODE: 0,
            DeviceDescriptionType.WAKEUP_INTERVAL: 0,
            DeviceDescriptionType.WAKEUP_OFFSET: 0,
            DeviceDescriptionType.WAKEUP_CHANNEL: 3,
            DeviceDescriptionType.CHANNEL_MAP: Hex('10080804'),
            DeviceDescriptionType.IPV6_ADDRESS: Hex('fe80000000000000010694bbae033fe4'),
        },
        2: {
            DeviceDescriptionType.RADIO_MODE: 0,
            DeviceDescriptionType.WAKEUP_INTERVAL: 333,
            DeviceDescriptionType.WAKEUP_OFFSET: 0,
            DeviceDescriptionType.WAKEUP_CHANNEL: 0,
            DeviceDescriptionType.CHANNEL_MAP: Hex('10080804'),
            DeviceDescriptionType.IPV6_ADDRESS: Hex('fc0000000000000000062aeae10f4b36'),
        },
    }

    assert p.to_dict() == expected


def test_value_description_report(mock_mower):
    expected_xml = """
        <value_description_report>
            <value_description mode="1" name="battery_level" persistent="0" type_id="17" value_id="1">
                <number_format max="100.0" min="0.0" step="1.0" unit="%"/>
            </value_description>
            <value_description mode="1" name="rf_link_quality" persistent="0" type_id="17" value_id="2">
                <number_format max="100.0" min="0.0" step="1.0" unit="%"/>
            </value_description>
            <value_description mode="1" name="manual_operation" persistent="0" type_id="17" value_id="3">
                <number_format max="1.0" min="0.0" step="1.0" unit=""/>
            </value_description>
            <value_description mode="1" name="status" persistent="0" type_id="17" value_id="4">
                <number_format max="18.0" min="0.0" step="1.0" unit=""/>
            </value_description>
            <value_description mode="1" name="timestamp_next_start" persistent="0" type_id="17" value_id="5">
                <hexBinary_format max_length="4"/>
            </value_description>
            <value_description mode="1" name="source_for_next_start" persistent="0" type_id="17" value_id="6">
                <number_format max="5.0" min="0.0" step="1.0" unit=""/>
            </value_description>
            <value_description mode="2" name="command" persistent="0" type_id="17" value_id="7">
                <number_format max="42.0" min="0.0" step="1.0" unit=""/>
            </value_description>
            <value_description mode="2" name="mower_timer" persistent="0" type_id="17" value_id="8">
                <number_format max="16777216.0" min="-16777215.0" step="1.0" unit="s"/>
            </value_description>
            <value_description mode="2" name="action_paused_until_1" persistent="1" type_id="17" value_id="9">
                <hexBinary_format max_length="6"/>
            </value_description>
            <value_description mode="2" name="start_delay_ms" persistent="1" type_id="17" value_id="10">
                <number_format max="59999.0" min="0.0" step="1.0" unit="ms"/>
            </value_description>
            <value_description mode="2" name="schedule_config" persistent="0" type_id="17" value_id="11">
                <hexBinary_format max_length="98"/>
            </value_description>
            <value_description mode="1" name="mmi_version" persistent="0" type_id="17" value_id="12">
                <string_format max_length="10"/>
            </value_description>
            <value_description mode="1" name="mainboard_version" persistent="0" type_id="17" value_id="13">
                <string_format max_length="10"/>
            </value_description>
            <value_description mode="1" name="device_type" persistent="0" type_id="17" value_id="14">
                <string_format max_length="4"/>
            </value_description>
            <value_description mode="1" name="device_variant" persistent="0" type_id="17" value_id="15">
                <string_format max_length="4"/>
            </value_description>
            <value_description mode="1" name="running_time" persistent="0" type_id="17" value_id="16">
                <number_format max="65535.0" min="0.0" step="1.0" unit=""/>
            </value_description>
            <value_description mode="1" name="cutting_time" persistent="0" type_id="17" value_id="17">
                <number_format max="65535.0" min="0.0" step="1.0" unit=""/>
            </value_description>
            <value_description mode="1" name="charging_cycles" persistent="0" type_id="17" value_id="18">
                <number_format max="65535.0" min="0.0" step="1.0" unit=""/>
            </value_description>
            <value_description mode="1" name="collisions" persistent="0" type_id="17" value_id="19">
                <number_format max="65535.0" min="0.0" step="1.0" unit=""/>
            </value_description>
            <value_description mode="1" name="last_error_code" persistent="0" type_id="17" value_id="20">
                <number_format max="65535.0" min="0.0" step="1.0" unit=""/>
            </value_description>
            <value_description mode="1" name="timestamp_last_error_code" persistent="0" type_id="17" value_id="21">
                <hexBinary_format max_length="4"/>
            </value_description>
            <value_description mode="2" name="starting_points" persistent="0" type_id="17" value_id="22">
                <hexBinary_format max_length="18"/>
            </value_description>
            <value_description mode="1" name="supported_wires" persistent="0" type_id="17" value_id="23">
                <number_format max="255.0" min="0.0" step="1.0" unit=""/>
            </value_description>
            <value_description mode="1" name="supported_starting_points" persistent="0" type_id="17" value_id="24">
                <number_format max="3.0" min="1.0" step="1.0" unit=""/>
            </value_description>
            <value_description mode="1" name="serial_number" persistent="0" type_id="17" value_id="25">
                <string_format max_length="10"/>
            </value_description>
            <value_description mode="1" name="internal_connection_state" persistent="0" type_id="17" value_id="26">
                <number_format max="5.0" min="0.0" step="1.0" unit=""/>
            </value_description>
            <value_description mode="1" name="onboard_temperature" persistent="0" type_id="17" value_id="27">
                <number_format max="225.0" min="-50.0" step="0.100000001" unit="°C"/>
            </value_description>
            <value_description mode="2" name="settings_control" persistent="0" type_id="17" value_id="28">
                <hexBinary_format max_length="32"/>
            </value_description>
            <value_description mode="1" name="settings_report" persistent="0" type_id="17" value_id="29">
                <hexBinary_format max_length="16"/>
            </value_description>
            <value_description mode="1" name="position" persistent="0" type_id="17" value_id="30">
                <hexBinary_format max_length="25"/>
            </value_description>
            <value_description mode="1" name="gnss" persistent="0" type_id="17" value_id="31">
                <hexBinary_format max_length="31"/>
            </value_description>
            <value_description mode="2" name="position_timer" persistent="0" type_id="17" value_id="32">
                <number_format max="3600.0" min="0.0" step="1.0" unit="s"/>
            </value_description>
            <value_description mode="2" name="position_update_interval" persistent="1" type_id="17" value_id="33">
                <number_format max="3600000.0" min="1.0" step="1.0" unit="ms"/>
            </value_description>
            <value_description mode="2" name="stop_and_turn" persistent="0" type_id="17" value_id="34">
                <number_format max="180.0" min="-180.0" step="1.0" unit="deg"/>
            </value_description>
            <value_description mode="2" name="lona_control" persistent="1" type_id="17" value_id="35">
                <number_format max="1.0" min="0.0" step="1.0" unit=""/>
            </value_description>
            <value_description mode="1" name="lona" persistent="0" type_id="17" value_id="36">
                <hexBinary_format max_length="512"/>
            </value_description>
            <value_description mode="1" name="lona_mcu_fw_version" persistent="0" type_id="17" value_id="37">
                <hexBinary_format max_length="8"/>
            </value_description>
            <value_description mode="1" name="lona_mcu_boot_fw_version" persistent="0" type_id="17" value_id="38">
                <hexBinary_format max_length="8"/>
            </value_description>
            <value_description mode="1" name="data_download" persistent="0" type_id="17" value_id="39">
                <hexBinary_format max_length="105"/>
            </value_description>
            <value_description mode="2" name="data_download_int" persistent="0" type_id="17" value_id="40">
                <hexBinary_format max_length="8"/>
            </value_description>
        </value_description_report>
"""

    vd = ReportValueDescription(mock_mower.value_description)

    expected_et = ETree.fromstring(expected_xml)
    assert_etree_equal(vd.toetree(), expected_et)


def test_get_multiple_partner_information(mock_rm, rm_partner_info_et):
    request_xml = """
<network xmlns="urn:partner_informationxsd" version="1">
    <device version="1">
        <partner_information_get partner_id="1"/>
        <partner_information_get partner_id="2"/>
        <partner_information_get partner_id="3"/>
        <partner_information_get partner_id="4"/>
        <partner_information_get partner_id="5"/>
        <partner_information_get partner_id="6"/>
        <partner_information_get partner_id="7"/>
        <partner_information_get partner_id="8"/>
        <partner_information_get partner_id="9"/>
        <partner_information_get partner_id="10"/>
        <partner_information_get partner_id="11"/>
        <partner_information_get partner_id="12"/>
        <partner_information_get partner_id="13"/>
        <partner_information_get partner_id="14"/>
        <partner_information_get partner_id="15"/>
    </device>
</network>
    """
    request_et = ETree.fromstring(request_xml)

    sock_addr = object()
    mock_rm.handle_partner_information(sock_addr, request_et)
    mock_rm.assert_sent_message_once(Service.PARTNER_INFORMATION, [rm_partner_info_et], sock_addr)


def test_get_all_partner_information(mock_rm, rm_partner_info_et):
    request_xml = """
<network xmlns="urn:partner_informationxsd" version="1">
    <device version="1">
        <partner_information_get/>
    </device>
</network>
    """
    request_et = ETree.fromstring(request_xml)

    sock_addr = object()
    mock_rm.handle_partner_information(sock_addr, request_et)
    mock_rm.assert_sent_message_once(Service.PARTNER_INFORMATION, [rm_partner_info_et], sock_addr)


def test_get_absent_partner_information(mock_rm):
    request_xml = """
<network xmlns="urn:partner_informationxsd" version="1">
    <device version="1">
        <partner_information_get partner_id="3"/>
    </device>
</network>
    """
    request_et = ETree.fromstring(request_xml)
    expected_response_xml = "<partner_information_report/>"""
    expected_response_et = ETree.fromstring(expected_response_xml)

    sock_addr = object()
    mock_rm.handle_partner_information(sock_addr, request_et)
    mock_rm.assert_sent_message_once(Service.PARTNER_INFORMATION, [expected_response_et], sock_addr)


def test_delete_partner_information(mock_rm):
    request_xml = """
<network xmlns="urn:partner_informationxsd" version="1">
    <device version="1">
        <partner_information_delete partner_id="1"/>
    </device>
</network>
    """
    request_et = ETree.fromstring(request_xml)

    expected_partner_information = {2: copy.deepcopy(mock_rm.partner_information[2])}

    sock_addr = object()
    mock_rm.handle_partner_information(sock_addr, request_et)

    assert mock_rm.partner_information == expected_partner_information


def test_delete_all_partner_information(mock_rm):
    request_xml = """
<network xmlns="urn:partner_informationxsd" version="1">
    <device version="1">
        <partner_information_delete/>
    </device>
</network>
    """
    request_et = ETree.fromstring(request_xml)

    sock_addr = object()
    mock_rm.handle_partner_information(sock_addr, request_et)

    assert mock_rm.partner_information == {}


def test_delete_absent_partner_information(mock_rm):
    request_xml = """
<network xmlns="urn:partner_informationxsd" version="1">
    <device version="1">
        <partner_information_delete partner_id="3"/>
    </device>
</network>
    """
    request_et = ETree.fromstring(request_xml)

    expected_partner_information = copy.deepcopy(mock_rm.partner_information)

    sock_addr = object()
    mock_rm.handle_partner_information(sock_addr, request_et)

    assert mock_rm.partner_information == expected_partner_information


def test_set_partner_information(mock_rm):
    request_xml = """
<network xmlns="urn:partner_informationxsd" version="1">
    <device version="1">
        <partner_information_set>
            <partner partner_id="3">
                <info type_id="13" number="1" />
                <info type_id="14" number="10000"/>
                <info type_id="15" number="240"/>
                <info type_id="16" number="2"/>
                <info type_id="19" hex="fc000000000000000100000000000007"/>
            </partner>
        </partner_information_set>
    </device>
</network>
    """
    request_et = ETree.fromstring(request_xml)

    expected_partner_information = {
        **copy.deepcopy(mock_rm.partner_information),
        3: {
            DeviceDescriptionType.RADIO_MODE: 1,
            DeviceDescriptionType.WAKEUP_INTERVAL: 10000,
            DeviceDescriptionType.WAKEUP_OFFSET: 240,
            DeviceDescriptionType.WAKEUP_CHANNEL: 2,
            DeviceDescriptionType.IPV6_ADDRESS: Hex("FC000000000000000100000000000007")
        }
    }

    sock_addr = object()
    mock_rm.handle_partner_information(sock_addr, request_et)

    assert mock_rm.partner_information == expected_partner_information


def test_update_partner_information(mock_rm):
    request_xml = """
    <network xmlns="urn:partner_informationxsd" version="1">
        <device version="1">
            <partner_information_set>
                <partner partner_id="2">
                    <info type_id="13" number="0" />
                    <info type_id="19" hex="fc000000000000000100000000000005"/>
                </partner>
            </partner_information_set>
        </device>
    </network>
        """
    request_et = ETree.fromstring(request_xml)

    expected_partner_information = copy.deepcopy(mock_rm.partner_information)
    expected_partner_information[2].update({
        DeviceDescriptionType.RADIO_MODE: 0,
        DeviceDescriptionType.IPV6_ADDRESS: Hex("FC000000000000000100000000000005")
    })

    sock_addr = object()
    mock_rm.handle_partner_information(sock_addr, request_et)

    assert mock_rm.partner_information == expected_partner_information


def test_set_get_value(mock_mower, mower_client):
    mower_client.set_value(value_id=7, value=42)
    assert mock_mower.value[7] == 42
    assert mower_client.get_value(value_id=7) == [ReportValue(value_id=7, value=42.0, timestamp=0)]


def test_firmware_data():
    xml = '<firmware_data offset="0"><chunk>EF629EE40E000F00A8A0</chunk></firmware_data>'
    firmware_data = FirmwareData.frometree(ETree.fromstring(xml))
    assert firmware_data == FirmwareData(offset=0, chunk=Hex("EF629EE40E000F00A8A0"))
