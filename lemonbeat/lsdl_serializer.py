# coding=utf-8

# Copyright 2018 Gardena GmbH
# Adrian Friedli <adrian.friedli@husqvarnagroup.com>
#
# SPDX-License-Identifier: LGPL-2.0-or-later

"""
FFI interface to Lemonbeat's lsdl serializer library.
"""

__version__ = "0.1.0"

__all__ = [
    "get_version",
    "compress",
    "decompress",
]

import inspect
import os
import platform
import threading
from ctypes import cdll, create_string_buffer, c_char_p, c_ulong, c_ushort

BUFFER_SIZE = 32768

MUTEX = threading.Lock()


def _load():
    """Load the C library."""
    try:
        return cdll.LoadLibrary('/usr/lib/liblsdl-serializer.so')
    except OSError:
        arch = None
        if platform.system() == 'Linux':
            if platform.machine() == 'x86_64':
                arch = 'x86_64-linux-gnu'
            if platform.machine() == 'armv7l':
                arch = 'arm-linux-gnueabihf'
            if platform.machine() == 'aarch64':
                arch = 'aarch64-linux-gnu'
        if arch is None:
            raise
        so_file = os.path.join(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))),
                               f'lib/{arch}/liblsdl-serializer.so')
        return cdll.LoadLibrary(so_file)


SERIALIZER = _load()
SERIALIZER.lsdlconv_getVersion.argtypes = []
SERIALIZER.lsdlconv_getVersion.restype = c_char_p
SERIALIZER.compressXML.argtypes = [c_ushort, c_char_p, c_ulong, c_char_p, c_ulong, c_ulong]
SERIALIZER.compressXML.restype = c_ulong
SERIALIZER.decompressEXI.argtypes = [c_ushort, c_char_p, c_ulong, c_char_p, c_ulong, c_ulong]
SERIALIZER.decompressEXI.restype = c_ulong


def get_version():
    """Get library version string."""
    with MUTEX:
        return SERIALIZER.lsdlconv_getVersion().decode()


def compress(port, xml):
    """Convert XML to EXI."""
    buf = create_string_buffer(BUFFER_SIZE)
    with MUTEX:
        length = SERIALIZER.compressXML(port, xml, len(xml), buf, len(buf), 0)
    return buf.raw[:length]


def decompress(port, exi):
    """Convert EXI to XML."""
    buf = create_string_buffer(BUFFER_SIZE)
    with MUTEX:
        length = SERIALIZER.decompressEXI(port, exi, len(exi), buf, len(buf), 0)
    return buf.raw[:length]
