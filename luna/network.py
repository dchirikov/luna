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
from config import usedby_key

import logging

from bson.objectid import ObjectId

from luna import utils
from luna.base import Base
from luna.cluster import Cluster


class Network(Base):
    """Class for operating with network objects"""

    log = logging.getLogger(__name__)

    def __init__(self, name=None, mongo_db=None,
                 create=False, id=None, version=None,
                 NETWORK=None, PREFIX=None,
                 ns_hostname=None, ns_ip=None, comment=''):
        """
        create  - should be True if we need create a network
        NETWORK - network
        PREFIX  - the prefix in a networks CIDR format
        """

        self.log.debug("function {} args".format(self._debug_function()))

        # Define the schema used to represent network objects

        self._collection_name = 'network'
        self._keylist = {
            'PREFIX': type(0),
            'ns_hostname': type(''),
            'include': type(''),
            'rev_include': type(''),
            'comment': type(''),
        }

        # Check if this network is already present in the datastore
        # Read it if that is the case

        net = self._get_object(name, mongo_db, create, id)

        if create:
            if not version:
                version = utils.ip.get_ip_version(NETWORK)
                if version == 0:
                    err_msg = ("Unable to determine protocol version " +
                               "for given network")
                    self.log.error(err_msg)
                    raise RuntimeError, err_msg

            if version not in [4, 6]:
                err_msg = "IP version should be 4 or 6"
                self.log.error(err_msg)
                raise RuntimeError, err_msg

            maxbits = 32
            if version == 6:
                maxbits = 128

            self.version = version
            self.maxbits = maxbits

            cluster = Cluster(mongo_db=self._mongo_db)
            num_subnet = utils.ip.get_num_subnet(NETWORK, PREFIX, self.version)

            flist = self._flist_to_str([{
                'start': 1,
                'end': (1 << (self.maxbits - int(PREFIX))) - 2
            }])

            # Try to guess the nameserver hostname if none provided

            if not ns_hostname:
                ns_hostname = utils.ip.guess_ns_hostname()

            # Store the new network in the datastore
            if self.version == 6:
                num_subnet = str(num_subnet)

            # Try to find duplicate net
            if utils.helpers.find_duplicate_net(
                    num_subnet, mongo_db=self._mongo_db
                ):
                err_msg = (
                    "Network {}/{} is defined already"
                    .format(NETWORK, PREFIX)
                )
                self.log.error(err_msg)
                raise RuntimeError, err_msg

            net = {'name': name, 'NETWORK': num_subnet, 'PREFIX': PREFIX,
                   'freelist': flist, 'ns_hostname': ns_hostname,
                   'ns_ip': None, 'version': version,
                   'include': None, 'rev_include': None,
                   'comment': comment}

            self.log.debug("Saving net '{}' to the datastore".format(net))

            self.store(net)
            self._convert_to_int()

            # Link this network to the current cluster

            self.link(cluster)

            # If no IP address is provided for the nameserver, default to
            # the cluster's frontend address

            if ns_ip is None:
                ns_ip = utils.ip.reltoa(num_subnet,
                                        int(flist[0]['end']),
                                        self.version)

            self.set('ns_ip', ns_ip)

        self.version = self._json['version']
        self.maxbits = 32
        if self.version == 6:
            self.maxbits = 128
        self._convert_to_int()

        self.log = logging.getLogger(__name__ + '.' + self._name)

    def _convert_to_int(self):
        """
        Converting self._json from strings to integers
        This is required, as mongo is unable to sore int representation
        of IPv6
        """

        if self.version == 4:
            return None

        self._json['NETWORK'] = int(self._json['NETWORK'])
        flist = []
        for elem in self._json['freelist']:
            start = elem['start']
            end = elem['end']
            flist.append({
                'start': int(start),
                'end': int(end)
            })
        if self._json['ns_ip']:
            self._json['ns_ip'] = int(self._json['ns_ip'])
        self._json['freelist'] = flist

    def _flist_to_str(self, flist):
        """
        Convert flist's interegers to strings for IPv6
        """
        if self.version == 4:
            return flist
        new_flist = []
        for elem in flist:
            new_elem = {
                'start': str(elem['start']),
                'end': str(elem['end'])
            }
            new_flist.append(new_elem)
        return new_flist

    def set(self, key, value):
        self._convert_to_int()
        net = self._json

        if key == 'ns_ip':

            rel_ns_ip = utils.ip.atorel(
                value, net['NETWORK'], net['PREFIX'], self.version
            )

            old_ip = net['ns_ip']

            if old_ip:
                self.release_ip(old_ip)

            self.reserve_ip(rel_ns_ip)

            if self.version == 6:
                rel_ns_ip = str(rel_ns_ip)

            ret = super(Network, self).set('ns_ip', rel_ns_ip)

        elif key == 'NETWORK':
            prefix = net['PREFIX']
            num_subnet = utils.ip.get_num_subnet(
                value, prefix, self.version
            )
            if self.version == 6:
                num_subnet = str(num_subnet)

            ret = super(Network, self).set('NETWORK', num_subnet)

        elif key == 'PREFIX':
            num_subnet = net['NETWORK']
            new_num_subnet = utils.ip.get_num_subnet(
                num_subnet, value, self.version
            )

            limit = (1 << (self.maxbits - value)) - 2
            prev_limit = (1 << (self.maxbits - self.get('PREFIX'))) - 2

            flist = utils.freelist.set_upper_limit(
                net['freelist'], limit, prev_limit)

            if self.version == 6:
                flist = self._flist_to_str(flist)
                new_num_subnet = str(new_num_subnet)

            ret = super(Network, self).set('freelist', flist)
            ret &= super(Network, self).set('NETWORK', new_num_subnet)
            ret &= super(Network, self).set('PREFIX', value)

        else:
            ret = super(Network, self).set(key, value)

        self._convert_to_int()
        return ret

    def get(self, key):
        self._convert_to_int()
        net = self._json

        if key == 'NETWORK':
            value = utils.ip.ntoa(
                net[key], self.version
            )

        elif key == 'NETMASK':
            prefix = int(net['PREFIX'])
            num_mask = (((1 << self.maxbits) - 1)
                        ^ ((1 << (self.maxbits+1 - prefix) - 1) - 1)
                        )

            value = utils.ip.ntoa(
                num_mask, self.version
            )

        elif key == 'ns_ip':
            value = utils.ip.reltoa(
                net['NETWORK'], net['ns_ip'], self.version
            )

        else:
            value = super(Network, self).get(key)

        return value

    def reserve_ip(self, ip1=None, ip2=None, ignore_errors=True):
        self._convert_to_int()
        net = self._json

        if type(ip1) is str:
            try:
                ip1 = utils.ip.atorel(
                    ip1, net['NETWORK'], net['PREFIX'], self.version
                )
            except RuntimeError:
                return None

        if type(ip2) is str:
            try:
                ip2 = utils.ip.atorel(
                    ip2, net['NETWORK'], net['PREFIX'], self.version
                )
            except RuntimeError:
                return None

        if bool(ip2) and ip2 <= ip1:
            self.log.error("Wrong range definition.")
            return None

        if bool(ip1):
            flist, unfreed = utils.freelist.unfree_range(net['freelist'],
                                                         ip1, ip2)

        elif ignore_errors:
            flist, unfreed = utils.freelist.next_free(net['freelist'])

        self.set('freelist', self._flist_to_str(flist))

        return unfreed

    def release_ip(self, ip1, ip2=None):
        net = self._json
        self._convert_to_int()

        if type(ip1) is str:
            ip1 = utils.ip.atorel(
                ip1, net['NETWORK'], net['PREFIX'], self.version
            )

        if type(ip2) is str:
            ip2 = utils.ip.atorel(
                ip2, net['NETWORK'], net['PREFIX'], self.version
            )

        if bool(ip2) and ip2 <= ip1:
            self.log.error("Wrong range definition.")
            return None

        flist, freed = utils.freelist.free_range(net['freelist'], ip1, ip2)
        self.set('freelist', self._flist_to_str(flist))

        return True

    def resolve_used_ips(self):
        from luna.switch import Switch
        from luna.otherdev import OtherDev
        from luna.group import Group

        net = self._json

        try:
            rev_links = net[usedby_key]
        except:
            self.log.error(("No IPs configured for network '{}'"
                            .format(self.name)))
            return {}

        out_dict = {}

        def add_to_out_dict(name, relative_ip):
            if name in out_dict:
                self.log.error(("Duplicate name '{}' in network '{}'"
                                .format(name, self.name)))
                return False
            if not relative_ip:
                self.log.error(("IP is not provided for '{}'"
                                .format(name)))
                return False

            out_dict[name] = utils.ip.reltoa(
                net['NETWORK'], relative_ip, self.version
            )
            return True

        for elem in rev_links:
            if elem == "group":
                for gid in rev_links[elem]:
                    try:
                        group = Group(id=ObjectId(gid),
                                      mongo_db=self._mongo_db)
                    except RuntimeError:
                        self.log.error('No group with id={} found.'
                            .format(gid))
                        continue
                    tmp_dict = group.get_allocated_ips(self)
                    if not tmp_dict:
                        continue

                    for nodename in tmp_dict:
                        add_to_out_dict(nodename, tmp_dict[nodename])

            if elem == "switch":
                for sid in rev_links[elem]:
                    switch = Switch(id=ObjectId(sid), mongo_db=self._mongo_db)
                    add_to_out_dict(switch.name, switch.get_rel_ip())

            if elem == "otherdev":
                for oid in rev_links[elem]:
                    odev = OtherDev(id=ObjectId(oid), mongo_db=self._mongo_db)
                    add_to_out_dict(odev.name, odev.get_ip(self.id))

        add_to_out_dict(net['ns_hostname'], net['ns_ip'])

        return out_dict

    @property
    def zone_data(self):
        zone_dict = {}
        master_ip = self.get('ns_ip')
        zone_dict['zone_name'] = self.name
        zone_dict['ns_hostname'] = self.get('ns_hostname')
        zone_dict['ns_ip'] = master_ip
        zone_dict['version'] = self.version
        zone_dict['hosts'] = self.resolve_used_ips()
        for key in ['include', 'rev_include']:
            if key in self._json and bool(self._json[key]):
                zone_dict[key] = self._json[key]
            else:
                zone_dict[key] = ''

        if self.version == 4:

            """
            # here we need to find first octet in IP address
            # which varies.
            # 191.168.1.2, 191.168.1.254   => 3
            # 10.141.0.1,  10.141.255.254  => 2
            # find min and max IPs
            ips = zone_dict['hosts'].values()
            ips.sort()
            ip_max = 0
            ip_min = utils.ip.aton('255.255.255.255')
            for ip in ips:
                ip_num = utils.ip.aton(ip, ver=self.version)
                if ip_num < ip_min:
                    ip_min = ip_num
                if ip_num > ip_max:
                    ip_max = ip_num

            # now we have first and last IPs:
            ip_min = utils.ip.ntoa(ip_min).split('.')
            ip_max = utils.ip.ntoa(ip_max).split('.')
            mutable_octet = 0
            for i in range(len(ip_min)):
                if ip_min[i] != ip_max[i]:
                    break
                mutable_octet = i
            """

            prefix = self.get('prefix')

            if prefix < 8:
                prefix = 8
            if prefix > 24:
                prefix = 24

            mutable_octet = self.get('PREFIX')//8
            tmp = master_ip.split('.')[:mutable_octet]
            zone_dict['rev_zone_name'] = '.'.join(reversed(tmp))
            zone_dict['rev_hosts'] = {}
            for host in zone_dict['hosts']:
                ip = zone_dict['hosts'][host]
                ip_reversed = list(reversed(ip.split('.')))
                ptr = ip_reversed[:(4-mutable_octet)]
                ptr = '.'.join(ptr)
                ptr_hostname = host + '.' + self.name + '.'
                zone_dict['rev_hosts'][ptr] = ptr_hostname
            return zone_dict

        # IPv6
        prefix = self.get('prefix')
        # IPv6 PTR uses nibbles (4 bits)
        # https://tools.ietf.org/html/rfc3596
        if prefix < 4:
            prefix = 4
        if prefix > 124:
            prefix = 124
        mutable_octet = self.get('PREFIX')//4
        master_nibbles = utils.ip.ipv6_unwrap(master_ip)
        # master_nibbles in fe80:0000:0000:0000:ffff:ffff:ffff:fffe format
        # need to get it in f.e.8.0.0.0.0.0 ... format
        master_nibbles_list = "".join(master_nibbles.split(':'))
        master_nibbles_list = list(master_nibbles_list)
        tmp = master_nibbles_list[:mutable_octet]
        zone_dict['rev_zone_name'] = '.'.join(reversed(tmp))
        zone_dict['rev_hosts'] = {}

        for host in zone_dict['hosts']:
            ip = zone_dict['hosts'][host]
            host_nibbles = utils.ip.ipv6_unwrap(ip)
            host_nibbles_list = "".join(host_nibbles.split(':'))
            host_nibbles_list = list(host_nibbles_list)
            host_nibbles_list_reversed = list(reversed(host_nibbles_list))
            ptr = host_nibbles_list_reversed[:(32-mutable_octet)]
            ptr = '.'.join(ptr)
            ptr_hostname = host + '.' + self.name + '.'
            zone_dict['rev_hosts'][ptr] = ptr_hostname

        return zone_dict

    def get_ip_macs(self):

        from luna.group import Group

        net = self._json

        try:
            rev_links = net[usedby_key]
        except:
            self.log.error(("No IPs configured for network '{}'"
                            .format(self.name)))
            return {}

        group_macs_list = []

        for elem in rev_links:

            if elem != "group":
                continue

            for gid in rev_links[elem]:
                try:
                    group = Group(id=ObjectId(gid),
                                  mongo_db=self._mongo_db)
                except RuntimeError:
                    self.log.error('No group with id={} found.'
                        .format(gid))
                    continue

                tmp_dict = group.get_macs(self)

                if not tmp_dict:
                    continue

                group_macs_list.append(tmp_dict)

        if not group_macs_list:
            return {}

        out_dict = group_macs_list.pop()

        for elem in group_macs_list:
            out_dict.update(elem)

        return out_dict
