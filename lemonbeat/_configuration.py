# SPDX-FileCopyrightText: GARDENA GmbH
#
# SPDX-License-Identifier: LGPL-2.0-or-later

# coding=utf-8

"""
A Configuration Mixin for the Device class.
"""

import xml.etree.ElementTree as ETree

from ._service import Service


class ConfigurationMixin:
    """Configuration Mixin for the Device class."""

    def get_config_status(self):
        """Send 'config_status_get' message."""
        response = self._send_request(Service.CONFIGURATION, [ETree.Element("config_status_get")])
        return int(response[0].attrib['status'])

    def _set_config_mode(self, mode):
        """Send 'config_mode_set' message."""
        self._send_message(Service.CONFIGURATION, [ETree.Element("config_mode_set", mode=str(mode))])

    def rollback_config(self):
        """Rollback any configuration changes. (Rollback)"""
        return self._set_config_mode(0)

    def save_config(self):
        """Save any configuration changes and reset the state machine states. (Save and Reset)"""
        return self._set_config_mode(1)

    def save_config_and_preserve_states(self):
        """Save any configuration changes and do not change the state machine states. (Save and Preserve)"""
        return self._set_config_mode(2)

    def reset_config(self):
        """Clear the configuration and set the default configuration. (Set Default)"""
        return self._set_config_mode(3)

    def clear_config(self):
        """Clear the configuration. (Clear)"""
        return self._set_config_mode(4)

    def get_timezone_offset(self):
        """Send 'calendar_get_timezone' message."""
        response = self._send_request(Service.CALENDAR, [ETree.Element("calendar_get_timezone")])
        return int(response[0].attrib['offset'])

    def set_timezone_offset(self, offset):
        """Set Calendar timezone offset in seconds."""
        self._send_message(Service.CALENDAR, [ETree.Element("calendar_set_timezone", offset=str(offset))])
