# SPDX-FileCopyrightText: GARDENA GmbH
#
# SPDX-License-Identifier: LGPL-2.0-or-later

# coding=utf-8

"""Value properties unit tests."""

import unittest
from unittest.mock import Mock

from lemonbeat import Hex, ValueMode, ReportValue
from lemonbeat.value_properties import ValueProperties


class MockDevice:
    """Mock Lemonbeat Device"""

    # noinspection PyMethodMayBeStatic,DuplicatedCode
    def get_value_description(self):
        # TODO refactor to use some kind of shared test fixture
        return {
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

    @property
    def zoned_address(self):
        return "mock_address"


class TestValueProperties(unittest.TestCase):
    """Lemonbeat value properties unit tests."""

    def test_properties(self):
        d = MockDevice()
        v = ValueProperties(d)
        self.assertIn('rf_link_quality', dir(v))
        self.assertIn('rf_link_state', dir(v))
        self.assertIn('watering_timer_1', dir(v))
        self.assertIn('valves_master_config', dir(v))
        self.assertIn('command', dir(v))
        self.assertIn('stm8_fw_version', dir(v))
        self.assertIn('schedule_config', dir(v))
        self.assertIn('be_decision_time', dir(v))
        self.assertIn('string', dir(v))
        self.assertIn('write_only_value', dir(v))

    # noinspection PyUnresolvedReferences
    def test_get_value(self):
        d = MockDevice()
        mock_values = {1: 60, 2: 2, 3: 4.2, 10: 0, 26: 37, 27: Hex("f0ad1086"), 28: Hex(""), 32: 1, 41: "hallo"}
        d.get_value = Mock(side_effect=lambda value_id: [ReportValue(value_id=value_id, value=mock_values[value_id])])
        v = ValueProperties(d)
        self.assertEqual(60, v.rf_link_quality)
        self.assertEqual(2, v.rf_link_state)
        self.assertEqual(4.2, v.watering_timer_1)
        self.assertEqual(0, v.valves_master_config)
        self.assertEqual(37, v.command)
        self.assertEqual(Hex("f0ad1086"), v.stm8_fw_version)
        self.assertEqual(Hex(""), v.schedule_config)
        self.assertEqual(1, v.be_decision_time)
        self.assertEqual("hallo", v.string)
        with self.assertRaises(AttributeError):
            # noinspection PyStatementEffect
            v.write_only_value

    def test_set_value(self):
        d = MockDevice()
        d.set_value = Mock()
        v = ValueProperties(d)
        with self.assertRaises(AttributeError):
            v.rf_link_quality = 60
        with self.assertRaises(AttributeError):
            v.rf_link_state = 2
        v.watering_timer_1 = 4.2
        d.set_value.assert_called_with(value=4.2, value_id=3)
        v.valves_master_config = 0
        d.set_value.assert_called_with(value=0, value_id=10)
        v.command = 37
        d.set_value.assert_called_with(value=37, value_id=26)
        with self.assertRaises(AttributeError):
            v.stm8_fw_version = Hex("f0ad1086")
        v.schedule_config = Hex("")
        d.set_value.assert_called_with(value=Hex(""), value_id=28)
        v.be_decision_time = 1
        d.set_value.assert_called_with(value=1, value_id=32)
        v.string = "hallo"
        d.set_value.assert_called_with(value="hallo", value_id=41)
        v.write_only_value = "x"
        d.set_value.assert_called_with(value="x", value_id=42)

    def test_set_nonexistent_property(self):
        d = MockDevice()
        d.set_value = Mock()
        v = ValueProperties(d)
        with self.assertRaises(AttributeError):
            v.asdfasdf = 7
