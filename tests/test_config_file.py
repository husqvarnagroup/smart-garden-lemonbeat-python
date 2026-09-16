# SPDX-FileCopyrightText: GARDENA GmbH
#
# SPDX-License-Identifier: LGPL-2.0-or-later

# coding=utf-8

"""Lemonbeat Device config_file tests."""

from unittest import mock

import pytest

from lemonbeat import Device, config_file

INCLUSION_MESSAGE = "0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF"


# autouse this fixture, otherwise tests might accidentally overwrite your config file
@pytest.fixture(autouse=True)
def save_data_mock():
    save_mock = mock.MagicMock()
    with mock.patch("lemonbeat.config_file._save_data", save_mock):
        yield save_mock


@pytest.fixture
def xdg_load_first_config_mock():
    xdg_mock = mock.MagicMock()
    with mock.patch("lemonbeat.config_file.load_first_config", xdg_mock):
        yield xdg_mock
    xdg_mock.assert_called_with("lemonbeat-python")


@pytest.fixture
def load_data_mock(xdg_load_first_config_mock):
    xdg_load_first_config_mock.return_value = "fake_config_file_path"
    load_mock = mock.MagicMock()
    with mock.patch("lemonbeat.config_file._load_data", load_mock):
        yield load_mock
    load_mock.assert_called_with(xdg_load_first_config_mock.return_value + "/default.toml")


@pytest.fixture
def generate_mock():
    gen_mock = mock.MagicMock()
    gen_mock.return_value = "42" * 64
    with mock.patch("lemonbeat.config_file.generate", gen_mock):
        yield gen_mock
    gen_mock.assert_called_once()


@pytest.mark.parametrize("load_function", [config_file.load, config_file.load_or_create])
def test_load(load_function, load_data_mock):
    load_data_mock.return_value = (
        INCLUSION_MESSAGE,
        {"test_device_1": "2001:db8::1", "test_device_2": "2001:db8::2"},
    )
    gateway, devices = load_function()
    assert gateway.inclusion_message == INCLUSION_MESSAGE
    assert devices["test_device_1"].address == "2001:db8::1"
    assert devices["test_device_2"].address == "2001:db8::2"

    gateway2, _ = config_file.load(gateway=gateway)
    assert gateway2 is gateway


@pytest.mark.parametrize("load_function", [config_file.load, config_file.load_or_create])
def test_load_with_only_gateway(load_function, load_data_mock):
    load_data_mock.return_value = (
        INCLUSION_MESSAGE,
        {},
    )
    gateway, devices = load_function()
    assert gateway.inclusion_message == INCLUSION_MESSAGE
    assert devices == {}

    gateway2, _ = config_file.load(gateway=gateway)
    assert gateway2 is gateway


def test_load_with_only_devices(load_data_mock):
    load_data_mock.return_value = (
        None,
        {"test_device_1": "2001:db8::1", "test_device_2": "2001:db8::2"},
    )
    gateway, devices = config_file.load()
    assert gateway is None
    assert devices["test_device_1"].address == "2001:db8::1"
    assert devices["test_device_2"].address == "2001:db8::2"

    gateway2, _ = config_file.load(gateway=gateway)
    assert gateway2 is gateway


def test_load_or_create_with_only_devices(load_data_mock, generate_mock):
    load_data_mock.return_value = (
        None,
        {"test_device_1": "2001:db8::1", "test_device_2": "2001:db8::2"},
    )
    gateway, devices = config_file.load_or_create()
    assert gateway.inclusion_message == "42" * 64
    assert devices["test_device_1"].address == "2001:db8::1"
    assert devices["test_device_2"].address == "2001:db8::2"


def test_load_with_empty_data(load_data_mock):
    load_data_mock.return_value = (
        None,
        {},
    )
    gateway, devices = config_file.load()
    assert gateway is None
    assert devices == {}

    gateway2, _ = config_file.load(gateway=gateway)
    assert gateway2 is gateway


def test_load_or_create_with_empty_data(load_data_mock, generate_mock, save_data_mock):
    load_data_mock.return_value = (
        None,
        {},
    )
    gateway, devices = config_file.load_or_create()
    assert gateway.inclusion_message == "42" * 64
    assert devices == {}
    save_data_mock.assert_called_once_with("42" * 64, {})


def test_load_without_config_file(load_data_mock):
    load_data_mock.side_effect = config_file.NoConfigFoundError
    with pytest.raises(config_file.NoConfigFoundError):
        config_file.load()


def test_load_or_create_without_config_file(load_data_mock, generate_mock, save_data_mock):
    load_data_mock.side_effect = config_file.NoConfigFoundError
    gateway, devices = config_file.load_or_create()
    assert gateway.inclusion_message == "42" * 64
    assert devices == {}
    save_data_mock.assert_called_once_with("42" * 64, {})


def test_load_without_config_dir(xdg_load_first_config_mock):
    xdg_load_first_config_mock.return_value = None
    with pytest.raises(config_file.NoConfigFoundError):
        config_file.load()


def test_load_or_create_without_config_dir(xdg_load_first_config_mock, generate_mock, save_data_mock):
    xdg_load_first_config_mock.return_value = None
    gateway, devices = config_file.load_or_create()
    assert gateway.inclusion_message == "42" * 64
    assert devices == {}
    save_data_mock.assert_called_once_with("42" * 64, {})


def test_add_device(load_data_mock, save_data_mock):
    load_data_mock.return_value = (
        INCLUSION_MESSAGE,
        {"test_device_1": "2001:db8::1", "test_device_2": "2001:db8::2"},
    )
    config_file.add_device("new_test_device", Device(None, "2001:db8::42"))
    save_data_mock.assert_called_once_with(
        INCLUSION_MESSAGE,
        {"test_device_1": "2001:db8::1", "test_device_2": "2001:db8::2", "new_test_device": "2001:db8::42"},
    )


def test_add_device_without_config_file(load_data_mock, save_data_mock):
    load_data_mock.side_effect = config_file.NoConfigFoundError
    config_file.add_device("new_test_device", Device(None, "2001:db8::42"))
    save_data_mock.assert_called_once_with(None, {"new_test_device": "2001:db8::42"})
