# SPDX-FileCopyrightText: GARDENA GmbH
#
# SPDX-License-Identifier: LGPL-2.0-or-later

from xml.etree import ElementTree as ETree

from lemonbeat import DeviceDescriptionType, ServiceDescriptionType, Hex
from ._types import BaseElement, _convert_attrib, BaseValueElement


class BaseElementContainer:
    _int_attributes = ()
    _float_attributes = ()
    _hex_attribute = None
    _string_attribute = None
    _value = "value"
    _key_type = int

    @property
    def _tag(self):
        raise NotImplementedError

    @property
    def _key(self):
        raise NotImplementedError

    @property
    def _child_class(self):
        raise NotImplementedError

    def __init__(self, _children, **kwargs):
        if isinstance(_children, dict):
            if self._value is dict:
                self._children = [self._child_class(**{self._key: k, **v}) for k, v in _children.items()]
            else:
                self._children = [self._child_class(**{self._key: k, self._value: v}) for k, v in _children.items()]
        else:
            self._children = _children
        self.__dict__.update(kwargs)

    def __iter__(self):
        return iter(self._children)

    def toetree(self):
        attrib = {k: str(v) for k, v in self.__dict__.items() if not k.startswith('_')}
        etree = ETree.Element(self._tag, attrib=attrib)
        etree.extend([child.toetree() for child in self._children])
        return etree

    def to_dict(self):
        return {self._key_type(getattr(child, self._key)): child.to_dict() for child in self._children}

    @classmethod
    def frometree(cls, etree):
        child_class = cls._child_class
        assert isinstance(child_class, type)
        assert issubclass(child_class, (BaseElementContainer, BaseElement))
        children = [child_class.frometree(e) for e in etree]
        fields = _convert_attrib(etree.attrib, int_attributes=cls._int_attributes,
                                 float_attributes=cls._float_attributes, hex_attribute=cls._hex_attribute,
                                 string_attribute=cls._string_attribute)
        return cls(_children=children, **fields)


class InfoElement(BaseValueElement):
    _tag = "info"
    _int_attributes = ("type_id", "number")
    _hex_attribute = "hex"
    _keep_int = True

    def __init__(self, *, type_id, value):
        super().__init__(type_id=type_id, value=value)

    # TODO: move to base classes
    def to_dict(self):
        return self.value


class ReportDeviceDescription(BaseElementContainer):
    _tag = "device_description_report"
    _key = "type_id"
    _key_type = DeviceDescriptionType
    _child_class = InfoElement


class PartnerElement(BaseElementContainer):
    _tag = "partner"
    _int_attributes = ("partner_id",)
    _key = "type_id"
    _key_type = DeviceDescriptionType
    _child_class = InfoElement


class ServiceElement(BaseElement):
    _tag = "service"
    _int_attributes = ("service_id", "version")


class ReportServiceDescription(BaseElementContainer):
    _tag = "service_description_report"
    _key = "service_id"
    _value = "version"
    _key_type = ServiceDescriptionType
    _child_class = ServiceElement


class BaseSetReportPartnerInformation(BaseElementContainer):
    @property
    def _tag(self):
        raise NotImplementedError

    _key = "partner_id"
    _value = "_children"
    _child_class = PartnerElement


class SetPartnerInformation(BaseSetReportPartnerInformation):
    _tag = "partner_information_set"


class ReportPartnerInformation(BaseSetReportPartnerInformation):
    _tag = "partner_information_report"


class MemoryInformation(BaseElement):
    _tag = "memory_information"
    _int_attributes = ("memory_id", "count", "free_count")

    def __init__(self, *, memory_id, count, free_count):
        super().__init__(memory_id=memory_id, count=count, free_count=free_count)


class ReportMemoryInformation(BaseElementContainer):
    _tag = "memory_information_report"
    _key = "memory_id"
    _value = dict
    _child_class = MemoryInformation


class NumberFormatElement(BaseElement):
    _tag = "number_format"
    _float_attributes = ("min", "max", "step")
    _string_attribute = "unit"


class StringFormatElement(BaseElement):
    _tag = "string_format"
    _int_attributes = ("max_length",)


class HexBinaryFormatElement(BaseElement):
    _tag = "hexBinary_format"
    _int_attributes = ("max_length",)


class ValueDescriptionElement(BaseElement):
    _tag = "value_description"
    _int_attributes = ("value_id", "type_id", "mode", "persistent")
    _string_attribute = "name"

    def __init__(self, value_id, type_id, mode, persistent, name=None, min_log_interval=None, max_log_values=None,
                 virtual=None, **kwargs):
        super().__init__(value_id=value_id, type_id=type_id, mode=mode, persistent=persistent, name=name,
                         min_log_interval=min_log_interval, max_log_values=max_log_values, virtual=virtual)
        type_ = kwargs.pop("type")
        if type_ in (int, float):
            self._child = NumberFormatElement(**kwargs)
        elif type_ == str:
            self._child = StringFormatElement(**kwargs)
        elif type_ == Hex:
            self._child = HexBinaryFormatElement(**kwargs)
        else:
            raise ValueError

    def toetree(self, *, attrib=None):
        etree = super().toetree(attrib=attrib)
        etree.append(self._child.toetree())
        return etree

    @classmethod
    def frometree(cls, etree):
        raise NotImplementedError("The method ValueDescriptionElement.frometree() is not implemented yet.")


class ReportValueDescription(BaseElementContainer):
    _tag = "value_description_report"
    _key = "value_id"
    _value = dict
    _child_class = ValueDescriptionElement


class SetCalendarTimezone(BaseElement):
    _tag = "calendar_set_timezone"
    _int_attributes = ("offset",)


class ReportCalendarTimezone(BaseElement):
    _tag = "calendar_report_timezone"
    _int_attributes = ("offset",)


class InitFirmware(BaseElement):
    _tag = "firmware_init"
    _int_attributes = ("firmware_id", "size")
    _hex_attribute = "checksum"


class ReportFirmware(BaseElement):
    _tag = "firmware_report"
    _int_attributes = ("expected_offset", "status")


class FirmwareData(BaseElement):
    _tag = "firmware_data"
    _int_attributes = ("offset",)

    def toetree(self, *, attrib=None):
        raise NotImplementedError("The method FirmwareData.toetree() is not implemented yet.")

    @classmethod
    def frometree(cls, etree):
        firmware_data = super().frometree(etree)
        # TODO input validation
        firmware_data.chunk = Hex(etree[0].text)
        return firmware_data


class ReportStatusLevel(BaseElement):
    _tag = "status_report_level"
    _int_attributes = ("level",)
