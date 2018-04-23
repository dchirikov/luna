'''
Written by Dmitry Chirikov <dmitry@chirikov.ru>
This file is part of Luna, cluster provisioning tool
https://github.com/dchirikov/luna

This file is part of Luna.

Luna is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Luna is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Luna.  If not, see <http://www.gnu.org/licenses/>.

'''

import re
import socket
from binascii import hexlify, unhexlify
import logging


log = logging.getLogger(__name__)

af = {
    4: socket.AF_INET,
    6: socket.AF_INET6,
}

hex_format = {
    4: '08x',
    6: '032x'
}


def ntoa(num_ip, ver=4):
    """
    Convert the IP numip from the binary notation
    into the IPv4 numbers-and-dots form
    """

    try:

        ip = socket.inet_ntop(
            af[ver],
            unhexlify(format(num_ip, hex_format[ver]))
        )

        return ip

    except:
        err_msg = ("Cannot convert '{}' from C"
                   " to IPv{} format".format(num_ip, ver))
        log.error(err_msg)
        raise RuntimeError, err_msg


def aton(ip, ver=4):
    """
    Convert the IP ip from the IPv4 numbers-and-dots
    notation into binary form (in network byte order)
    """
    try:
        absnum = int(hexlify(socket.inet_pton(af[ver], ip)), 16)
        return long(absnum)

    except:
        err_msg = "Cannot convert IP '{}' to C format".format(ip)
        log.error(err_msg)
        raise RuntimeError, err_msg


def reltoa(num_net, rel_ip, ver):
    """
    Convert a relative ip (a number relative to the base of the
    network obtained using 'get_num_subnet') into an IPv4 address
    """

    num_ip = int(num_net) + int(rel_ip)
    return ntoa(num_ip, ver)


def atorel(ip, num_net, prefix, ver=4):
    """
    Convert an IPv4 address into a number relative to the base of
    the network obtained using 'get_num_subnet'
    """

    num_ip = aton(ip, ver)

    # Check if the ip address actually belongs to num_net/prefix
    if not ip_in_net(ip, num_net, prefix, ver):
        err_msg = ("Network '{}/{}' does not contain '{}'"
                   .format(ntoa(num_net, ver), prefix, ip))
        log.error(err_msg)
        raise RuntimeError, err_msg

    relative_num = long(num_ip - num_net)

    return relative_num


def get_num_subnet(ip, prefix, ver=4):
    """
    Get the address of the subnet to which ip belongs in binary form
    """

    maxbits = 32
    if ver == 6:
        maxbits = 128

    try:
        prefix = int(prefix)
    except:
        err_msg = "Prefix '{}' is invalid, must be 'int'".format(prefix)
        log.error(err_msg)
        raise RuntimeError, err_msg

    if ver == 4 and prefix not in range(1, 31):
        err_msg = "Prefix should be in the range [1..30]"
        log.error(err_msg)
        raise RuntimeError, err_msg

    if ver == 6 and prefix not in range(1, 127):
        err_msg = "Prefix should be in the range [1..126]"
        log.error(err_msg)
        raise RuntimeError, err_msg

    if type(ip) is long or type(ip) is int:
        num_ip = ip
    else:
        try:
            num_ip = aton(ip, ver)
        except socket.error:
            err_msg = "'{}' is not a valid IP".format(ip)
            log.error(err_msg)
            raise RuntimeError, err_msg

    num_mask = (((1 << maxbits) - 1)
                ^ ((1 << (maxbits+1 - prefix) - 1) - 1))

    num_subnet = long(num_ip & num_mask)

    return num_subnet


def ip_in_net(ip, num_net, prefix, ver=4):
    """
    Check if an address (either in binary or IPv4 form) belongs to
    num_net/prefix
    """

    if type(ip) is long or type(ip) is int:
        num_ip = ip
    else:
        num_ip = aton(ip, ver)

    num_subnet1 = get_num_subnet(num_net, prefix, ver)
    num_subnet2 = get_num_subnet(num_ip, prefix, ver)

    return num_subnet1 == num_subnet2


def guess_ns_hostname():
    """
    Try to guess the hostname to use for the nameserver
    it supports hosts of the format host-N, hostN for HA
    configurations. Returns the current hostname otherwise
    """
    ns_hostname = socket.gethostname().split('.')[0]

    if ns_hostname[-1:].isdigit():
        guessed_name = re.match('(.*)[0-9]+$', ns_hostname).group(1)

        if guessed_name[-1] == '-':
            guessed_name = guessed_name[:-1]

        try:
            guessed_ip = socket.gethostbyname(guessed_name)
        except:
            guessed_ip = None

        if guessed_ip:
            log.info(("Guessed that NS server should be '%s', "
                      "instead of '%s'. "
                      "Please update if this is not correct.") %
                     (guessed_name, ns_hostname))
            return guessed_name

    # Return the current host's hostname if the guessed name could not
    # be resolved
    return ns_hostname


def get_ip_version(ip):
    for ver in [4, 6]:
        try:
            int(hexlify(socket.inet_pton(af[ver], ip)), 16)
            return ver
        except:
            pass
    return None


def ipv6_unwrap(ip):
    """
    Retruns IPv6 ip address in full form:
    fe80:1::                => fe80:0001:0000:0000:0000:0000:0000:0000
    2001:db8::ff00:42:8329  => 2001:0db8:0000:0000:0000:ff00:0042:8329
    """

    ip = ntoa(aton(ip, 6), 6)

    out = [''] * 8
    start, end = ip.split('::')

    start_splited = start.split(':')
    end_splited = end.split(':')

    out[:len(start_splited)] = start_splited

    i = 1
    for elem in reversed(end_splited):
        out[-i] = elem
        i += 1

    for i in range(len(out)):
        out[i] = '{:0>4}'.format(out[i])

    return ":".join(out)
