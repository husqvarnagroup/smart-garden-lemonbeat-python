# coding=utf-8

# Copyright 2019 Gardena GmbH
# Adrian Friedli <adrian.friedli@husqvarnagroup.com>
#
# SPDX-License-Identifier: LGPL-2.0-or-later

"""
Remote Gateway wrapper
"""

__version__ = "0.1.0"

__all__ = [
    "RemoteGateway",
]

from plumbum import SshMachine
from rpyc.utils.zerodeploy import DeployedServer

from lemonbeat import Gateway
from lemonbeat._gateway import _parse_if_inet6


class RemoteGateway(Gateway):
    """Object representing a remote Lemonbeat Gateway.

    This is usually a computer with a Lemonbeat Dongle or a physical
    Gardena Gateway reachable by SSH.
    """

    def __init__(self, host, *, python_executable="/usr/bin/python3", **kwargs):
        """Create a remote gateway object.

        :param host: host name of the remote SSH host.
        :param port: SSH port to connect to.
        :param user: user name to connect with.
        :param python_executable: Path to the Python executable on the
               remote host.

        For more available parameters also see `plumbum.SshMachine` and
        `rpyc.utils.zerodeploy.DeployedServer`.

        All parameters from `lemonbeat.Gateway` are also available.
        """
        ssh_machine_args = {k: v for k, v in kwargs.items() if
                            k in ['user', 'port', 'keyfile', 'ssh_command', 'scp_command', 'ssh_opts', 'scp_opts',
                                  'password', 'encoding', 'connect_timeout', 'new_session']}
        kwargs = {k: v for k, v in kwargs.items() if k not in ssh_machine_args}
        self.ssh_machine = SshMachine(host, **ssh_machine_args)

        deployed_server_args = {k: v for k, v in kwargs.items() if k in ['server_class', 'extra_setup']}
        kwargs = {k: v for k, v in kwargs.items() if k not in deployed_server_args}
        self.deployed_server = DeployedServer(self.ssh_machine, python_executable=python_executable,
                                              **deployed_server_args)

        self.rpyc_conn = self.deployed_server.classic_connect()
        # sometimes we call select with a large timeout, increasing this from the default 30 seconds
        self.rpyc_conn._config['sync_request_timeout'] = 120

        super().__init__(sel_sock=(self.rpyc_conn.modules.select, self.rpyc_conn.modules.socket), **kwargs)

    @property
    def _interface_bind_address(self):
        """Get the first link-local IPv6 address and the interface index from the interface.

        The return value is usable as an argument to socket.bind()
        """
        with self.rpyc_conn.builtins.open("/proc/net/if_inet6") as if_inet6_file:
            data = if_inet6_file.read()
        return _parse_if_inet6(data, self.interface)
