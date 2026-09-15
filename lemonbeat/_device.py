# SPDX-FileCopyrightText: GARDENA GmbH
#
# SPDX-License-Identifier: LGPL-2.0-or-later

# coding=utf-8

"""
The Lemonbeat device object and some helper functions.
"""

import logging
import warnings
import xml.etree.ElementTree as ETree

from ._configuration import ConfigurationMixin
from ._defines import DEFAULT_TIMEOUT
from ._device_description import DeviceDescriptionType, RadioMode
from ._firmware import FirmwareMixin
from ._memory_information import MemoryInformationType
from ._message import _send, _verify_message_format
from ._partner import PartnerMixin
from ._service import Service, ServiceDescriptionType
from ._types import MessageFormatError, MessageParseError, BaseValueElement, _parse_report, _key2type, _convert_attrib
from ._value import ValueMode


def _update_map(attrs, key, func):
    """Map and update dictionary element with the provided map function.

    :param attrs: dictionary
    :param key: key of the element in the dictionary
    :param func: map function
    """
    if key in attrs:
        attrs[key] = func(attrs[key])


def _is_int(value):
    """Check if float value is integer

    :param value: float value
    :return: True if value is integer
    """
    try:
        return float(value).is_integer()
    except (TypeError, ValueError):
        return False


def _parse_value_description_element(etree):
    # TODO: better input validation, check required values, value types, set invalid values to None and output warnings
    if len(etree) != 1:
        raise MessageParseError
    type_ = _key2type(etree[0].tag.replace('{urn:value_descriptionxsd}', '').replace('_format', ''),
                      hex_attribute="hexBinary", number_type=float)
    if type_.__class__ is not type:
        raise MessageParseError

    attrib = etree.attrib
    attrib.update(etree[0].attrib)
    _update_map(attrib, 'type_id', int)
    _update_map(attrib, 'mode', lambda v: ValueMode(int(v)))
    _update_map(attrib, 'persistent', lambda v: bool(int(v)))
    # not converting name
    # ignoring min_log_interval
    # ignoring max_log_values
    _update_map(attrib, 'virtual', lambda v: bool(int(v)))

    if type_ == float:
        if _is_int(attrib.get('min')) and _is_int(attrib.get('max')) and _is_int(attrib.get('step')):
            type_ = int
        # not converting unit
        _update_map(attrib, 'min', lambda v: type_(float(v)))
        _update_map(attrib, 'max', lambda v: type_(float(v)))
        _update_map(attrib, 'step', lambda v: type_(float(v)))
    else:
        _update_map(attrib, 'max_length', int)
        # not supported valid_value child tags of string_format

    attrib['type'] = type_
    return etree.attrib


def _parse_value_description(etree):
    return _parse_report(etree, 'value_id', _parse_value_description_element)


def _map_device_description_type(id_):
    try:
        return DeviceDescriptionType(id_)
    except ValueError:
        logging.warning("Unknown device description type %d", id_)
        return id_


def _map_memory_information_tag(id_):
    try:
        return MemoryInformationType(id_)
    except ValueError:
        logging.warning("Unknown memory information tag %d", id_)
        return id_


def _map_service_description_tag(id_):
    try:
        return ServiceDescriptionType(id_)
    except ValueError:
        logging.warning("Unknown service description tag %d", id_)
        return id_


def _parse_device_description_element(etree):
    a = _convert_attrib(etree, int_attributes=('type_id', 'number'), rename_value_key=(), hex_attribute='hex')
    return a[()]


def _parse_device_description(etree):
    device_description = _parse_report(etree, 'type_id', _parse_device_description_element,
                                       map_id=_map_device_description_type)
    _update_map(device_description, DeviceDescriptionType.RADIO_MODE, RadioMode)
    return device_description


def _parse_memory_information_element(etree):
    return _convert_attrib(etree, int_attributes=('memory_id', 'count', 'free_count'))


def _parse_memory_information(etree):
    memory_information = _parse_report(etree, 'memory_id', _parse_memory_information_element,
                                       map_id=_map_memory_information_tag)
    return memory_information


def _parse_service_description_element(etree):
    return _convert_attrib(etree, int_attributes=('service_id', 'version'))


def _parse_service_description(etree):
    service_description = _parse_report(etree, 'service_id', _parse_service_description_element,
                                        map_id=_map_service_description_tag)
    return service_description


def _parse_value(etree):
    return [ReportValue.frometree(element) for element in etree]


class BaseSetReportValue(BaseValueElement):
    """Abstract class for SetValue and ReportValue."""
    _int_attributes = ("value_id", "timestamp")
    _hex_attribute = "hexBinary"

    @property
    def _tag(self):
        raise NotImplementedError

    def __init__(self, *, value_id, value, timestamp=None):
        super().__init__(value_id=value_id, value=value, timestamp=timestamp)


class SetValue(BaseSetReportValue):
    """Object used for set_value."""
    _tag = "value_set"


class ReportValue(BaseSetReportValue):
    """Object used for report_value."""
    _tag = "value_report"


class Device(PartnerMixin, FirmwareMixin, ConfigurationMixin):
    """Object representing a Lemonbeat device."""

    def __init__(self, gateway, address, *, go_to_sleep=None, timeout=DEFAULT_TIMEOUT):
        """Create a device object.

        :param gateway: Gateway object the device is reachable at.
        :param address: IPv6 address as string of the device.
        :param timeout: Timeout in seconds for all requests to that device.
        """
        self.gateway = gateway
        try:
            self.address = address
        except AttributeError:
            # The Gateway subclass dynamically gets the address
            pass
        self.go_to_sleep = go_to_sleep
        self.timeout = timeout
        super().__init__()

    def _send_message(self, service, etrees, *, encrypted=True):
        _send(self.gateway.select, self.gateway.socket, self.gateway.bind_address, self.address, service, etrees,
              go_to_sleep=self.go_to_sleep, timeout=None, encrypted=encrypted)

    def _send_request(self, service, etrees, *, encrypted=True, **kwargs):
        try:
            go_to_sleep = kwargs.pop('go_to_sleep')
        except KeyError:
            go_to_sleep = self.go_to_sleep
        else:
            warnings.warn("_send_request() with keyword argument 'go_to_sleep' is deprecated", DeprecationWarning)

        try:
            timeout = kwargs.pop('timeout')
        except KeyError:
            timeout = self.timeout
        else:
            assert timeout is not None
            warnings.warn("_send_request() with keyword argument 'timeout' is deprecated", DeprecationWarning)

        if kwargs:
            raise TypeError(f"_send_request() got an unexpected keyword argument '{next(iter(kwargs))}'")

        response = _send(self.gateway.select, self.gateway.socket, self.gateway.bind_address, self.address, service,
                         etrees, go_to_sleep=go_to_sleep, timeout=timeout, encrypted=encrypted)

        if not _verify_message_format(service, response):
            raise MessageFormatError
        return [e for e in response[0]]

    def _send_request_raw(self, service, etrees):
        warnings.warn("_send_request_raw is deprecated, use _send_request instead", DeprecationWarning)
        return _send(self.gateway.select, self.gateway.socket, self.gateway.bind_address, self.address, service, etrees,
                     go_to_sleep=self.go_to_sleep, timeout=self.timeout)

    @property
    def zoned_address(self):
        """Device's IPv6 address with Zone ID i.e. name of the interface."""
        return self.address + '%' + self.gateway.interface

    def include(self):
        """Send network management include message."""
        etree = ETree.Element("network_include")
        etree.text = self.gateway.inclusion_message
        self._send_message(Service.NETWORK_MANAGEMENT, [etree], encrypted=False)

    def exclude(self):
        """Send network management exclude message."""
        etree = ETree.Element("device_description_set")
        etree.append(ETree.Element("info", number="0", type_id=str(DeviceDescriptionType.INCLUDED.value)))
        self._send_message(Service.DEVICE_DESCRIPTION, [etree])

    def get_device_description(self):
        """Get device description."""
        response = self._send_request(Service.DEVICE_DESCRIPTION, [ETree.Element("device_description_get")])
        return _parse_device_description(response)

    def get_device_description_raw(self):
        """Get device description. Returns raw XML.

        This method is deprecated, use get_device_description instead.
        """
        warnings.warn("get_device_description_raw is deprecated, use get_device_description instead",
                      DeprecationWarning)
        response = self._send_request_raw(Service.DEVICE_DESCRIPTION, [ETree.Element("device_description_get")])
        return response[0]

    def get_memory_information(self):
        """Get memory information."""
        response = self._send_request(Service.MEMORY_INFORMATION, [ETree.Element("memory_information_get")])
        return _parse_memory_information(response)

    def get_service_description(self):
        """Get service description."""
        response = self._send_request(Service.SERVICE_DESCRIPTION, [ETree.Element("service_description_get")])
        return _parse_service_description(response)

    def get_value_description(self, value_description_id=None):
        """Get value description by id or all value descriptions."""
        # TODO: also allow a list as value_description_id
        attrib = {}
        if value_description_id is not None:
            attrib = {'value_description_id': str(value_description_id)}
        response = self._send_request(Service.VALUE_DESCRIPTION, [ETree.Element("value_description_get", **attrib)])
        return _parse_value_description(response)

    def get_value_description_raw(self):
        """Get value description. Returns raw XML.

        This method is deprecated, use get_value_description instead.
        """
        warnings.warn("get_value_description_raw is deprecated, use get_value_description instead", DeprecationWarning)
        return self._send_request_raw(Service.VALUE_DESCRIPTION, [ETree.Element("value_description_get")])

    def get_value(self, value_id=None):
        """Get value selected by value_id or all values."""
        # TODO: also allow a list as value_id
        attrib = {}
        if value_id is not None:
            attrib = {'value_id': str(value_id)}
        response = self._send_request(Service.VALUE, [ETree.Element("value_get", **attrib)])
        return _parse_value(response)

    def get_value_raw(self, value_id=None):
        """Get value selected by value_id or all values. Returns raw XML.

        This method is deprecated, use get_value instead.
        """
        warnings.warn("get_value_raw is deprecated, use get_value instead", DeprecationWarning)
        attrib = {}
        if value_id is not None:
            attrib = {'value_id': str(value_id)}
        response = self._send_request_raw(Service.VALUE, [ETree.Element("value_get", **attrib)])
        return response

    def set_value(self, value_id, value):
        """Send 'value_set' message."""
        # TODO: also allow to set a list of values
        etree = SetValue(value_id=value_id, value=value, timestamp=0).toetree()
        self._send_message(Service.VALUE, [etree])

    def get_status_level(self):
        """Send 'status_get_level' message."""
        response = self._send_request(Service.STATUS, [ETree.Element("status_get_level")])
        return int(response[0].attrib['level'])

    def set_status_level(self, level):
        """Send 'status_set_level' message."""
        self._send_message(Service.STATUS, [ETree.Element("status_set_level", level=str(int(level)))])
