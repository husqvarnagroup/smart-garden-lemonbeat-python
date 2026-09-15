# SPDX-FileCopyrightText: GARDENA GmbH
#
# SPDX-License-Identifier: LGPL-2.0-or-later

# coding=utf-8

"""
Lemonbeat types for data being (de-)serialized.
"""

import copy
import enum
import logging
import math
import xml.etree.ElementTree as ETree
from binascii import hexlify, unhexlify


class RequestTimeoutError(Exception):
    """Exception for representing a low level request timeout error."""
    pass


class UnexpectedLemonbeatEncryptionError(Exception):
    """Exception for representing an error when encryption settings didn't meet expectations."""
    pass


class SocketError(Exception):
    """Exception for representing a low level socket error."""
    pass


class MessageFormatError(Exception):
    """Exception for representing a low level message format error."""
    pass


class MessageParseError(Exception):
    """Exception for representing a message parsing error."""
    pass


def _parse_report(report, id_attribute, element_parser, *, unwrap=True, map_id=int):
    """Parse any type of Lemonbeat report to a dict.

    :param report: report ETree object
    :param id_attribute: name of the id attribute.
    :param element_parser: function to parse each element
    :param unwrap: True, if the list of elements is wrapped in an
                   additional layer in the report ETree. False if the
                   report ETree contains the list directly
    :param map_id: callable to map the attribute id with
    :return: dictionary with elements, keys are taken from the id
             attribute and are optionally mapped with the provided
             function. values are parsed with the provided
             element_parser function.
    """
    if unwrap:
        report = report[0]
    elements = {}
    for element in report:
        element_id = map_id(int(element.attrib.pop(id_attribute)))
        elements[element_id] = element_parser(element)
    return elements


def _key2type(key, *, hex_attribute, number_type):
    """Get Python type for Lemonbeat types.

    :param key: name of the type
    :param hex_attribute: name to use the Hex type for
    :param number_type: Python type to use for numbers
    :return: Python type
    """
    if key == 'number':
        return number_type
    if key == 'string':
        return str
    if key == hex_attribute:
        return Hex
    raise ValueError(f"Invalid attribute key '{key}' for value conversion.")


def _convert_attrib(attrib, *, rename_value_key=None, int_attributes=(), float_attributes=(), hex_attribute=None,
                    string_attribute=None):
    """Convert value types from string to corresponding Python types in Lemonbeat reports.

    :param attrib: dictionary of attributes
    :param rename_value_key: name to rename the value key to. If not
           None it activates automatic value attributes conversion with
           the default names and guarantees the resulting dictionary
           having this key.
    :param int_attributes: names to use the int type for
    :param hex_attribute: name to use the Hex type for instead of the default
    :return: dictionary
    """
    # Use int type for 'number' attribute if desired
    if rename_value_key is not None and 'number' in int_attributes:
        int_attributes = [a for a in int_attributes if a != 'number']
        number_type = int
    else:
        number_type = float

    result = {}
    for key, value in attrib.items():
        if key in int_attributes:
            value = int(value)
        elif key in float_attributes:
            value = float(value)
        elif rename_value_key is not None:
            value = _key2type(key, hex_attribute=hex_attribute, number_type=number_type)(value)
            key = rename_value_key
        elif key == hex_attribute:
            value = Hex(value)
        elif key == string_attribute:
            value = str(value)
        else:
            raise ValueError(f"Invalid attribute key '{key}'.")
        if key in result:
            logging.warning("Multiple occurrences of attrib '%s'", key)
        result[key] = value
    if rename_value_key is not None:
        result.setdefault(rename_value_key)
    return result


class Hex(bytes):
    """Type representing a Lemonbeat hex value."""

    def __new__(cls, value):
        if isinstance(value, int):
            raise TypeError("cannot convert 'int' object to Hex")
        if isinstance(value, str):
            return bytes.__new__(cls, unhexlify(value))
        return bytes.__new__(cls, value)

    def __repr__(self):
        return "%s('%s')" % (self.__class__.__name__, str(self))

    def __str__(self):
        return hexlify(self).decode('ascii')


class BaseElement:
    """Abstract class for Lemonbeat elements."""
    _int_attributes = ()
    _float_attributes = ()
    _hex_attribute = None
    _string_attribute = None

    @property
    def _tag(self):
        raise NotImplementedError

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __repr__(self):
        items = ("%s=%r" % (k, v) for k, v in self.__dict__.items() if v is not None)
        return "%s(%s)" % (self.__class__.__name__, ', '.join(items))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented

        return self.__dict__.__eq__(other.__dict__)

    def toetree(self, *, attrib=None):
        """Convert object to an ETree Element."""
        if attrib is None:
            attrib = {}
        attributes = {k: self._convert_value(k, v) for k, v in self.__dict__.items() if
                      v is not None and not k.startswith("_")}
        attributes.update(attrib)
        return ETree.Element(self._tag, attrib=attributes)

    @classmethod
    def frometree(cls, etree):
        """Return object from a Lemonbeat ETree Element."""
        # TODO input validation
        fields = _convert_attrib(etree.attrib, int_attributes=cls._int_attributes,
                                 float_attributes=cls._float_attributes, hex_attribute=cls._hex_attribute,
                                 string_attribute=cls._string_attribute)
        return cls(**fields)

    def _convert_value(self, key, value):
        if isinstance(value, enum.IntEnum):
            value = value.value

        if key in self._int_attributes:
            return str(int(value))
        elif key in self._float_attributes:
            value = float(value)
            if math.isfinite(value):
                return str(value)
            elif math.isnan(value):
                return 'NaN'
            elif value == float('inf'):
                return 'INF'
            elif value == float('-inf'):
                return '-INF'
            else:
                raise ValueError(f"Field `{key}` has an invalid float value.")
        elif key == self._hex_attribute:
            return str(Hex(value)).upper()
        elif key == self._string_attribute:
            return str(value)
        else:
            raise KeyError(f"Type of attribute `{key}` not specified for class `{self.__name__}`.")


class BaseValueElement(BaseElement):
    """Abstract class for Lemonbeat elements, which contain a number, string or hexBinary attribute."""

    @property
    def _tag(self):
        raise NotImplementedError

    _keep_int = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Tell the code inspector this class has a value attribute,
        # but don't change the order of kwargs and self.__dict__.
        assert hasattr(self, "value")
        self.value = getattr(self, "value")

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented

        # Handle NaN value as equal
        self_value = self.__dict__.get('value')
        other_value = other.__dict__.get('value')
        if isinstance(self_value, float) and math.isnan(self_value) and \
                isinstance(other_value, float) and math.isnan(other_value):
            return {k: v for k, v in self.__dict__.items() if k != 'value'} == \
                {k: v for k, v in other.__dict__.items() if k != 'value'}

        return super().__eq__(other)

    def toetree(self, *, attrib=None):
        """Convert object to an ETree Element."""
        proxy = copy.copy(self)
        value = proxy.__dict__.pop('value')
        if isinstance(value, bytes):  # Hex is derived from bytes
            proxy._hex_attribute = self._hex_attribute
            setattr(proxy, self._hex_attribute, value)
        elif self._keep_int and isinstance(value, int):
            proxy._int_attributes += ('number',)
            proxy.number = int(value)
        elif isinstance(value, (int, float)):
            proxy._float_attributes += ('number',)
            proxy.number = float(value)
        elif isinstance(value, str):
            proxy._string_attribute = 'string'
            proxy.string = value
        elif value is None:
            pass
        else:
            raise TypeError("Field 'value' has an invalid type.")
        return BaseElement.toetree(proxy, attrib=attrib)

    @classmethod
    def frometree(cls, etree):
        # TODO input validation
        fields = _convert_attrib(etree.attrib, rename_value_key='value', int_attributes=cls._int_attributes,
                                 float_attributes=cls._float_attributes, hex_attribute=cls._hex_attribute,
                                 string_attribute=cls._string_attribute)
        if 'value' not in fields:
            logging.warning(f"Instance of class `{cls.__name__}` without value.")
            return cls(value=None, **fields)
        return cls(**fields)
