# SPDX-FileCopyrightText: GARDENA GmbH
#
# SPDX-License-Identifier: LGPL-2.0-or-later

# coding=utf-8

"""Lemonbeat values unit tests."""

import unittest
import xml.etree.ElementTree as ETree

from lemonbeat import SetValue, ReportValue, Hex, ValueMode, DeviceDescriptionType, RadioMode, Service
from lemonbeat._device import _parse_value_description, _parse_device_description, _parse_value
from lemonbeat._gateway import _SERVICE_REPORT_PARSERS
from . import etree_compare


class TestValues(unittest.TestCase):
    """Lemonbeat values unit tests."""

    def assertETreeEqual(self, first, second, msg=None):
        self.assertEqual(first.tag, second.tag, msg)
        self.assertEqual(first.text, second.text, msg)
        self.assertEqual(first.tail, second.tail, msg)
        self.assertEqual(first.attrib, second.attrib, msg)
        self.assertEqual(len(first), len(second), msg)
        for child_first, child_second in zip(first, second):
            self.assertETreeEqual(child_first, child_second, msg)

    def test_zero_value(self):
        obj = SetValue(value_id=42, value=0, timestamp=0)
        et = ETree.Element('value_set', {'value_id': '42', 'number': '0.0', 'timestamp': '0'})
        self.assertEqual('SetValue(value_id=42, value=0, timestamp=0)', obj.__repr__())
        self.assertETreeEqual(et, obj.toetree())
        self.assertEqual(obj, SetValue.frometree(et))

        obj = ReportValue(value_id=42, value=0, timestamp=0)
        et = ETree.Element('value_report', {'value_id': '42', 'number': '0.0', 'timestamp': '0'})
        self.assertEqual('ReportValue(value_id=42, value=0, timestamp=0)', obj.__repr__())
        self.assertETreeEqual(et, obj.toetree())
        self.assertEqual(obj, ReportValue.frometree(et))

    def test_number_value(self):
        obj = SetValue(value_id=42, value=12.34, timestamp=5678)
        et = ETree.Element('value_set', {'value_id': '42', 'number': '12.34', 'timestamp': '5678'})
        self.assertEqual('SetValue(value_id=42, value=12.34, timestamp=5678)', obj.__repr__())
        self.assertETreeEqual(et, obj.toetree())
        self.assertEqual(obj, SetValue.frometree(et))

        obj = ReportValue(value_id=42, value=12.34, timestamp=5678)
        et = ETree.Element('value_report', {'value_id': '42', 'number': '12.34', 'timestamp': '5678'})
        self.assertEqual('ReportValue(value_id=42, value=12.34, timestamp=5678)', obj.__repr__())
        self.assertETreeEqual(et, obj.toetree())
        self.assertEqual(obj, ReportValue.frometree(et))

    def test_negative_number_value(self):
        obj = SetValue(value_id=42, value=-42.23, timestamp=1337)
        et = ETree.Element('value_set', {'value_id': '42', 'number': '-42.23', 'timestamp': '1337'})
        self.assertEqual('SetValue(value_id=42, value=-42.23, timestamp=1337)', obj.__repr__())
        self.assertETreeEqual(et, obj.toetree())
        self.assertEqual(obj, SetValue.frometree(et))

        obj = ReportValue(value_id=42, value=-42.23, timestamp=1337)
        et = ETree.Element('value_report', {'value_id': '42', 'number': '-42.23', 'timestamp': '1337'})
        self.assertEqual('ReportValue(value_id=42, value=-42.23, timestamp=1337)', obj.__repr__())
        self.assertETreeEqual(et, obj.toetree())
        self.assertEqual(obj, ReportValue.frometree(et))

    def test_nan_value(self):
        obj = SetValue(value_id=42, value=float('nan'), timestamp=0)
        et = ETree.Element('value_set', {'value_id': '42', 'number': 'NaN', 'timestamp': '0'})
        self.assertEqual('SetValue(value_id=42, value=nan, timestamp=0)', obj.__repr__())
        self.assertETreeEqual(et, obj.toetree())
        self.assertEqual(obj, SetValue.frometree(et))

        obj = ReportValue(value_id=42, value=float('nan'), timestamp=0)
        et = ETree.Element('value_report', {'value_id': '42', 'number': 'NaN', 'timestamp': '0'})
        self.assertEqual('ReportValue(value_id=42, value=nan, timestamp=0)', obj.__repr__())
        self.assertETreeEqual(et, obj.toetree())
        self.assertEqual(obj, ReportValue.frometree(et))

    def test_inf_value(self):
        obj = SetValue(value_id=42, value=float('inf'), timestamp=0)
        et = ETree.Element('value_set', {'value_id': '42', 'number': 'INF', 'timestamp': '0'})
        self.assertEqual('SetValue(value_id=42, value=inf, timestamp=0)', obj.__repr__())
        self.assertETreeEqual(et, obj.toetree())
        self.assertEqual(obj, SetValue.frometree(et))

        obj = ReportValue(value_id=42, value=float('inf'), timestamp=0)
        et = ETree.Element('value_report', {'value_id': '42', 'number': 'INF', 'timestamp': '0'})
        self.assertEqual('ReportValue(value_id=42, value=inf, timestamp=0)', obj.__repr__())
        self.assertETreeEqual(et, obj.toetree())
        self.assertEqual(obj, ReportValue.frometree(et))

    def test_negative_inf_value(self):
        obj = SetValue(value_id=42, value=float('-inf'), timestamp=0)
        et = ETree.Element('value_set', {'value_id': '42', 'number': '-INF', 'timestamp': '0'})
        self.assertEqual('SetValue(value_id=42, value=-inf, timestamp=0)', obj.__repr__())
        self.assertETreeEqual(et, obj.toetree())
        self.assertEqual(obj, SetValue.frometree(et))

        obj = ReportValue(value_id=42, value=float('-inf'), timestamp=0)
        et = ETree.Element('value_report', {'value_id': '42', 'number': '-INF', 'timestamp': '0'})
        self.assertEqual('ReportValue(value_id=42, value=-inf, timestamp=0)', obj.__repr__())
        self.assertETreeEqual(et, obj.toetree())
        self.assertEqual(obj, ReportValue.frometree(et))

    def test_empty_hex_value(self):
        obj = SetValue(value_id=42, value=Hex(""), timestamp=0)
        et = ETree.Element('value_set', {'value_id': '42', 'hexBinary': '', 'timestamp': '0'})
        self.assertEqual('SetValue(value_id=42, value=Hex(\'\'), timestamp=0)', obj.__repr__())
        self.assertETreeEqual(et, obj.toetree())
        self.assertEqual(obj, SetValue.frometree(et))

        obj = ReportValue(value_id=42, value=Hex(""), timestamp=0)
        et = ETree.Element('value_report', {'value_id': '42', 'hexBinary': '', 'timestamp': '0'})
        self.assertEqual('ReportValue(value_id=42, value=Hex(\'\'), timestamp=0)', obj.__repr__())
        self.assertETreeEqual(et, obj.toetree())
        self.assertEqual(obj, ReportValue.frometree(et))

    def test_hex_value(self):
        obj = SetValue(value_id=42, value=Hex("ad11"), timestamp=42)
        et = ETree.Element('value_set', {'value_id': '42', 'hexBinary': 'AD11', 'timestamp': '42'})
        self.assertEqual('SetValue(value_id=42, value=Hex(\'ad11\'), timestamp=42)', obj.__repr__())
        self.assertETreeEqual(et, obj.toetree())
        self.assertEqual(obj, SetValue.frometree(et))

        obj = ReportValue(value_id=42, value=Hex("ad11"), timestamp=42)
        et = ETree.Element('value_report', {'value_id': '42', 'hexBinary': 'AD11', 'timestamp': '42'})
        self.assertEqual('ReportValue(value_id=42, value=Hex(\'ad11\'), timestamp=42)', obj.__repr__())
        self.assertETreeEqual(et, obj.toetree())
        self.assertEqual(obj, ReportValue.frometree(et))

    def test_hex_bytes_value(self):
        obj = SetValue(value_id=42, value=b'\xad\x11', timestamp=42)
        et = ETree.Element('value_set', {'value_id': '42', 'hexBinary': 'AD11', 'timestamp': '42'})
        self.assertEqual('SetValue(value_id=42, value=b\'\\xad\\x11\', timestamp=42)', obj.__repr__())
        self.assertETreeEqual(et, obj.toetree())
        self.assertEqual(obj, SetValue.frometree(et))

        obj = ReportValue(value_id=42, value=b'\xad\x11', timestamp=42)
        et = ETree.Element('value_report', {'value_id': '42', 'hexBinary': 'AD11', 'timestamp': '42'})
        self.assertEqual('ReportValue(value_id=42, value=b\'\\xad\\x11\', timestamp=42)', obj.__repr__())
        self.assertETreeEqual(et, obj.toetree())
        self.assertEqual(obj, ReportValue.frometree(et))

    def test_empty_string_value(self):
        obj = SetValue(value_id=42, value="", timestamp=0)
        et = ETree.Element('value_set', {'value_id': '42', 'string': '', 'timestamp': '0'})
        self.assertEqual('SetValue(value_id=42, value=\'\', timestamp=0)', obj.__repr__())
        self.assertETreeEqual(et, obj.toetree())
        self.assertEqual(obj, SetValue.frometree(et))

        obj = ReportValue(value_id=42, value="", timestamp=0)
        et = ETree.Element('value_report', {'value_id': '42', 'string': '', 'timestamp': '0'})
        self.assertEqual('ReportValue(value_id=42, value=\'\', timestamp=0)', obj.__repr__())
        self.assertETreeEqual(et, obj.toetree())
        self.assertEqual(obj, ReportValue.frometree(et))

    def test_string_value(self):
        obj = SetValue(value_id=42, value="miau", timestamp=13)
        et = ETree.Element('value_set', {'value_id': '42', 'string': 'miau', 'timestamp': '13'})
        self.assertEqual('SetValue(value_id=42, value=\'miau\', timestamp=13)', obj.__repr__())
        self.assertETreeEqual(et, obj.toetree())
        self.assertEqual(obj, SetValue.frometree(et))

        obj = ReportValue(value_id=42, value="miau", timestamp=13)
        et = ETree.Element('value_report', {'value_id': '42', 'string': 'miau', 'timestamp': '13'})
        self.assertEqual('ReportValue(value_id=42, value=\'miau\', timestamp=13)', obj.__repr__())
        self.assertETreeEqual(et, obj.toetree())
        self.assertEqual(obj, ReportValue.frometree(et))

    def test_xml_entities_string_value(self):
        obj = SetValue(value_id=42, value="miau\"miau\"'miau'&wuff", timestamp=13)
        et = ETree.Element('value_set', {'value_id': '42', 'string': 'miau"miau"\'miau\'&wuff', 'timestamp': '13'})
        self.assertEqual('SetValue(value_id=42, value=\'miau"miau"\\\'miau\\\'&wuff\', timestamp=13)', obj.__repr__())
        self.assertETreeEqual(et, obj.toetree())
        self.assertEqual(obj, SetValue.frometree(et))
        self.assertTrue(etree_compare.eq(ETree.fromstring(
            b'<value_set string="miau&quot;miau&quot;\'miau\'&amp;wuff" timestamp="13" value_id="42" />'), et))

        obj = ReportValue(value_id=42, value="miau\"miau\"'miau'&wuff", timestamp=13)
        et = ETree.Element('value_report', {'value_id': '42', 'string': 'miau"miau"\'miau\'&wuff', 'timestamp': '13'})
        self.assertEqual('ReportValue(value_id=42, value=\'miau\"miau"\\\'miau\\\'&wuff\', timestamp=13)',
                         obj.__repr__())
        self.assertETreeEqual(et, obj.toetree())
        self.assertEqual(obj, ReportValue.frometree(et))
        self.assertTrue(etree_compare.eq(ETree.fromstring(
            b'<value_report string="miau&quot;miau&quot;\'miau\'&amp;wuff" timestamp="13" value_id="42" />'), et))

    def test_parse_report_value(self):
        input_data = [ETree.Element('value_report', x) for x in [
            {'number': '100.0', 'timestamp': '1551151774195', 'value_id': '1'},
            {'number': '2.0', 'timestamp': '1551148087108', 'value_id': '2'},
            {'number': '0.0', 'timestamp': '0', 'value_id': '3'},
            {'number': 'NaN', 'timestamp': '0', 'value_id': '10'},
            {'number': '1.0', 'timestamp': '0', 'value_id': '26'},
            {'hexBinary': '00060001', 'timestamp': '0', 'value_id': '27'},
            {'hexBinary': '', 'timestamp': '0', 'value_id': '28'},
            {'number': '480.0', 'timestamp': '0', 'value_id': '32'},
        ]]
        expected_output = [ReportValue(value_id=1, value=100.0, timestamp=1551151774195),
                           ReportValue(value_id=2, value=2.0, timestamp=1551148087108),
                           ReportValue(value_id=3, value=0.0, timestamp=0),
                           ReportValue(value_id=10, value=float('nan'), timestamp=0),
                           ReportValue(value_id=26, value=1.0, timestamp=0),
                           ReportValue(value_id=27, value=Hex('00060001'), timestamp=0),
                           ReportValue(value_id=28, value=Hex(''), timestamp=0),
                           ReportValue(value_id=32, value=480.0, timestamp=0)]
        output = _SERVICE_REPORT_PARSERS[Service.VALUE](input_data)
        self.assertEqual(expected_output, output)

    def test_parse_value_description(self):
        def value_description(vd, f, fd):
            v = ETree.Element('value_description', vd)
            v.append(ETree.Element(f, fd))
            return v

        value_description_report = ETree.Element('value_description_report')
        value_description_report.extend([value_description(vd, f, fd) for (vd, f, fd) in [
            ({'mode': '1', 'name': 'rf_link_quality', 'persistent': '0', 'type_id': '17', 'value_id': '1'},
             'number_format', {'max': '100.0', 'min': '0.0', 'step': '1.0', 'unit': '%'}),
            ({'mode': '1', 'name': 'rf_link_state', 'persistent': '0', 'type_id': '17', 'value_id': '2'},
             'number_format', {'max': '2.0', 'min': '0.0', 'step': '1.0', 'unit': ''}),
            ({'mode': '2', 'name': 'watering_timer_1', 'persistent': '0', 'type_id': '17', 'value_id': '3'},
             'number_format', {'max': '35999.8', 'min': '-36000.0', 'step': '0.2', 'unit': 's'}),
            ({'mode': '2', 'name': 'valves_master_config', 'persistent': '1', 'type_id': '17', 'value_id': '10'},
             'number_format', {'max': '126.0', 'min': '0.0', 'step': '2.0', 'unit': ''}),
            ({'mode': '2', 'name': 'command', 'persistent': '0', 'type_id': '17', 'value_id': '26'},
             'number_format', {'max': '37.0', 'min': '0.0', 'step': '1.0', 'unit': ''}),
            ({'mode': '1', 'name': 'stm8_fw_version', 'persistent': '0', 'type_id': '17', 'value_id': '27'},
             'hexBinary_format', {'max_length': '4'}),
            ({'mode': '2', 'name': 'schedule_config', 'persistent': '0', 'type_id': '17', 'value_id': '28'},
             'hexBinary_format', {'max_length': '245'}),
            ({'mode': '2', 'name': 'be_decision_time', 'persistent': '1', 'type_id': '17', 'value_id': '32'},
             'number_format', {'max': '3600.0', 'min': '1.0', 'step': '1.0', 'unit': 's'}),
            ({'mode': '2', 'name': 'string', 'persistent': '0', 'type_id': '17', 'value_id': '41'},
             'string_format', {'max_length': '128'}),
            ({'mode': '3', 'name': 'write_only_value', 'persistent': '0', 'type_id': '17', 'value_id': '42'},
             'string_format', {'max_length': '1'}),
        ]])
        input_data = [value_description_report]

        expected_output = {
            1: {'mode': ValueMode.R, 'name': 'rf_link_quality', 'persistent': False, 'type_id': 17, 'max': 100,
                'min': 0, 'step': 1, 'unit': '%', 'type': int},
            2: {'mode': ValueMode.R, 'name': 'rf_link_state', 'persistent': False, 'type_id': 17, 'max': 2, 'min': 0,
                'step': 1, 'unit': '', 'type': int},
            3: {'mode': ValueMode.RW, 'name': 'watering_timer_1', 'persistent': False, 'type_id': 17,
                'max': 35999.8, 'min': -36000.0, 'step': 0.2, 'unit': 's', 'type': float},
            10: {'mode': ValueMode.RW, 'name': 'valves_master_config', 'persistent': True, 'type_id': 17, 'max': 126,
                 'min': 0, 'step': 2, 'unit': '', 'type': int},
            26: {'mode': ValueMode.RW, 'name': 'command', 'persistent': False, 'type_id': 17, 'max': 37, 'min': 0,
                 'step': 1, 'unit': '', 'type': int},
            27: {'mode': ValueMode.R, 'name': 'stm8_fw_version', 'persistent': False, 'type_id': 17, 'max_length': 4,
                 'type': Hex},
            28: {'mode': ValueMode.RW, 'name': 'schedule_config', 'persistent': False, 'type_id': 17, 'max_length': 245,
                 'type': Hex},
            32: {'mode': ValueMode.RW, 'name': 'be_decision_time', 'persistent': True, 'type_id': 17, 'max': 3600,
                 'min': 1, 'step': 1, 'unit': 's', 'type': int},
            41: {'mode': ValueMode.RW, 'name': 'string', 'persistent': False, 'type_id': 17, 'max_length': 128,
                 'type': str},
            42: {'mode': ValueMode.W, 'name': 'write_only_value', 'persistent': False, 'type_id': 17, 'max_length': 1,
                 'type': str},
        }
        output = _parse_value_description(input_data)
        self.assertEqual(expected_output, output)

    def test_parse_device_description(self):
        device_description_report = ETree.Element('device_description_report')
        device_description_report.extend([ETree.Element('info', dd) for dd in [
            {'number': '6', 'type_id': '1'},
            {'number': '3', 'type_id': '2'},
            {'hex': '000000000000E21BEDB87461', 'type_id': '3'},
            {'hex': 'E21BEDB87461', 'type_id': '4'},
            {'string': '0.0.0', 'type_id': '5'},
            {'string': '2.5.2', 'type_id': '6'},
            {'string': '1.2.6', 'type_id': '7'},
            {'string': '1.0.1', 'type_id': '8'},
            {'number': '1', 'type_id': '9'},
            {'number': '2', 'type_id': '10'},
            {'number': '1', 'type_id': '11'},
            {'string': 'SG IC24', 'type_id': '12'},
            {'number': '0', 'type_id': '13'},
            {'number': '333', 'type_id': '14'},
            {'number': '0', 'type_id': '15'},
            {'number': '3', 'type_id': '16'},
            {'hex': '10080804', 'type_id': '17'},
            {'number': '10000', 'type_id': '18'},
        ]])
        input_data = [device_description_report]

        expected_output = {
            DeviceDescriptionType.DEVICE_TYPE: 6,
            DeviceDescriptionType.DEVICE_MANUFACTURER: 3,
            DeviceDescriptionType.SGTIN: Hex("000000000000E21BEDB87461"),
            DeviceDescriptionType.MAC_ADDRESS: Hex("E21BEDB87461"),
            DeviceDescriptionType.HARDWARE_VERSION: "0.0.0",
            DeviceDescriptionType.BOOTLOADER_VERSION: "2.5.2",
            DeviceDescriptionType.STACK_VERSION: "1.2.6",
            DeviceDescriptionType.APPLICATION_VERSION: "1.0.1",
            DeviceDescriptionType.PROTOCOL: 1,
            DeviceDescriptionType.DEVICE_PRODUCT: 2,
            DeviceDescriptionType.INCLUDED: 1,
            DeviceDescriptionType.NAME: "SG IC24",
            DeviceDescriptionType.RADIO_MODE: RadioMode.ALWAYS_ONLINE,
            DeviceDescriptionType.WAKEUP_INTERVAL: 333,
            DeviceDescriptionType.WAKEUP_OFFSET: 0,
            DeviceDescriptionType.WAKEUP_CHANNEL: 3,
            DeviceDescriptionType.CHANNEL_MAP: Hex("10080804"),
            DeviceDescriptionType.CHANNEL_SCAN_TIME: 10000,
        }
        output = _parse_device_description(input_data)
        self.assertEqual(expected_output, output)

    def test_parse_device_description_mower(self):
        device_description_xml = '''<?xml version="1.0" ?>
<network version="1" xmlns="urn:device_descriptionxsd">
    <device device_id="1" version="1">
        <device_description_report>
            <!-- Type -->
            <info number="3" type_id="1"/>
            <!-- Manufacturer -->
            <info number="3" type_id="2"/>
            <!-- Sgtin -->
            <info hex="3034F8EE90060080000007B8" type_id="3"/>
            <!-- Mac Address -->
            <info hex="94BBAE002B3B" type_id="4"/>
            <!-- Hardware Version -->
            <info string="3.0.0" type_id="5"/>
            <!-- Bootloader Version -->
            <info string="2.5.2" type_id="6"/>
            <!-- Stack Version -->
            <info string="1.2.6" type_id="7"/>
            <!-- Application Version -->
            <info string="1.5.3" type_id="8"/>
            <!-- Protocol -->
            <info number="1" type_id="9"/>
            <!-- Product -->
            <info number="14" type_id="10"/>
            <!-- Included -->
            <info number="1" type_id="11"/>
            <!-- Name -->
            <info string="Husqvarna Automower" type_id="12"/>
            <!-- Radio Mode -->
            <info number="0" type_id="13"/>
            <!-- Wakeup Interval -->
            <info number="333" type_id="14"/>
            <!-- Wakeup Offset -->
            <info number="0" type_id="15"/>
            <!-- Wakeup Channel -->
            <info number="3" type_id="16"/>
            <!-- Channel Map -->
            <info hex="10080804" type_id="17"/>
            <!-- Channel Scan Time -->
            <info number="10000" type_id="18"/>
            <!-- IPv6 Address -->
            <info type_id="19"/>
            <!-- Wakeup Now -->
            <info type_id="20"/>
            <!-- Diversity Mode -->
            <info number="1" type_id="21"/>
            <!-- TX Power -->
            <info number="14" type_id="27"/>
        </device_description_report>
    </device>
</network>
'''
        device_description_report = ETree.fromstring(device_description_xml)[0][0]
        input_data = [device_description_report]

        expected_output = {
            DeviceDescriptionType.DEVICE_TYPE: 3,
            DeviceDescriptionType.DEVICE_MANUFACTURER: 3,
            DeviceDescriptionType.SGTIN: Hex("3034F8EE90060080000007B8"),
            DeviceDescriptionType.MAC_ADDRESS: Hex("94BBAE002B3B"),
            DeviceDescriptionType.HARDWARE_VERSION: "3.0.0",
            DeviceDescriptionType.BOOTLOADER_VERSION: "2.5.2",
            DeviceDescriptionType.STACK_VERSION: "1.2.6",
            DeviceDescriptionType.APPLICATION_VERSION: "1.5.3",
            DeviceDescriptionType.PROTOCOL: 1,
            DeviceDescriptionType.DEVICE_PRODUCT: 14,
            DeviceDescriptionType.INCLUDED: 1,
            DeviceDescriptionType.NAME: "Husqvarna Automower",
            DeviceDescriptionType.RADIO_MODE: RadioMode.ALWAYS_ONLINE,
            DeviceDescriptionType.WAKEUP_INTERVAL: 333,
            DeviceDescriptionType.WAKEUP_OFFSET: 0,
            DeviceDescriptionType.WAKEUP_CHANNEL: 3,
            DeviceDescriptionType.CHANNEL_MAP: Hex("10080804"),
            DeviceDescriptionType.CHANNEL_SCAN_TIME: 10000,
            DeviceDescriptionType.IPV6_ADDRESS: None,
            DeviceDescriptionType.WAKEUP_NOW: None,
            DeviceDescriptionType.DIVERSITY_MODE: 1,
            27: 14,
        }
        output = _parse_device_description(input_data)
        self.assertEqual(expected_output, output)


def test_parse_value():
    value_report_xml = '''<?xml version="1.0" ?>
<network version="1" xmlns="urn:valuexsd">
    <device device_id="1" version="1">
        <value_report number="6.0" timestamp="1567673339068" value_id="9"/>
    </device>
</network>
'''
    value_report = ETree.fromstring(value_report_xml)[0][0]
    assert _parse_value([value_report]) == [ReportValue(value_id=9, value=6.0, timestamp=1567673339068)]
