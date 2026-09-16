# coding=utf-8

# Copyright 2020 Gardena GmbH
# Adrian Friedli <adrian.friedli@husqvarnagroup.com>
#
# SPDX-License-Identifier: LGPL-2.0-or-later

"""
Utility functions for loading and saving a simple config file.
"""

__version__ = "0.1.0"

__all__ = [
    "add_device",
    "get_path",
    "load",
    "load_or_create",
    "NoConfigFoundError",
    "save",
]

import logging
import os

import toml
from xdg.BaseDirectory import save_config_path, load_first_config

from lemonbeat import Gateway, Device, MissingInclusionMessageError
from lemonbeat.inclusion_message import generate

CONFIG_RESOURCE = "lemonbeat-python"
DEFAULT_CONFIG_FILE = "default.toml"


class NoConfigFoundError(Exception):
    """Exception for representing the error when no config file was found."""
    pass


def get_path():
    """Get the load path of the config file.

    This config file will be tried loading if you call `load()`.

    :raises NoConfigFoundError if the xdg config resource directory was not found.
    """
    config_dir = load_first_config(CONFIG_RESOURCE)
    if config_dir is None:
        raise NoConfigFoundError
    return os.path.join(config_dir, DEFAULT_CONFIG_FILE)


def load(**kwargs):
    """Load the config file.

    Returns a 2-tuple with a Gateway object and a dictionary of Device
    objects. Associate loaded devices with optionally specified Gateway
    instance instead of creating new instance with data loaded from
    config file.
    :raises NoConfigFoundError if no config file was found.
    """
    inclusion_message, device_addresses = _load_data(get_path())
    if inclusion_message is not None:
        kwargs["inclusion_message"] = inclusion_message
    return _create_devices(device_addresses, **kwargs)


def _load_data(config_file):
    try:
        file = open(config_file)
    except FileNotFoundError:
        raise NoConfigFoundError
    with file:
        config_data = toml.load(file)
    inclusion_message = config_data.get("gateway", {}).get("inclusion_message")
    device_addresses = {device["name"]: device["address"] for device in config_data.get("devices", [])}
    return inclusion_message, device_addresses


def load_or_create(**kwargs):
    """Load config file or create one if it does not exist yet.

    If no config file exists, a random inclusion message is generated
    and persisted for the Gateway. The Device dictionary will be empty.

    Returns the same as `load()`.

    WARNING: This must not be called simultaneously in parallel if no
    config file does exist.
    """
    if 'gateway' in kwargs or 'inclusion_message' in kwargs:
        raise TypeError("load_or_create() got an unexpected keyword argument.")

    modified = False
    try:
        inclusion_message, device_addresses = _load_data(get_path())
    except NoConfigFoundError:
        logging.info("No config file present, creating file with random inclusion message.")
        inclusion_message = generate()
        device_addresses = {}
        modified = True
    if inclusion_message is None:
        logging.info("No inclusion message found in config file, creating and adding with random data.")
        inclusion_message = generate()
        modified = True
    gateway, devices = _create_devices(device_addresses, inclusion_message=inclusion_message, **kwargs)
    if modified:
        # Small race condition here if the config file does not exist and load_or_create() gets called in parallel.
        save(gateway, devices)
    return gateway, devices


def save(gateway, devices):
    """Save a Gateway and a dictionary of Device objects to the config file.

    From the Gateway the inclusion message gets persisted. From the
    Devices the name (dict key) and the IPv6 address get persisted.

    An example usage:
    ```
    gw, devices = load_or_create()
    # ...
    # do something
    # ...
    # add another device
    devices["fancy_device"] = Device(gw, "2001:db8::42")
    # ...
    save(gw, devices)
    ```
    """
    inclusion_message = None
    if gateway is not None:
        try:
            inclusion_message = gateway.inclusion_message
        except MissingInclusionMessageError:
            pass
    device_addresses = {name: device.address for name, device in devices.items()}
    _save_data(inclusion_message, device_addresses)


def _save_data(inclusion_message, device_addresses):
    data = {}
    if inclusion_message is not None:
        data["gateway"] = {"inclusion_message": inclusion_message}
    if len(device_addresses):
        data["devices"] = [{"name": name, "address": address} for name, address in device_addresses.items()]
    with open(os.path.join(save_config_path(CONFIG_RESOURCE), DEFAULT_CONFIG_FILE), 'w') as file:
        toml.dump(data, file)


def add_device(name, device):
    """Add a Device to the config file.

    The config file is created with a random inclusion message if it does
    not exist, similar to `load_or_create()`.

    WARNING: This must not be called simultaneously in parallel.

    An example usage:
    ```
    add_device("fancy_device", Device(None, "2001:db8::42"))
    ```
    """
    try:
        inclusion_message, device_addresses = _load_data(get_path())
    except NoConfigFoundError:
        logging.info("No config file present, creating file.")
        inclusion_message = None
        device_addresses = {}
    device_addresses[name] = device.address
    # Small race condition here.
    _save_data(inclusion_message, device_addresses)


def _create_devices(device_addresses, *, gateway_cls=Gateway, device_cls=Device, gateway=None, inclusion_message=None):
    if gateway is None and inclusion_message is not None:
        gateway = gateway_cls(inclusion_message=inclusion_message)
    devices = {name: device_cls(gateway, address) for name, address in device_addresses.items()}
    return gateway, devices
