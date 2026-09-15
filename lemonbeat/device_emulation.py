# SPDX-FileCopyrightText: GARDENA GmbH
#
# SPDX-License-Identifier: LGPL-2.0-or-later

__version__ = "0.1.0"

__all__ = [
    "ABSENT",
    "FROM_CACHE",
    "DeviceEmulation",
    "RadioModuleEmulation",
]

import copy
import logging
import socket
import threading

try:
    from functools import cached_property
except ImportError:
    # Use uncached property for Python < 3.8, expecting only a small performance loss.
    cached_property = property

import crcmod

from lemonbeat import DeviceDescriptionType, RadioMode, Hex, ServiceDescriptionType, MemoryInformationType, Service, \
    Gateway, SetValue, ReportValue, ValueMode, FirmwareReportStatus, Status
from ._device_emulation_types import ReportDeviceDescription, ReportServiceDescription, ReportValueDescription, \
    ReportMemoryInformation, SetPartnerInformation, ReportPartnerInformation, SetCalendarTimezone, \
    ReportCalendarTimezone, InitFirmware, ReportFirmware, FirmwareData, ReportStatusLevel
from ._gateway import calculate_dongle_address
from ._message import _etrees_to_xml, _pretty_addr, _pretty, _xml_to_exi

ABSENT = object()  # sentinel value to mark absence of a value
FROM_CACHE = object()  # sentinel value to mark an intent of using entity from cache

crc16 = crcmod.predefined.mkPredefinedCrcFun("xmodem")


def address_tuple(address):
    return socket.getaddrinfo(address, None, family=socket.AF_INET6, proto=socket.IPPROTO_UDP)[0][4]


class DeviceEmulation:
    DEFAULT_DEVICE_DESCRIPTION_TRANSMIT_INTERVAL = 10

    DEFAULT_DEVICE_DESCRIPTION = {
        DeviceDescriptionType.DEVICE_TYPE: None,
        DeviceDescriptionType.DEVICE_MANUFACTURER: 3,
        DeviceDescriptionType.SGTIN: None,
        DeviceDescriptionType.MAC_ADDRESS: None,
        DeviceDescriptionType.HARDWARE_VERSION: '1.0.0',
        DeviceDescriptionType.BOOTLOADER_VERSION: '4.0.0',
        DeviceDescriptionType.STACK_VERSION: '1.5.3',
        DeviceDescriptionType.APPLICATION_VERSION: None,
        DeviceDescriptionType.PROTOCOL: 1,
        DeviceDescriptionType.DEVICE_PRODUCT: 2,
        DeviceDescriptionType.INCLUDED: 0,
        DeviceDescriptionType.NAME: None,
        DeviceDescriptionType.RADIO_MODE: RadioMode.ALWAYS_ONLINE,
        DeviceDescriptionType.WAKEUP_INTERVAL: 333,
        DeviceDescriptionType.WAKEUP_OFFSET: 0,
        DeviceDescriptionType.WAKEUP_CHANNEL: 3,
        DeviceDescriptionType.CHANNEL_MAP: Hex('10080804'),
        DeviceDescriptionType.CHANNEL_SCAN_TIME: 10000,
        DeviceDescriptionType.IPV6_ADDRESS: None,
        DeviceDescriptionType.WAKEUP_NOW: None,
        DeviceDescriptionType.DIVERSITY_MODE: 0,
        DeviceDescriptionType.TX_POWER: 14,
    }

    DEFAULT_SERVICE_DESCRIPTION = {
        ServiceDescriptionType.MEMORY_INFORMATION: 1,
        ServiceDescriptionType.DEVICE_DESCRIPTION: 1,
        ServiceDescriptionType.VALUE_DESCRIPTION: 1,
        ServiceDescriptionType.VALUE: 1,
        ServiceDescriptionType.PARTNER_INFORMATION: 1,
        ServiceDescriptionType.ACTION: 1,
        ServiceDescriptionType.CALCULATION: 1,
        ServiceDescriptionType.TIMER: 1,
        ServiceDescriptionType.CALENDAR: 1,
        ServiceDescriptionType.STATE_MACHINE: 1,
        ServiceDescriptionType.FIRMWARE_UPDATE: 1,
        ServiceDescriptionType.STATUS: 1,
        ServiceDescriptionType.CONFIGURATION: 1,
    }

    DEFAULT_MOCK_MEMORY_INFORMATION = {
        MemoryInformationType.ACTION_ITEMS: {'count': 1, 'free_count': 1},
        MemoryInformationType.CALCULATION: {'count': 1, 'free_count': 1},
        MemoryInformationType.TIMER: {'count': 1, 'free_count': 1},
        MemoryInformationType.CALENDER: {'count': 1, 'free_count': 1},
        MemoryInformationType.STATEMACHINE: {'count': 1, 'free_count': 1},
        MemoryInformationType.STATEMACHINE_TRANSACTIONS: {'count': 1, 'free_count': 1},
    }

    @cached_property
    def service_handler_map(self):
        return {
            Service.VALUE: self.handle_value,
            Service.DEVICE_DESCRIPTION: self.handle_device_description,
            Service.NETWORK_MANAGEMENT: self.handle_network_management,
            Service.VALUE_DESCRIPTION: self.handle_value_description,
            Service.SERVICE_DESCRIPTION: self.handle_service_description,
            Service.MEMORY_INFORMATION: self.handle_memory_information,
            Service.PARTNER_INFORMATION: self.handle_partner_information,
            Service.CALENDAR: self.handle_calendar,
            Service.FIRMWARE_UPDATE: self.handle_firmware_update,
            Service.STATUS: self.handle_status,
            Service.CONFIGURATION: self.handle_configuration,
        }

    def __init__(self, *, address, controller_address, device_description=None, service_description=None,
                 value_description=None, partner_information_count=1, mock_memory_information=None):
        self.address = address
        if address is not None:
            address = address_tuple(address)
        if controller_address is not None:
            controller_address = address_tuple(controller_address)

        self.controller = Gateway(inclusion_message=None, address=controller_address, bind_address=address)

        dd = copy.deepcopy(self.DEFAULT_DEVICE_DESCRIPTION)
        if device_description is not None:
            dd.update(device_description)
        self.device_description = {k: v for k, v in dd.items() if v is not ABSENT}

        sd = copy.deepcopy(self.DEFAULT_SERVICE_DESCRIPTION)
        if service_description is not None:
            sd.update(service_description)
        self.service_description = {k: v for k, v in sd.items() if v is not ABSENT}

        mmi = copy.deepcopy(self.DEFAULT_MOCK_MEMORY_INFORMATION)
        if mock_memory_information is not None:
            mmi.update(mock_memory_information)
        self.mock_memory_information = {k: v for k, v in mmi.items() if v is not ABSENT}

        if value_description is None:
            value_description = {}
        self.value_description = copy.deepcopy(value_description)
        self.value = {value_id: None for value_id in self.value_description}

        self.partner_information_count = partner_information_count
        self.partner_information = {}

        self.inclusion_message = None
        self.timezone_offset = 0
        self.device_description_transmit_interval = self.DEFAULT_DEVICE_DESCRIPTION_TRANSMIT_INTERVAL
        self.stop_device_description_sender = None

        self.firmware_update_current_id = None
        self.firmware_update = {}

    @property
    def memory_information(self):
        return {
            MemoryInformationType.VALUE: {'count': len(self.value_description), 'free_count': 0},
            MemoryInformationType.PARTNER_INFORMATION: {
                'count': self.partner_information_count,
                'free_count': self.partner_information_count - len(self.partner_information)
            },
            **self.mock_memory_information,
        }

    @property
    def included(self):
        return self.device_description[DeviceDescriptionType.INCLUDED] != 0

    @included.setter
    def included(self, value):
        self.device_description[DeviceDescriptionType.INCLUDED] = 1 if value else 0

    def _send(self, service, data, sock_addr=None):
        if data is None:
            return
        etrees = [d.toetree() for d in data]
        self._send_message(service, etrees, sock_addr)

    def _send_message(self, service, etrees, sock_addr=None):
        if sock_addr is not None:
            xml = _etrees_to_xml(service, etrees)
            logging.info("sending %s data to %s\n"
                         "======================\n"
                         "%s"
                         "======================",
                         service.name.lower(), _pretty_addr(sock_addr[1]), _pretty(xml))
            exi = _xml_to_exi(service, xml)
            sock_addr[0].sendto(exi, sock_addr[1])
        else:
            self.controller._send_message(service, etrees)

    def send_device_description(self, *, sock_addr=None):
        self._send(Service.DEVICE_DESCRIPTION, [ReportDeviceDescription(self.device_description)], sock_addr)

    def report_value(self, value_id, value=FROM_CACHE, *, timestamp=0, sock_addr=None):
        if value is FROM_CACHE:
            value = self.value[value_id]
        self._send(Service.VALUE, [ReportValue(value_id=value_id, value=value, timestamp=timestamp)], sock_addr)

    @staticmethod
    def _check_element_count(service, etree, *, allow_multi=False):
        if len(etree[0]) == 0:
            logging.warning(f"Ignoring empty {service.name.lower()} message.")
            return False
        elif len(etree[0]) > 1 and not allow_multi:
            logging.warning(f"Ignoring subsequent commands in {service.name.lower()} message.")
        return True

    def _generic_handle_commands(self, service, sock_addr, etree, command_family, element_key, access_dict,
                                 report_convert_fun, *, set_fun=None, has_delete=False):
        if not self._check_element_count(service, etree, allow_multi=True):
            return
        command_family_txt = command_family.replace("_", " ")

        report_ids = None
        for element in etree[0]:
            if element.tag == f'{{{service.xmlns}}}{command_family}_get':
                element_id = element.attrib.get(element_key)
                if element_id is not None:
                    element_id = int(element_id)
                if report_ids is None:
                    report_ids = set()
                report_ids.add(element_id)
            elif set_fun is not None and element.tag == f'{{{service.xmlns}}}{command_family}_set':
                logging.info(f"Setting {command_family_txt} for device {self.address}.")
                set_fun(element)
            elif has_delete is not None and element.tag == f'{{{service.xmlns}}}{command_family}_delete':
                element_id = element.attrib.get(element_key)
                if element_id is not None:
                    logging.info(f"Deleting {command_family_txt} for device {self.address}.")
                    try:
                        del access_dict[int(element_id)]
                    except KeyError:  # ignore if not present
                        pass
                else:
                    logging.info(f"Deleting all {command_family_txt} for device {self.address}.")
                    access_dict.clear()
            else:
                logging.warning(f"Unhandled {command_family_txt} command for device {self.address}.")

        if report_ids is not None:
            logging.info(f"Replying with {command_family_txt} report for device {self.address}.")
            if None in report_ids:
                # report all
                report_dict = access_dict
            else:
                report_dict = {i: access_dict[i] for i in report_ids if i in access_dict}
            self._send(service, report_convert_fun(report_dict), sock_addr)

    def handle_device_description(self, sock_addr, etree):
        if not self._check_element_count(Service.DEVICE_DESCRIPTION, etree):
            return

        if etree[0][0].tag == '{urn:device_descriptionxsd}device_description_get':
            logging.info(f"Replying with device description for device {self.address}.")
            self.send_device_description(sock_addr=sock_addr)
        elif etree[0][0].tag == '{urn:device_descriptionxsd}device_description_set':
            if len(etree[0][0]) == 0:
                logging.warning(f"Ignoring empty device description set command.")
            for element in etree[0][0]:
                if element.tag != '{urn:device_descriptionxsd}info':
                    logging.warning(f"Ignoring device description set element for device {self.address}.")
                    continue

                type_id = element.attrib.get("type_id")
                number = element.attrib.get("number")
                if type_id == str(int(DeviceDescriptionType.INCLUDED)) and number == "0":
                    logging.info(f"Excluding device {self.address}.")
                    self.included = False
                elif type_id == str(int(DeviceDescriptionType.WAKEUP_CHANNEL)) and number is not None:
                    logging.info(f"Updating wakeup channel for device {self.address}.")
                    self.device_description[DeviceDescriptionType.WAKEUP_CHANNEL] = int(number)
                else:
                    logging.warning(f"Unhandled device description set command for device {self.address}.")
        else:
            logging.warning(f"Unhandled device description command for device {self.address}.")

    def handle_service_description(self, sock_addr, etree):
        if not self._check_element_count(Service.SERVICE_DESCRIPTION, etree):
            return

        if etree[0][0].tag == '{urn:service_descriptionxsd}service_description_get':
            logging.info(f"Replying with service description for device {self.address}.")
            self._send(Service.SERVICE_DESCRIPTION, [ReportServiceDescription(self.service_description)], sock_addr)
        else:
            logging.warning(f"Unhandled service description command for device {self.address}.")

    def handle_value_description(self, sock_addr, etree):
        self._generic_handle_commands(
            Service.VALUE_DESCRIPTION, sock_addr, etree, "value_description", "value_description_id",
            self.value_description, lambda dct: [ReportValueDescription(dct)]
        )

    def handle_value(self, sock_addr, etree):
        def set_value(element):
            set_v = SetValue.frometree(element)
            self.value[set_v.value_id] = set_v.value
            self.set_value_hook(value_id=set_v.value_id, value=set_v.value, timestamp=set_v.timestamp)

        self._generic_handle_commands(
            Service.VALUE, sock_addr, etree, "value", "value_id", self.value,
            lambda dct: [ReportValue(value_id=k, value=v, timestamp=0) for k, v in dct.items()], set_fun=set_value
        )

    def handle_memory_information(self, sock_addr, etree):
        if not self._check_element_count(Service.MEMORY_INFORMATION, etree):
            return

        if etree[0][0].tag == '{urn:memory_informationxsd}memory_information_get':
            logging.info(f"Replying with memory information for device {self.address}.")
            self._send(Service.MEMORY_INFORMATION, [ReportMemoryInformation(self.memory_information)], sock_addr)
        else:
            logging.warning(f"Unhandled memory information command for device {self.address}.")

    def handle_partner_information(self, sock_addr, etree):
        def set_partner_information(element):
            for partner in SetPartnerInformation.frometree(element):
                self.partner_information.setdefault(partner.partner_id, {}).update(partner.to_dict())

        self._generic_handle_commands(Service.PARTNER_INFORMATION, sock_addr, etree, "partner_information",
                                      "partner_id",
                                      self.partner_information, lambda dct: [ReportPartnerInformation(dct)],
                                      set_fun=set_partner_information, has_delete=True)

    def handle_network_management(self, _sock_addr, etree):
        if not self._check_element_count(Service.NETWORK_MANAGEMENT, etree):
            return

        if etree[0][0].tag == '{urn:network_managementxsd}network_include':
            logging.info(f"Marking device {self.address} as included.")
            self.inclusion_message = etree[0][0].text.upper()
            self.included = True
            logging.info(f"Sending updated device description for device {self.address}")
            self.send_device_description()
        else:
            logging.warning(f"Unhandled network management command for device {self.address}.")

    def handle_configuration(self, _sock_addr, etree):
        if not self._check_element_count(Service.CONFIGURATION, etree):
            return

        if etree[0][0].tag == '{urn:configurationxsd}config_mode_set':
            logging.info(f"Ignoring config mode set command for device {self.address}.")
        else:
            logging.warning(f"Unhandled configuration command for device {self.address}.")

    def handle_calendar(self, sock_addr, etree):
        if not self._check_element_count(Service.CALENDAR, etree):
            return

        if etree[0][0].tag == '{urn:calendarxsd}calendar_set_timezone':
            set_timezone = SetCalendarTimezone.frometree(etree[0][0])
            logging.info(f"Setting calendar time zone for device {self.address}.")
            self.timezone_offset = set_timezone.offset
        elif etree[0][0].tag == '{urn:calendarxsd}calendar_get_timezone':
            logging.info(f"Replying with calendar time zone for device {self.address}.")
            self._send(Service.CALENDAR, [ReportCalendarTimezone(offset=self.timezone_offset)], sock_addr)
        else:
            logging.warning(f"Unhandled calendar command for device {self.address}.")

    def handle_firmware_update(self, sock_addr, etree):
        if not self._check_element_count(Service.FIRMWARE_UPDATE, etree):
            return

        if etree[0][0].tag == '{urn:firmware_updatexsd}firmware_init':
            init_firmware = InitFirmware.frometree(etree[0][0])
            self.firmware_update_current_id = init_firmware.firmware_id
            try:
                previous_state = self.firmware_update[init_firmware.firmware_id].copy()
            except KeyError:
                previous_state = None
            self.firmware_update[init_firmware.firmware_id] = {
                "size": init_firmware.size,
                "checksum": int.from_bytes(init_firmware.checksum, "big"),
                "current_size": 0,
                "running_crc16": 0,
                "max_chunk_size": 0,
            }

            logging.info(f"Firmware upload init for device {self.address}.")
            ctx = {
                "id": self.firmware_update_current_id,
                "state": self.firmware_update[self.firmware_update_current_id],
                "previous_state": previous_state,
                "response": [ReportFirmware(expected_offset=0, status=FirmwareReportStatus.OK)],
            }
            self.firmware_init_hook(ctx)
            self._send(Service.FIRMWARE_UPDATE, ctx["response"], sock_addr)
        elif etree[0][0].tag == '{urn:firmware_updatexsd}firmware_data':
            firmware_data = FirmwareData.frometree(etree[0][0])

            if self.firmware_update_current_id not in self.firmware_update:
                logging.info(f"Firmware upload not initialized for device {self.address}.")
                self._send(Service.FIRMWARE_UPDATE,
                           [ReportFirmware(expected_offset=0, status=FirmwareReportStatus.NOT_INITIALIZED)], sock_addr)
                return

            firmware_update = self.firmware_update[self.firmware_update_current_id]
            expected_offset = firmware_update["current_size"]

            if firmware_data.offset != expected_offset:
                logging.info(f"Firmware upload wrong offset for device {self.address}.")
                self._send(Service.FIRMWARE_UPDATE,
                           [ReportFirmware(expected_offset=expected_offset, status=FirmwareReportStatus.WRONG_OFFSET)],
                           sock_addr)
                return

            new_expected_offset = expected_offset + len(firmware_data.chunk)
            if new_expected_offset > firmware_update["size"]:
                logging.info(f"Firmware upload data overflow for device {self.address}.")
                self._send(Service.FIRMWARE_UPDATE,
                           [ReportFirmware(expected_offset=expected_offset, status=FirmwareReportStatus.DATA_OVERFLOW)],
                           sock_addr)
                return

            firmware_update["current_size"] = new_expected_offset
            firmware_update["running_crc16"] = crc16(firmware_data.chunk, crc=firmware_update["running_crc16"])
            firmware_update["max_chunk_size"] = max(firmware_update["max_chunk_size"], len(firmware_data.chunk))

            logging.info(f"Firmware upload data received for device {self.address}.")
            ctx = {
                "id": self.firmware_update_current_id,
                "state": firmware_update,
                "response": [ReportFirmware(expected_offset=new_expected_offset, status=FirmwareReportStatus.OK)],
            }
            self.firmware_data_hook(ctx)
            self._send(Service.FIRMWARE_UPDATE, ctx["response"], sock_addr)
        elif etree[0][0].tag == '{urn:firmware_updatexsd}firmware_update_start':
            firmware_update = self.firmware_update[self.firmware_update_current_id] if \
                self.firmware_update_current_id is not None else None
            if firmware_update is None or firmware_update["current_size"] != firmware_update["size"]:
                # The Lemonbeat stack seems to ignore the command if the upload not finished.
                logging.info(f"Ignoring firmware update start command for device {self.address}.")
                return

            # assuming every firmware_id is using crc16
            if firmware_update["running_crc16"] != firmware_update["checksum"]:
                logging.info(f"Replying with firmware update crc mismatch for device {self.address}.")
                self._send(Service.FIRMWARE_UPDATE,
                           [ReportFirmware(expected_offset=firmware_update["current_size"],
                                           status=FirmwareReportStatus.CHECKSUM_ERROR_IN_RECEIVED_DATA)],
                           sock_addr)
                return

            logging.info(f"Successful firmware update start command for device {self.address}.")
            ctx = {
                "id": self.firmware_update_current_id,
                "state": firmware_update,
                "response": [
                    ReportFirmware(expected_offset=firmware_update["current_size"], status=FirmwareReportStatus.OK)],
            }
            self.firmware_update_start_hook(ctx)
            self._send(Service.FIRMWARE_UPDATE, ctx["response"], sock_addr)
        else:
            logging.warning(f"Unhandled firmware update command for device {self.address}.")

    def handle_status(self, sock_addr, etree):
        if not self._check_element_count(Service.STATUS, etree):
            return

        if etree[0][0].tag == '{urn:statusxsd}status_get_level':
            self._send(Service.STATUS, [ReportStatusLevel(level=Status.Level.ERROR)], sock_addr)
        else:
            logging.warning(f"Unhandled status commands for device {self.address}.")

    def start_service(self, service):
        self.controller.start_service_listener(service, raw="sock_addr", handler=self.service_handler_map[service],
                                               listen_any=False)

    def start_services(self):
        for service in self.service_handler_map:
            self.start_service(service)

    def start_device_description_sender(self, transmit_interval=None):
        def send():
            if not self.included:
                logging.info(f"sending device description for device {self.address}.")
                self.send_device_description()

        def run():
            send()
            while not self.stop_device_description_sender.wait(self.device_description_transmit_interval):
                send()
            self.stop_device_description_sender = None

        if self.stop_device_description_sender is not None:
            raise RuntimeError(f"Device Description Sender already running for device {self.address}.")

        if transmit_interval is not None:
            self.device_description_transmit_interval = transmit_interval

        self.stop_device_description_sender = threading.Event()
        t = threading.Thread(target=run)
        t.daemon = True
        t.start()

    def stop_device_description_sender(self):
        self.stop_device_description_sender.set()

    def set_value_hook(self, *, value_id, value, timestamp):
        pass

    def firmware_init_hook(self, context):
        pass

    def firmware_data_hook(self, context):
        pass

    def firmware_update_start_hook(self, context):
        pass


class RadioModuleEmulation(DeviceEmulation):
    DEFAULT_DEVICE_DESCRIPTION = {
        DeviceDescriptionType.DEVICE_TYPE: 1,
        DeviceDescriptionType.DEVICE_MANUFACTURER: 2,
        DeviceDescriptionType.SGTIN: None,
        DeviceDescriptionType.MAC_ADDRESS: None,
        DeviceDescriptionType.HARDWARE_VERSION: '1',
        DeviceDescriptionType.BOOTLOADER_VERSION: '4.1.0',
        DeviceDescriptionType.STACK_VERSION: '1.5.3',
        DeviceDescriptionType.APPLICATION_VERSION: '1.5.3',
        DeviceDescriptionType.PROTOCOL: 1,
        DeviceDescriptionType.DEVICE_PRODUCT: 1,
        DeviceDescriptionType.INCLUDED: 0,
        DeviceDescriptionType.NAME: 'DONGLE',
        DeviceDescriptionType.RADIO_MODE: RadioMode.ALWAYS_ONLINE,
        DeviceDescriptionType.WAKEUP_INTERVAL: 0,
        DeviceDescriptionType.WAKEUP_OFFSET: 0,
        DeviceDescriptionType.WAKEUP_CHANNEL: 3,
        DeviceDescriptionType.CHANNEL_MAP: Hex('10080804'),
        DeviceDescriptionType.CHANNEL_SCAN_TIME: 10000,
        DeviceDescriptionType.TX_POWER: 14,
    }

    DEFAULT_SERVICE_DESCRIPTION = {
        ServiceDescriptionType.MEMORY_INFORMATION: 1,
        ServiceDescriptionType.DEVICE_DESCRIPTION: 1,
        ServiceDescriptionType.VALUE_DESCRIPTION: 1,
        ServiceDescriptionType.VALUE: 1,
        ServiceDescriptionType.PARTNER_INFORMATION: 1,
        ServiceDescriptionType.STATUS: 1,
        ServiceDescriptionType.CONFIGURATION: 1,
        ServiceDescriptionType.CHANNEL_SCAN: 1,
    }

    DEFAULT_MOCK_MEMORY_INFORMATION = {}

    @cached_property
    def service_handler_map(self):
        shm = super().service_handler_map
        del shm[Service.CALENDAR]
        del shm[Service.FIRMWARE_UPDATE]
        return shm

    def __init__(self, *, address=None, controller_address, **kwargs):
        if address is None and controller_address is not None:
            address = calculate_dongle_address(address_tuple(controller_address))

        kwargs.setdefault("value_description", {
            1: {'mode': ValueMode.RW, 'name': 'Mac Sequence Count', 'persistent': False, 'type_id': 18, 'max_length': 4,
                'type': Hex},
        })
        kwargs.setdefault("partner_information_count", 70)
        super().__init__(address=address, controller_address=controller_address, **kwargs)
