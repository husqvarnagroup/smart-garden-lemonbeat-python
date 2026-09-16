# SPDX-FileCopyrightText: GARDENA GmbH
#
# SPDX-License-Identifier: LGPL-2.0-or-later

# coding=utf-8

"""
The Lemonbeat gateway device object and some helper functions.
"""

import logging
import select as std_select
import socket as std_socket
import threading
import warnings
import xml.etree.ElementTree as ETree
from ipaddress import IPv6Address

from lemonbeat import lsdl_serializer
from ._defines import MAX_MSG_SIZE, DEFAULT_INTERFACE, LEMONBEATD_NETWORK_KEY_FILE
from ._device import Device, _parse_device_description, _parse_value
from ._message import _pretty, _verify_message_format, _pretty_addr
from ._service import Service
from ._status import _parse_status

_SERVICE_REPORT_PARSERS = {
    Service.DEVICE_DESCRIPTION: _parse_device_description,
    Service.STATUS: _parse_status,
    Service.VALUE: _parse_value,
}


class MissingInclusionMessageError(Exception):
    """Exception for representing an error thrown when trying to access an unconfigured inclusion message."""
    pass


def _parse_if_inet6(data, interface):
    # one line from file contains:
    # 0) ipv6 address without ":"
    # 1) netlink device number
    # 2) prefix in hex
    # 3) scope value
    # 4) interface flags
    # 5) device name
    raw_lines = data.strip().split("\n")
    for raw_line in raw_lines:
        line = raw_line.split(maxsplit=5)
        if line[5] == interface:
            address = IPv6Address(bytes.fromhex(line[0]))
            if not address.is_link_local:
                continue
            if address == IPv6Address("fe80::106:100:0:0"):
                # skip static BNW Gateway address
                continue
            return address.compressed, 0, 0, int(line[1], 16)
    raise IOError("Error while getting ipv6 address from interface: %s" % interface)


def calculate_dongle_address(address_tuple):
    local_address, _, _, _ = address_tuple
    local_prefix = "fe80::106"
    dongle_prefix = "fc00::6"
    return local_address.replace(local_prefix, dongle_prefix)


class Gateway(Device):
    """Object representing a Lemonbeat Gateway, usually a Dongle or a physical Gardena Gateway."""

    def __init__(self, *, interface=None, bind_address=None, address=None, sel_sock=(std_select, std_socket),
                 lemonbeatd_network_key=False, **kwargs):
        """Create a gateway object.

        :param interface: Network interface name of the Lemonbeat dongle, alternatively you can manually specify
        bind_address and the address.
        :param bind_address: Tuple of local address passed to socket.bind().
        :param address: IPv6 address as string of the dongle device. If None the address will be obtained from the
        interface.
        :param sel_sock: Tuple for overriding the Python modules select and socket.
        :param lemonbeatd_network_key: Use inclusion_message from lemonbeatd if true. Ignored if inclusion_message was provided before.
        :param inclusion_message: Inclusion message of the Lemonbeat network.
        :param timeout: Timeout in seconds for all requests to that device.
        """
        if interface is None and bind_address is None:
            interface = DEFAULT_INTERFACE
        self.interface = interface
        self._bind_address = bind_address
        self._address = address
        self.select = sel_sock[0]
        self.socket = sel_sock[1]
        try:
            inclusion_message = kwargs.pop('inclusion_message')
        except KeyError:
            if lemonbeatd_network_key:
                # The package python3-json is optional on the Gateway, import on demand
                import json
                with open(LEMONBEATD_NETWORK_KEY_FILE) as key_file:
                    network_key = json.load(key_file)
                inclusion_message = network_key["encrypted_key"].upper()
            else:
                logging.warning(
                    "No inclusion message specified, you won't be able to include devices. Use the generate() function "
                    "from the inclusion_message module to generate a random inclusion message. Pass inclusion_message=None "
                    "to hide this warning.")
                inclusion_message = None
        else:
            if inclusion_message is not None:
                inclusion_message = inclusion_message.upper()
        self._inclusion_message = inclusion_message
        self._listener_threads = {}
        super().__init__(self, address, **kwargs)

    @property
    def bind_address(self):
        if self._bind_address is None:
            # initialize after first use
            self._bind_address = self._interface_bind_address
        return self._bind_address

    @property
    def address(self):
        if self._address is None:
            # initialize after first use
            self._address = self._dongle_address
        return self._address

    @property
    def _interface_bind_address(self):
        """Get the first link-local IPv6 address and the interface index from the interface.

        The return value is usable as an argument to socket.bind()
        """
        with open("/proc/net/if_inet6") as if_inet6_file:
            data = if_inet6_file.read()
        return _parse_if_inet6(data, self.interface)

    @property
    def _dongle_address(self):
        """Convert local address from bind_address to Lemonbeat dongle address."""
        dongle_address = calculate_dongle_address(self.bind_address)
        logging.debug("local address: %s, dongle address: %s", self.bind_address[0], dongle_address)
        return dongle_address

    @property
    def inclusion_message(self):
        """Get the inclusion message for the gateway's network."""
        if self._inclusion_message is None:
            raise MissingInclusionMessageError("Include not possible when inclusion message is not configured.")
        return self._inclusion_message

    def _service_listener(self, listener_address):
        """Service listener thread worker."""
        port = listener_address[1]
        service = Service(port)
        logging.info("Starting '%s' service listener at %s.", service.name.lower(), _pretty_addr(listener_address))

        # create socket, IPv6, UDP and non-blocking
        with self.socket.socket(self.socket.AF_INET6, self.socket.SOCK_DGRAM | self.socket.SOCK_NONBLOCK) as sock:
            sock.bind(listener_address)

            while self._listener_threads[service][1]:
                self.select.select((sock.fileno(),), (), (), 1)
                # receive new data
                try:
                    # TODO use recvmsg and extract ancdata
                    data, remote_address = sock.recvfrom(MAX_MSG_SIZE)
                except BlockingIOError:
                    continue

                # convert and parse XML
                xml = lsdl_serializer.decompress(port, data)
                logging.info("%s service listener at %s received data from %s.\n"
                             "======================\n"
                             "%s"
                             "======================",
                             service.name.lower(), _pretty_addr(listener_address),
                             _pretty_addr(remote_address), _pretty(xml))
                etree = ETree.fromstring(xml)
                if not _verify_message_format(service, etree):
                    logging.error(f"{service.name.lower()} message does not follow "
                                  "<network><device>...</device></network> format."
                                  "Ignoring message.")
                    continue

                # call handler
                listener_thread = self._listener_threads[service]
                handler = listener_thread[2]
                raw = listener_thread[3]
                if handler is not None:
                    # noinspection PyBroadException
                    try:
                        if raw == "sock_addr":
                            handler((sock, remote_address), etree)
                        elif raw:
                            handler(remote_address, etree)
                        else:
                            handler(remote_address, _SERVICE_REPORT_PARSERS[service](etree[0]))
                    except Exception:  # pylint: disable=broad-except
                        logging.exception("")

        logging.info("Stopping %s service listener at %s.", service.name.lower(), _pretty_addr(listener_address))

    def start_service_listener(self, service, *, handler, raw=False, listen_any=True):
        """Start a listener for the given service."""
        port = service.value
        if listen_any:
            listener_address = ('::', port)
        else:
            listener_address = (self.bind_address[0], port, *self.bind_address[2:])
        if service in self._listener_threads:
            logging.warning("service listener already running at %s", _pretty_addr(listener_address))
            return
        # create and start thread
        thread = threading.Thread(target=self._service_listener, args=(listener_address,))
        if not raw and service not in _SERVICE_REPORT_PARSERS:
            raise NotImplementedError('Functionality not implemented yet.')
        if raw and service in _SERVICE_REPORT_PARSERS:
            warnings.warn("Using a raw handler for the '{}' service is deprecated.".format(service.name.lower()),
                          DeprecationWarning)
        # data structure: [thread, running, handler, raw]
        self._listener_threads[service] = [thread, True, handler, raw]
        thread.daemon = True
        thread.start()

    def stop_service_listener(self, service=None):
        """Stop service listener optionally defined by service, or all service listeners."""
        if service is None:
            for listener_service in tuple(self._listener_threads):
                self.stop_service_listener(listener_service)
            return
        self._listener_threads[service][1] = False
        self._listener_threads[service][0].join()
        del self._listener_threads[service]

    @property
    def service_listeners(self):
        """Return an iterable of services with running listeners."""
        return self._listener_threads.keys()
