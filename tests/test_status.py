# SPDX-FileCopyrightText: GARDENA GmbH
#
# SPDX-License-Identifier: LGPL-2.0-or-later

# coding=utf-8

"""Lemonbeat Status unit tests."""

import xml.etree.ElementTree as ETree

from lemonbeat import ReportStatus, Hex
from lemonbeat._status import _parse_status


def test_parse_status():
    status_report_xml = '''<?xml version="1.0" ?>
<network version="1" xmlns="urn:statusxsd">
    <device version="1">
        <!-- Status Level Error -->
        <status_report code="23" level="2" type_id="200"/>
    </device>
</network>
'''
    status_report = ETree.fromstring(status_report_xml)[0][0]
    assert _parse_status([status_report]) == [ReportStatus(type_id=200, code=23, level=2)]


def test_parse_status_data():
    status_report_xml = '''<?xml version="1.0" ?>
<network version="1" xmlns="urn:statusxsd">
    <device version="1">
        <!-- Status Level Important -->
        <status_report code="10" data="000007" level="1" type_id="200"/>
    </device>
</network>
'''
    status_report = ETree.fromstring(status_report_xml)[0][0]
    assert _parse_status([status_report]) == [ReportStatus(type_id=200, code=10, level=1, data=Hex("000007"))]
