# SPDX-FileCopyrightText: GARDENA GmbH
#
# SPDX-License-Identifier: LGPL-2.0-or-later

# coding=utf-8

"""Lemonbeat Device unit tests."""

import xml.etree.ElementTree as ETree
from unittest import mock

import pytest

from lemonbeat import Device, Gateway, ReportValue, Service, Status, MemoryInformationType
from . import etree_compare


@pytest.fixture
def device():
    gw = Gateway(bind_address=("::", 0, 0, 0), address="fc00::1234:1")
    return Device(gw, "fc00::1234:2")


def test_get_value(device):
    expected_request = ETree.fromstring('<value_get value_id="23"/>')
    mock_response = [ETree.fromstring('<value_report number="42.0" timestamp="123456" value_id="23"/>')]
    device._send_request = mock.Mock(return_value=mock_response)
    assert device.get_value(23) == [ReportValue(value_id=23, value=42.0, timestamp=123456)]
    assert device._send_request.call_args[0][0] == Service.VALUE
    assert etree_compare.eq(device._send_request.call_args[0][1][0], expected_request)


def test_set_value(device):
    expected_request = ETree.fromstring('<value_set number="101.0" timestamp="0" value_id="1337"/>')
    device._send_message = mock.Mock(return_value=None)
    device.set_value(value_id=1337, value=101)
    assert device._send_message.call_args[0][0] == Service.VALUE
    assert etree_compare.eq(device._send_message.call_args[0][1][0], expected_request)


def test_set_status_level(device):
    expected_request = ETree.fromstring('<status_set_level level="5"/>')
    device._send_message = mock.Mock(return_value=None)
    device.set_status_level(Status.Level.DEBUG)
    assert device._send_message.call_args[0][0] == Service.STATUS
    assert etree_compare.eq(device._send_message.call_args[0][1][0], expected_request)


@mock.patch('lemonbeat._device._send')
def test_go_to_sleep(patched_send, device):
    device.go_to_sleep = 2342
    device.set_value(value_id=1337, value=101)
    assert patched_send.call_args[1]["go_to_sleep"] == 2342


def test_get_memory_information(device):
    """Test get_memory_information with a captured example message."""
    memmory_information_message = """<memory_information_report>
    <!-- Value -->
    <memory_information count="11" free_count="0" memory_id="1" />
    <!-- Partner Information -->
    <memory_information count="1" free_count="0" memory_id="2" />
    <!-- Action Item -->
    <memory_information count="1" free_count="1" memory_id="3" />
    <!-- Calculation -->
    <memory_information count="1" free_count="1" memory_id="4" />
    <!-- Timer -->
    <memory_information count="1" free_count="1" memory_id="5" />
    <!-- Calendar -->
    <memory_information count="1" free_count="1" memory_id="6" />
    <!-- Statemachine -->
    <memory_information count="1" free_count="1" memory_id="7" />
    <!-- Statemachine Transaction -->
    <memory_information count="1" free_count="1" memory_id="8" />
</memory_information_report>
"""
    mock_response = [ETree.fromstring(memmory_information_message)]
    device._send_request = mock.Mock(return_value=mock_response)
    memory_information = device.get_memory_information()

    assert memory_information[MemoryInformationType.VALUE] == {'count': 11, 'free_count': 0}
    assert memory_information[MemoryInformationType.PARTNER_INFORMATION] == {'count': 1, 'free_count': 0}
    assert memory_information[MemoryInformationType.ACTION_ITEMS] == {'count': 1, 'free_count': 1}
    assert type(memory_information[MemoryInformationType.STATEMACHINE_TRANSACTIONS]['count']) == int
    assert type(memory_information[MemoryInformationType.STATEMACHINE_TRANSACTIONS]['free_count']) == int
