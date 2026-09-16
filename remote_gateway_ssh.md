# SPDX-FileCopyrightText: GARDENA GmbH
#
# SPDX-License-Identifier: LGPL-2.0-or-later

# Using the library with a Remote Gateway and SSH

**TODO: This file needs to be updated regarding the changes of the BNW migration.**

This Python library can be used on your local computer by using the
radio module in a remote gateway, where you have access to via SSH.

## Setup

This procedure has only been tested with the LC Gateway, the old
Gateway is out of scope.

### Prepare Gateway

Make sure you have SSH access to the gateway and you can login without
entering a password by using SSH keys. For your convenience you may add
a host name for your gateway in `/etc/hosts` on your local computer. In
this document, we assume the gateway's host name is `mygateway`.

Shadoway must not be running on the gateway or some features might not
be available.

Shadoway might be restarted by some scripts. In order to disable
shadoway perform these steps:

```bash
ssh root@mygateway systemctl stop shadoway
ssh root@mygateway systemctl disable shadoway
ssh root@mygateway systemctl mask shadoway
```

To enable and start shadoway again, perform the opposite `systemctl`
commands in reverse order:

```bash
ssh root@mygateway systemctl unmask shadoway
ssh root@mygateway systemctl enable shadoway
ssh root@mygateway systemctl start shadoway
```

On the gateway you might need to install the pickle module from
Python's standard library. Use the following commands:

```bash
ssh root@mygateway opkg update
ssh root@mygateway opkg install python3-pickle
```

### Install Dependencies on your Local Computer

Install Pip and then install RPyC with the commands (installing jq is
optional, the step further below can easily performed manually):

```bash
sudo apt install python3-pip jq
pip3 install rpyc plumbum
```

### Get the Inclusion Message

Get the inclusion message from the Gateway with the command:

```bash
ssh root@mygateway cat \
/var/lib/shadoway/work/Network_management/Network_key.json \
| jq '.["encrypted_key"]'
```

# Interactive Use

Use in IPython:

```python
from lemonbeat.remote_gateway import RemoteGateway

INCLUSION_MESSAGE="... <insert inclusion message here> ..."

# this will take some seconds
gw = RemoteGateway("mygateway", user="root", inclusion_message=INCLUSION_MESSAGE)

# test if it works
gw.get_device_description()
```

After this you can use the `gw` instance in the same way as the regular
one described in the main [README.md](README.md).
