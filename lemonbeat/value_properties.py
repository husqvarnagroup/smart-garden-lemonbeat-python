# coding=utf-8

# Copyright 2019 Gardena GmbH
# Adrian Friedli <adrian.friedli@husqvarnagroup.com>
#
# SPDX-License-Identifier: LGPL-2.0-or-later

"""
Value property container for Lemonbeat devices.
"""

__version__ = "0.1.0"

__all__ = [
    "ValueProperties",
]

import logging
import re
from functools import partial

try:
    from IPython.lib.pretty import pretty
except ModuleNotFoundError:
    pretty = repr  # pylint: disable=invalid-name

from lemonbeat import ValueMode

# TODO: find a good value for the rounding
ROUND_DIGITS = 6


def _to_python_identifier(name):
    name = re.sub('[^0-9A-Za-z_]', '_', name)
    if name[0].isdigit():
        name = '_' + name
    while name.startswith('__'):
        name = name[1:]
    return name


def _check_step(value, min_, step):
    offset = round(value - min_, ROUND_DIGITS)
    step = round(step, ROUND_DIGITS)
    return round((offset / step), ROUND_DIGITS).is_integer()


def _validate_number_value(min_, max_, step, value):
    value = float(value)
    if min_ is not None and value < min_:
        raise ValueError('Value is lower than min.')
    if max_ is not None and value > max_:
        raise ValueError('Value is greater than max.')
    if step is not None and not _check_step(value, min_, step):
        raise ValueError('Value is not a multiple of step.')


def _validate_value_length(type_, max_length, value):
    value = type_(value)
    if max_length is not None and len(value) > max_length:
        raise ValueError('Value is longer than max_length.')


def _generate_validate_value_function(name, type_, description):
    if type_ in (int, float):
        limits = [description.get('min'), description.get('max'), description.get('step')]
        if limits[0] is None:
            logging.warning("Skipping min validation for %s.", name)
        if limits[1] is None:
            logging.warning("Skipping max validation for %s.", name)
        if limits[2] is None:
            logging.warning("Skipping step validation for %s.", name)
        if all(lim is not None for lim in limits[:2]) and limits[0] > limits[1]:
            logging.warning("Skipping min, max and step validation for %s, because min > max.", name)
            limits[:] = None, None, None
        elif limits[2] is not None and (any(lim is None for lim in limits[:2]) or not _check_step(*limits)):
            logging.warning("Skipping step validation for %s, because step does not match min and max.", name)
            limits[2] = None
        return partial(_validate_number_value, *limits)

    max_length = description.get('max_length')
    if max_length is None:
        logging.warning("Skipping max length validation for %s.", name)
    return partial(_validate_value_length, type_, max_length)


def _get_value(device, validate_function, type_, value_id, _self):
    value = device.get_value(value_id=value_id)[0].value
    # First try to validate and then try to convert, because for numbers, we first have to validate the limits as float
    # before possibly rounding to an integer.
    try:
        validate_function(value)
    except ValueError as err:
        logging.warning(err)
    try:
        value = type_(value)
    except ValueError as err:
        logging.warning(err)
    return value


def _set_value(device, validate_function, type_, value_id, _self, value):
    # First convert and then validate, to allow strings to be converted to Hex,
    # but don't round probable floats to integers.
    if type_ == int:
        type_ = float
    value = type_(value)
    validate_function(value)
    return device.set_value(value_id=value_id, value=value)


class ValueProperties:  # pylint: disable=too-few-public-methods
    """Generated properties for values from a value_description."""

    def __init__(self, device, value_description=None):
        if value_description is None:
            value_description = device.get_value_description()
        properties = {
            "__setattr__": self._set_attr,
        }
        for value_id, description in value_description.items():
            name = description.get('name')
            mode = description.get('mode')
            type_ = description.get('type')
            if not name:
                # Skipping empty names, or when the name is missing in the value_description
                logging.warning("No name for value id %d, skipping.", value_id)
                continue
            name = _to_python_identifier(name)
            if name in properties:
                logging.warning("Duplicate name %s, skipping.", name)
                continue
            if type_ is None:
                logging.warning("No type for %s, skipping.", name)
                continue
            getter, setter = None, None
            validate_function = _generate_validate_value_function(name, type_, description)
            if mode in (ValueMode.R, ValueMode.RW):
                getter = partial(_get_value, device, validate_function, type_, value_id)
            if mode in (ValueMode.RW, ValueMode.W):
                setter = partial(_set_value, device, validate_function, type_, value_id)
            if getter is None and setter is None:
                logging.warning("No accessor for %s.", name)
            doc = "Dynamically created property for Lemonbeat value ID {} of device {}.\n" \
                  "Value description:\n{}".format(value_id, device.zoned_address, pretty(description))
            properties[name] = property(getter, setter, None, doc)
        # Replacing the class of this instance with a dynamically created class,
        # because properties can only be set to a class, not an instance.
        self.__doc__ = "Dynamically created Lemonbeat value properties for device {}.".format(device.zoned_address)
        class_name = _to_python_identifier(self.__class__.__name__ + '_' + device.zoned_address)
        self.__class__ = type(class_name, self.__class__.__bases__, properties)

    def _set_attr(self, name, value):
        if name not in self.__class__.__dict__:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
        return super(self.__class__, self).__setattr__(name, value)
