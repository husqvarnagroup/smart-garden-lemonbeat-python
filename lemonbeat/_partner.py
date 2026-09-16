# SPDX-FileCopyrightText: GARDENA GmbH
#
# SPDX-License-Identifier: LGPL-2.0-or-later

# coding=utf-8

"""
A Partner Mixin for the Device class.
"""

import logging
import warnings
import xml.etree.ElementTree as ETree
from ipaddress import ip_address

from ._device_description import DeviceDescriptionType, RadioMode
from ._service import Service


def _ipv6_to_int(ipv6):
    """Convert IPv6 address to Lemonbeat format (long and uppercase without colons)."""
    return ip_address(ipv6).exploded.replace(':', '').upper()


class PartnerMixin:
    """Partner Mixin for the Device class."""

    def get_partner_information_memory(self):
        """Get partner information memory"""
        # TODO: parse response
        _ = self
        raise Exception('Functionality not implemented yet.')
        # return self._send_request(Service.PARTNER_INFORMATION, [ETree.Element("partner_information_get_memory")])

    def get_partner_information_memory_raw(self):
        """Get partner information memory. Returns raw XML."""
        warnings.warn(
            "get_partner_information_memory_raw is about to be deprecated, "
            "use get_partner_information_memory instead as soon it is implemented",
            PendingDeprecationWarning)
        return self._send_request_raw(Service.PARTNER_INFORMATION, [ETree.Element("partner_information_get_memory")])

    def get_partner_information(self):
        """Get partner information."""
        # TODO: parse response
        _ = self
        raise Exception('Functionality not implemented yet.')
        # return self._send_request(Service.PARTNER_INFORMATION, [ETree.Element("partner_information_get")])

    def get_partner_information_raw(self):
        """Get partner information. Returns raw XML."""
        warnings.warn(
            "get_partner_information_raw is about to be deprecated, "
            "use get_partner_information instead as soon it is implemented",
            PendingDeprecationWarning)
        return self._send_request_raw(Service.PARTNER_INFORMATION, [ETree.Element("partner_information_get")])

    def set_partner_information(self,
                                partner_id,
                                partner_address,
                                wakeup_channel=3,
                                channel_map="10080804"):
        """Set partner information (required to handle wakeup)."""
        partner = ETree.Element("partner", partner_id=str(partner_id))
        # radio mode (wake on radio)
        ETree.SubElement(partner,
                         "info",
                         type_id=str(DeviceDescriptionType.RADIO_MODE.value),
                         number=str(RadioMode.WAKE_ON_RADIO.value))
        # wakeup channel
        ETree.SubElement(partner,
                         "info",
                         type_id=str(DeviceDescriptionType.WAKEUP_CHANNEL.value),
                         number=str(wakeup_channel))
        # channel map
        ETree.SubElement(partner,
                         "info",
                         type_id=str(DeviceDescriptionType.CHANNEL_MAP.value),
                         hex=channel_map)
        # IPv6 address of partner
        ETree.SubElement(partner,
                         "info",
                         type_id=str(DeviceDescriptionType.IPV6_ADDRESS.value),
                         hex=_ipv6_to_int(partner_address))
        # wakeup now
        ETree.SubElement(partner,
                         "info",
                         type_id=str(DeviceDescriptionType.WAKEUP_NOW.value),
                         number="5000")
        etree = ETree.Element("partner_information_set")
        etree.append(partner)
        self._send_message(Service.PARTNER_INFORMATION, [etree])

    def wakeup_partner(self, partner_id, wakeup_now=5000):
        """Send wake up message."""
        partner = ETree.Element("partner", partner_id=str(partner_id))
        # wakeup now
        ETree.SubElement(partner,
                         "info",
                         type_id=str(DeviceDescriptionType.WAKEUP_NOW.value),
                         number=str(wakeup_now))
        etree = ETree.Element("partner_information_set")
        etree.append(partner)
        self._send_message(Service.PARTNER_INFORMATION, [etree])

    def get_partner_id(self, address):
        """Return partner id from memory, None if not found or on error."""
        element = self.get_partner_information_raw()

        partner_info = element[0][0]
        for partner in partner_info:
            info = partner.find(".//*[@type_id='%s']" % str(DeviceDescriptionType.IPV6_ADDRESS.value))
            ip_prepared = _ipv6_to_int(address)
            if info.get('hex') == ip_prepared:
                return int(partner.get('partner_id'))

        # TODO: raise error
        return None

    def register_partner(self, address):
        """Register new partner and return new partner_id. None on error."""
        if self.get_partner_id(address):
            logging.warning("Partner already exists, use get_partner_id to get the id")
            # TODO: raise error
            return None

        element = self.get_partner_information_memory_raw()
        partner_memory = element[0][0]
        partner_max = int(partner_memory.get('count'))
        partner_free = int(partner_memory.get('free_count'))
        if partner_max <= partner_free:
            logging.warning("no free space available: %d of %d used", partner_free, partner_max)
            # TODO: raise error
            return None

        element = self.get_partner_information_raw()
        partner_info = element[0][0]
        used_slots = set()
        for partner in partner_info:
            used_slots.add(int(partner.get('partner_id')))

        # initialize set with possible partner_ids
        # used_slots starts always with 1
        max_slots = set(list(range(1, partner_max + 1)))

        # get difference between used and usable partner_ids
        # diff should not be empty here, because we checked
        # used slots in memory before
        diff = max_slots.difference(used_slots)

        # return smallest free partner_id
        # set is always INC sorted, so we only need to pop first element
        partner_id = diff.pop()
        self.set_partner_information(partner_id=partner_id, partner_address=address)
        return partner_id

    def remove_partner(self, partner_id):
        """Remove partner from memory."""
        self._send_message(Service.PARTNER_INFORMATION,
                           [ETree.Element("partner_information_delete", partner_id=str(partner_id))])

    def remove_all_partner(self):
        """Remove all partner from memory."""
        self._send_message(Service.PARTNER_INFORMATION, [ETree.Element("partner_information_delete")])
