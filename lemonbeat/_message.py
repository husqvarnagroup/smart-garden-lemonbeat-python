# SPDX-FileCopyrightText: GARDENA GmbH
#
# SPDX-License-Identifier: LGPL-2.0-or-later

# coding=utf-8

"""
A Message Mixin for the Device class.
"""

import logging
import socket as std_socket
import xml.etree.ElementTree as ETree
from xml.dom import minidom

from lemonbeat import lsdl_serializer
from ._defines import MAX_MSG_SIZE
from ._types import RequestTimeoutError, SocketError, UnexpectedLemonbeatEncryptionError

LEMONBEAT_TCLASS_BASE = 0x0c
LEMONBEAT_TCLASS_ENCRYPTION_BIT = 4


def _etree_eq(first, second):
    return (first.tag == second.tag
            and first.text == second.text
            and first.tail == second.tail
            and first.attrib == second.attrib
            and len(first) == len(second)
            and all(_etree_eq(*c) for c in zip(first, second)))


def _verify_conversion(exi, port, xml):
    if logging.root.level <= logging.WARNING:
        xml_converted = lsdl_serializer.decompress(port, exi)
        if not _etree_eq(ETree.fromstring(xml_converted), ETree.fromstring(xml)):
            logging.warning("data differs after conversion\n"
                            "======================\n"
                            "%s"
                            "====\n"
                            "        !=\n"
                            "====\n"
                            "%s"
                            "======================",
                            _pretty(xml_converted),
                            _pretty(xml))


def _pretty(xml):
    """"Pretty format XML."""
    return minidom.parseString(xml).toprettyxml(indent="    ")


def _etrees_to_xml(service, etrees, go_to_sleep=None):
    network = ETree.Element('network', xmlns=service.xmlns, version="1")
    device = ETree.SubElement(network, "device", version="1")
    if go_to_sleep is not None:
        device.attrib['go_to_sleep'] = str(go_to_sleep)
    device.extend(etrees)
    return ETree.tostring(network, encoding="UTF-8")


def _xml_to_exi(service, xml):
    exi = lsdl_serializer.compress(service.value, xml)
    _verify_conversion(exi, service.value, xml)
    return exi


def _pretty_addr(sockaddr):
    ni = std_socket.getnameinfo(sockaddr, std_socket.NI_NUMERICHOST | std_socket.NI_NUMERICSERV)
    return f"[{ni[0]}]:{ni[1]}"


def _send(select, socket, bind_address, address, service, etrees, *, go_to_sleep=None, timeout=None, encrypted=True):
    """
    Send a simple Lemonbeat message. Returning XML ElementTree.

    @param select: select Python module
    @param socket: socket Python module to use
    @param bind_address: tuple passed to socket.bind()
    @param address: IPv6 address of the destination (string or 4-tuple)
    @param service: Lemonbeat service, e.g. Service.VALUE
    @param etrees: Message as a list of ElementTree objects
    @param go_to_sleep: Optional go_to_sleep argument, passed as attribute in the device tag
    @param timeout: Optional timeout to wait for response, None if no response expected
    @returns: ElementTree
    """

    if isinstance(address, str):
        address_tuple = (address, service.value)
    elif isinstance(address, tuple) and len(address) == 4:
        address_tuple = (address[0], service.value, *address[2:4])
    else:
        raise TypeError("Parameter address must be string or 4-tuple.")

    tclass_send = bool(encrypted) << LEMONBEAT_TCLASS_ENCRYPTION_BIT | LEMONBEAT_TCLASS_BASE
    xml = _etrees_to_xml(service, etrees, go_to_sleep)
    logging.info(f"sending {service.name.lower()} data to {_pretty_addr(address_tuple)} (tclass: {hex(tclass_send)})\n"
                 f"======================\n"
                 f"{_pretty(xml)}"
                 f"======================")
    exi = _xml_to_exi(service, xml)

    # send it via UDP
    with socket.socket(socket.AF_INET6, socket.SOCK_DGRAM | socket.SOCK_NONBLOCK) as sock:
        sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_TCLASS, tclass_send)
        # receive traffic class on incoming packets
        sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_RECVTCLASS, 1)
        sock.bind(bind_address)
        sock.sendto(exi, address_tuple)

        if timeout is None:
            # empty timeout is not an error
            return None

        # get answer
        select.select((sock.fileno(),), (), (), timeout)
        # receive new data
        try:
            # TODO flags = socket.MSG_ERRQUEUE, but does always raise BlockingIOError :-/
            response_exi, ancdata, msg_flags, remote_address = sock.recvmsg(MAX_MSG_SIZE, 1024, 0)
        except BlockingIOError:
            raise RequestTimeoutError

    tclass = None
    for i, (cmsg_level, cmsg_type, cmsg_data) in enumerate(ancdata):
        if cmsg_level == socket.IPPROTO_IPV6 and cmsg_type == socket.IPV6_TCLASS:
            tclass = cmsg_data[0]
            if tclass != tclass_send:
                logging.error(f"received unexpected encryption flag in traffic class: {hex(cmsg_data[0])}")
                raise UnexpectedLemonbeatEncryptionError
            del ancdata[i]
            continue
        logging.error(
            f"received socket error - cmsg_level: {cmsg_level}, cmsg_type: {cmsg_type}, cmsg_data: {cmsg_data}")
    if len(ancdata):
        raise SocketError
    assert tclass is not None

    # convert response to XML
    response_xml = lsdl_serializer.decompress(service.value, response_exi)
    logging.info(f"received {service.name.lower()} data from {_pretty_addr(remote_address)} (tclass: {hex(tclass)})\n"
                 f"======================\n"
                 f"{_pretty(response_xml)}"
                 f"======================")
    response_etree = ETree.fromstring(response_xml)
    return response_etree


def _verify_message_format(service, message):
    # verify message is of format "<network><device>...</device></network>"
    return message.tag == f"{{{service.xmlns}}}network" and len(message) == 1 and \
        message[0].tag == f"{{{service.xmlns}}}device"
