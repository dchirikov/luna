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

from config import use_key, usedby_key

import re
import logging
import datetime

from luna import utils
from luna.base import Base
from luna.cluster import Cluster
from luna.switch import Switch
from luna.group import Group
from tornado import template


class Node(Base):
    """Class for operating with node objects"""

    log = logging.getLogger(__name__)

    def __init__(self, name=None, mongo_db=None, create=False,
                 id=None, group=None, localboot=False, setupbmc=True,
                 service=False, comment=''):
        """
        name  - optional
        group - the group the node belongs to; required

        FLAGS:
        localboot - boot from localdisk
        setupbmc  - whether we setup ipmi on install
        service   - do not install, boot into installer (dracut environment)
        """

        self.log.debug("function {} args".format(self._debug_function()))

        # Define the schema used to represent node objects

        self._collection_name = 'node'
        self._keylist = {
            'port': type(''),
            'localboot': type(True),
            'setupbmc': type(True),
            'service': type(True),
            'mac': type(''),
            'comment': type(''),
        }

        # Check if this node is already present in the datastore
        # Read it if that is the case

        node = self._get_object(name, mongo_db, create, id)
        self.group = None
        if group:
            if type(group) == Group:
                self.group = group
            if type(group) == str:
                self.group = Group(group, mongo_db=self._mongo_db)

        if create:

            if not group:
                err_msg = "Group needs to be specified when creating node."
                self.log.error(err_msg)
                raise RuntimeError, err_msg

            cluster = Cluster(mongo_db=self._mongo_db)

            # If a name is not provided, generate one

            if not bool(name):
                name = self._generate_name(cluster, mongo_db=mongo_db)

            # Store the new node in the datastore

            node = {'name': name, 'group': self.group.DBRef, 'interfaces': {},
                    'mac': None, 'switch': None, 'port': None,
                    'localboot': localboot, 'setupbmc': setupbmc,
                    'service': service, 'comment': comment}

            self.log.debug("Saving node '{}' to the datastore".format(node))

            self.store(node)

            # check if we are able to allocate IPs  for all interfaces
            error_on_alloc = False
            configured_interfaces = []
            for interface_name in self.group.list_ifs().keys():
                configured_interfaces.append(interface_name)
                if not self.add_ip(interface_name):
                    error_on_alloc = True
                    break

            if error_on_alloc:
                # roll back allocations and throw exception
                for interface_name in configured_interfaces[:-1]:
                    self.del_ip(interface_name)
                err_msg = ("Unable to allocate IP address " +
                    "for interface '{}'").format(configured_interfaces[-1])
                self.log.error(err_msg)
                raise RuntimeError, err_msg

            # Link this node to its group and the current cluster

            self.link(self.group)
            self.link(cluster)

        if group:
            # check if group specified is the group node belongs to
            if self.group.DBRef != self._json['group']:
                err_msg = ("DBref of the group is not the same " +
                           "the node node belongs to")
                self.log.error(err_msg)
                raise RuntimeError, err_msg

        self.log = logging.getLogger(__name__ + '.' + self._json['name'])

    def _get_group(self):
        if not self.group:
            self.group = Group(
                id=self._json['group'].id, mongo_db=self._mongo_db
            )
        return True

    def _generate_name(self, cluster, mongo_db):
        """Based on every node linked to the cluster
           generate a name for the new node"""

        prefix = cluster.get('nodeprefix')
        digits = cluster.get('nodedigits')
        back_links = cluster.get_back_links()

        max_num = 0

        for link in back_links:

            # Skip non node objects

            if link['collection'] != self._collection_name:
                continue

            node = Node(id=link['DBRef'].id, mongo_db=mongo_db)
            name = node.name

            try:
                node_number = int(name.lstrip(prefix))
            except ValueError:
                continue

            if node_number > max_num:
                max_num = node_number

        new_name = prefix + str(max_num + 1).zfill(digits)

        return new_name

    def list_ifs(self):
        self._get_group()
        return self.group.list_ifs()

    def add_interface(self, interface_name=None):

        if not interface_name:
            self.log.error("Interface should be specified")
            return False

        interface_uuid = None
        # we will get group insterfaces to make sure
        # that we can add/configure such interface
        interface_dict = self.list_ifs()

        if not interface_name in interface_dict:
            self.log.error("Interface {} does not exist"
                .format(interface_name))
            return False

        interface_uuid = interface_dict[interface_name]

        interface_ips = {'4': None, '6': None}
        new_interfaces = {}

        for key in self._json['interfaces']:
            new_interfaces[key] = self._json['interfaces'][key].copy()

        new_interfaces[interface_uuid] = interface_ips
        res = self.set('interfaces', new_interfaces)

        return res

    def del_interface(self, interface_name=None, interface_uuid=None):

        if not interface_name and not interface_uuid:
            self.log.error("Interface should be specified")
            return False

        if not interface_uuid:

            interface_dict = self.list_ifs()

            if not interface_name in interface_dict:
                self.log.error("Interface {} does not exist"
                    .format(interface_name))
                return False

            interface_uuid = interface_dict[interface_name]

        interfaces = self._json['interfaces']

        if interface_uuid not in interfaces:
            self.log.error("Interface with UUID {} does not exist"
                .format(interface_uuid))
            return False

        new_interfaces = {}

        if interfaces[interface_uuid]['4'] or interfaces[interface_uuid]['6']:
            self.log.error(("IP addresses are configured for interface {}. " +
                            "Will not delete interface.")
                           .format(interface_uuid))
            return False

        for key in interfaces:
            new_interfaces[key] = interfaces[key].copy()

        new_interfaces.pop(interface_uuid)
        res = self.set('interfaces', new_interfaces)

        return res

    def add_ip(self, interface_name=None, new_ip=None, version=None):

        interface_uuid = None

        if interface_name:
            interface_dict = self.list_ifs()
            interface_uuid = interface_dict[interface_name]
        else:
            self.log.error("Interface should be specified")
            return None

        interfaces = self._json['interfaces']

        # First check if we have some bits for this interface,
        # if no - create empty. Latter should be the case
        # on node creation
        if interface_uuid in interfaces:
            interface_ips = interfaces[interface_uuid]
        else:
            interface_ips = {'4': None, '6': None}

        # Tiny list for storing IPvX keys for which IP
        # can be assigned: [], ['4'], ['6'], ['4', '6']
        no_ip_keys = []
        for key in interface_ips:
            if not interface_ips[key]:
                no_ip_keys.append(key)

        # Check if passed version in that list
        # If no - we are unable to proceed
        if version and version not in no_ip_keys:
            self.log.error("Interface '{}' has IPv{} address already"
                .format(interface_name, version))
            return False

        # No we know which IPvX we need to assign
        # if version is specified - use it
        if version:
            versions_to_assign = [version]
        else:
            versions_to_assign = no_ip_keys[:]

        # on this step we have versions_to_assign, but we are not sure
        # if we can as network for this IPvX could not exist in corresponding
        # group. So add only those who have.
        tmp = versions_to_assign[:]
        versions_to_assign = []
        for v in range(len(tmp)):
            group_if = self.group._json['interfaces'][interface_uuid]
            net = group_if['network'][tmp[v]]
            if net:
                versions_to_assign.append(tmp[v])

        # versions_to_assign contains all IPvX we can assign finally
        # Now we can report an error if we unable to meet assignment
        # if 'version' passed as parameter
        if version and version not in versions_to_assign:
            self.log.error(
                ("Unable to assign IP address IPv{} for interface {}, "
                 + "as network is not configured")
                .format(version, interface_name)
            )
            return False

        # Finally we can acquire IPs
        ips = {}  # for rolling back if needed
        for ver in versions_to_assign:
            ip = self.group.manage_ip(interface_uuid, new_ip, version=ver)
            interface_ips[ver] = ip
            if not ip:
                self.log.error(
                    "Could not reserve IP {} (IPv{}) for {} interface"
                    .format(new_ip or '', ver, interface_name or 'this'))
                for v in ips:
                    self.group.manage_ip(
                        interface_uuid,
                        ip=ips[v],
                        release=True,
                        version=v
                    )
                return False
            ips[ver] = ip

        all_interfaces = self._json['interfaces']
        all_interfaces[interface_uuid] = interface_ips
        res = self.set('interfaces', all_interfaces)

        return res

    def _get_interface(self, name=None, uuid=None):
        """
        returns (interface_name, interface_uuid, if_dict)
        return (None, None, {}) if no interface is configured
        """
        if not (name or uuid):
            self.log.error('Interface name or interface UUID ' +
                           'should be specified')
            return (None, None, {})

        interfaces = self._json['interfaces']

        if uuid and uuid not in interfaces:
            self.log.error("No interface with UUID '{}'."
                .format(uuid))
            return (None, None, {})

        if name:
            interface_dict = self.list_ifs()
            if name not in interface_dict:
                self.log.error("No such interface '{}'".format(name))
                return (None, None, {})
            uuid = interface_dict[name]

        else:
            # get interface name
            self._get_group()
            group_if = self.group._json['interfaces'][uuid]
            name = group_if['name']

        if not uuid or uuid not in interfaces:
            self.log.error('Unable to find UUID for interface {}'
                    .format(name))
            return (None, None, {})

        if_dict = interfaces[uuid]

        return (name, uuid, if_dict)

    def _unconfigure_if(self, interface_uuid=None, version=None):
        """
        Helper to unconfigure (unassign) IP addresses from interface
        """

        (interface_name,
         interface_uuid,
         if_dict) = self._get_interface(None,
                                        interface_uuid)

        if not interface_uuid:
            self.log.error("interface UUID needs to be specified.")
            return False

        # check if we have correct 'version' parameter
        if version:
            version = str(version)

        if version and version not in ['4', '6', 'all']:
            self.log.error("Only IPv4 and IPv6 are supported.")
            return False

        # store all versions for which IPs are configured

        ips_configured = []

        for key in if_dict:
            if if_dict[key]:
                ips_configured.append(key)

        # check if there is no ambiguity

        if not version and len(ips_configured) == 2:
            self.log.error("Both IPv4 and IPv6 are configured for interface.")
            return False

        # then check if 'version' specified has IP configured

        if version and version != 'all' and version not in ips_configured:
            self.log.error("IPv{} is not configured for {}."
                .format(version, interface_name))
            return False

        # 'versions' variable will contan IP versions we need to remove
        # if no 'version' == 'all' is specified - remove all configured IPs

        versions = []

        if version in ['4', '6']:
            versions = [version]

        # here we know that len(ips_configured) == 1 or version == 'all'

        if not versions or version == 'all':
            versions = ips_configured

        released_ips = {}

        if not versions and version == 'all':
            # Seems like we were asked to unconfigure 'empty' interface
            # No IPs are configured
            return True

        if not versions:
            self.log.error("No IPs are configured for {}."
                .format(interface_name))
            return False

        for ver in versions:
            if_ip_assigned = if_dict[ver]
            res = self.group.manage_ip(interface_uuid, if_ip_assigned,
                                       release=True, version=ver)

            if not res:

                self.log.error("Unable to release {} for {}."
                    .format(if_ip_assigned, interface_name))

                # roll back using released_ips

                for v in released_ips:
                    self.group.manage_ip(interface_uuid, released_ips[v],
                                         release=False, version=v)

                return False
            released_ips[ver] = if_ip_assigned

        return released_ips

    def del_ip(self, interface_name=None, version=None):

        self._get_group()

        interfaces = self._json['interfaces']

        if not interfaces:
            self.log.error("Node has no interfaces configured")
            return False

        new_interfaces = interfaces.copy()

        # if no interface_name is defined
        # release all ips

        if not interface_name:
            for if_uuid in interfaces:

                unconf_res = self._unconfigure_if(if_uuid, 'all')

                if unconf_res:
                    new_interfaces.pop(if_uuid)
                else:
                    self.log.error("Unable to unconfigure interface {}."
                        .format(if_uuid))
                    return False
            res = self.set('interfaces', new_interfaces)
            return res

        # here interface_name is defined,
        # so release this IP

        interface_uuid = None

        interface_dict = self.list_ifs()

        if interface_name not in interface_dict:
            self.log.error("Node does not have an '{}' interface"
                .format(interface_name))
            return False

        interface_uuid = interface_dict[interface_name]
        unconf_res = self._unconfigure_if(interface_uuid, version)
        if not unconf_res:
            self.log.error("Unable to unconfigure interface {}"
                .format(interface_name))
            return False

        if unconf_res:
            for ver in unconf_res:
                new_interfaces[interface_uuid][ver] = None

        res = self.set('interfaces', new_interfaces)
        return res

    @property
    def boot_params(self):
        """will return dictionary with all needed params for booting:
           kernel, initrd, kernel opts, ip, net, prefix"""

        params = {}
        self._get_group()
        group_params = self.group.boot_params

        params = group_params.copy()

        if not params['kernel_file']:
            self.log.error('No kernel file found for node.')

        if not params['initrd_file']:
            self.log.error('No initrd file found for node.')

        params['bootproto'] = 'dhcp'

        params['name'] = self.name

        params['hostname'] = self.name

        if params['domain']:
            params['hostname'] += "." + params['domain']

        params['service'] = int(self.get('service'))
        params['localboot'] = int(self.get('localboot'))

        interfaces = self.list_ifs()
        boot_if_uuid = None

        params['mac'] = self.get_mac()

        if not params['mac']:
            self.log.warning('No MAC found for node')
            params['mac'] = ''
            params['net'] = {}
            return params

        if 'BOOTIF' in interfaces:
            boot_if_uuid = interfaces['BOOTIF']
            for ver in ['4', '6']:
                if ver in group_params['net']:
                    params['net'][ver] = group_params['net'][ver].copy()
                    params['net'][ver]['ip'] = self.get_ip(
                        interface_uuid=boot_if_uuid,
                        version=int(ver),
                        quiet=True
                    )

                    params['bootproto'] = 'static'

        return params

    @property
    def install_params(self):
        params = {}
        self._get_group()
        params = self.group.install_params

        params['name'] = self.name
        params['setupbmc'] = self.get('setupbmc')
        params['mac'] = self.get_mac() or ''

        if params['domain']:
            params['hostname'] = self.name + "." + params['domain']
        else:
            params['hostname'] = self.name

        for interface in params['interfaces']:
            for ver in ['4', '6']:

                ip = self.get_ip(
                    interface_name=interface,
                    version=int(ver),
                    quiet=True
                )

                if not ip:
                    continue

                params['interfaces'][interface][ver]['ip'] = ip

        return params

    def show(self):
        def get_value(dbref):
            mongo_collection = self._mongo_db[dbref.collection]
            try:
                name = mongo_collection.find_one({'_id': dbref.id})['name']
                name = '[' + name + ']'
            except:
                name = '[id_' + str(dbref.id) + ']'
            return name

        json = self._json.copy()

        for attr in self._json:
            if attr in ['_id', use_key, usedby_key]:
                json.pop(attr)

        json['group'] = get_value(json['group'])
        if json['switch']:
            json['switch'] = get_value(json['switch'])

        return json

    def set_group(self, new_group_name=None):
        """
        Method to change group for node
        """
        if not new_group_name:
            self.log.error("Group needs to be specified")
            return False

        self._get_group()
        new_group = Group(new_group_name, mongo_db=self._mongo_db)

        old_group_interfaces = self.group._json['interfaces']

        # Dictionary to store old IPs
        old_ips = {'4': {}, '6': {}}
        old_interfaces = self._json['interfaces']

        for if_uuid in old_interfaces:
            for ver in ['4', '6']:
                old_ip = old_interfaces[if_uuid][ver]
                if old_ip:
                    old_if_name = old_group_interfaces[if_uuid]['name']
                    old_ip = self.get_ip(interface_uuid=if_uuid, version=ver)
                    old_net = old_group_interfaces[if_uuid]['network'][ver]
                    old_ips[ver][old_if_name] = {'ip': old_ip,
                                                 'network': old_net}

        self.log.debug('Old IPs dictionary: {}'.format(old_ips))

        self.log.debug('Release all IPs from node')
        self.del_ip()

        self.log.debug('Unlink old group from node')
        self.unlink(self.group)

        self.log.debug('Set new group')
        res = self.set('group', new_group.DBRef)

        if not res:
            self.log.error('Unable to set new group. Please delete node.')
            return False

        self.log.debug('Link with new group')
        self.link(new_group)

        self.log.debug('Update self.group')
        self.group = None
        self._get_group()

        new_group_interfaces = new_group._json['interfaces']
        new_interfaces = {}
        for uuid in new_group_interfaces:
            new_interfaces[uuid] = {'4': None, '6': None}

        self.set('interfaces', new_interfaces)

        new_ifs = self.list_ifs()

        for new_if_name in new_ifs:
            for ver in ['4', '6']:
                if_uuid = new_ifs[new_if_name]
                if new_group_interfaces[if_uuid]['network'][ver]:
                    self.add_ip(new_if_name, version=ver)

        self.log.debug('Automatically assigned IPs: {}'
                       .format(self._json['interfaces']))

        self.log.debug('Restore IPs')

        self.log.debug('First try to restore by name')

        # clone old_ips to tmp_dict
        # we need it , as we will .pop old_ips later
        tmp_dict = {'4': {}, '6': {}}
        for ver in tmp_dict:
            tmp_dict[ver] = old_ips[ver].copy()

        for if_uuid in new_group_interfaces:
            for ver in ['4', '6']:
                for old_if_name in tmp_dict[ver]:
                    new_if_dict = new_group_interfaces[if_uuid]
                    if old_if_name != new_if_dict['name']:
                        continue

                    self.log.debug(
                        'Old interface name is the same as new: {}'
                        .format(old_if_name)
                    )

                    new_net = new_group_interfaces[if_uuid]['network'][ver]

                    if not new_net:
                        self.log.debug(
                            "No network assigned for the interface."
                        )
                        continue

                    if not new_net == old_ips[ver][old_if_name]['network']:
                        self.log.debug(
                            "New network is not the same " +
                            "as the old one for the interface."
                        )
                        continue

                    self.log.debug(
                        'Network IPv{} is assigned on {}'
                        .format(ver, old_if_name)
                    )

                    auto_ip = self.get_ip(interface_name=old_if_name,
                                          version=ver)
                    old_ip = old_ips[ver][old_if_name]['ip']

                    self.log.debug(
                        "Automatically assigned IP {} for {}"
                        .format(auto_ip, new_if_dict['name'])
                    )

                    self.log.debug(
                        "Trying to restore {} for {} in new group"
                        .format(old_ip, old_if_name)
                    )

                    self.set_ip(interface_name=old_if_name, ip=old_ip)

                    self.log.debug('Modified node interface dictionary: {}'
                                   .format(self._json['interfaces']))

                    old_ips[ver].pop(old_if_name)

                    self.log.debug(
                        'Modified old interfaces dictionary: {}'
                        .format(old_ips)
                    )

        self.log.debug(
            'Old interfaces dictionary: {}'
            .format(old_ips)
        )

        self.log.debug('Try to restore using networks')

        # clone old_ips to tmp_dict
        tmp_dict = {'4': {}, '6': {}}
        for ver in tmp_dict:
            tmp_dict[ver] = old_ips[ver].copy()

        for if_uuid in new_group_interfaces:
            for ver in ['4', '6']:
                for old_if_name in tmp_dict[ver]:

                    new_net = new_group_interfaces[if_uuid]['network'][ver]
                    old_net = tmp_dict[ver][old_if_name]['network']

                    if old_net == new_net:

                        new_if_name = new_group_interfaces[if_uuid]['name']

                        self.log.debug(
                            "New/old {}/{} have the same net {}"
                            .format(new_if_name, old_if_name, new_net)
                        )

                        old_ip = tmp_dict[ver][old_if_name]['ip']

                        self.log.debug(
                            "Restoring {} for {}"
                            .format(old_ip, new_if_name)
                        )

                        self.set_ip(interface_name=new_if_name, ip=old_ip)

        return True

    def set_ip(self, interface_name=None,
               interface_uuid=None, ip=None, force=False):

        """
        Method to set/change IP
        returns   False is wrong parameters passed
                  or error occured
        otherwise True
        """

        (interface_name,
         interface_uuid,
         if_dict) = self._get_interface(interface_name,
                                        interface_uuid)

        if not interface_uuid:
            return False

        if not ip:
            self.log.error("IP address should be provided")
            return False

        ipver = utils.ip.get_ip_version(ip)

        if not ipver:
            self.log.error("Wrong IP address is provided")
            return False

        ipver = str(ipver)

        if force:
            self._json['interfaces'][interface_uuid][ipver] = None
            res = self.add_ip(interface_name, ip, version=ipver)
            if not res:
                self.log.error("Error on adding IP occurred.")
                return False
            return True

        old_ip = self.get_ip(interface_name, version=ipver)

        if not old_ip:
            self.log.error("Unable to get IP for interface.")
            return False

        res = self.del_ip(interface_name, version=ipver)

        if not res:
            self.log.error("Error on releasing IP occurred.")
            return False

        res = self.add_ip(interface_name, ip, version=ipver)
        if not res and old_ip:
            self.log.error("Error on adding IP occurred.")
            self.add_ip(interface_name, old_ip, version=ipver)
            return False

        return True

    def set_mac(self, mac=None):
        if not mac:
            mac = self.get_mac()
            self._mongo_db['switch_mac'].remove({'mac': mac})
            self._mongo_db['mac'].remove({'mac': mac})

        elif re.match('(([a-fA-F0-9]{2}:){5}([a-fA-F0-9]{2}))$', mac):
            mac = mac.lower()
            utils.helpers.set_mac_node(mac, self.DBRef, (self._mongo_db))

        else:
            self.log.error("Invalid MAC address '{}'".format(mac))
            return False

        return True

    def set_switch(self, value):
        if value:
            switch = self._json['switch']
            new_switch = Switch(value, mongo_db=self._mongo_db).DBRef

        elif self._json['switch'] is None:
            return True

        else:
            switch = self._json['switch']
            new_switch = None

        res = self.set('switch', new_switch)

        if res and value:
            self.link(new_switch)

        if res and switch:
            self.unlink(Switch(id=switch.id, mongo_db=self._mongo_db).DBRef)

        return bool(res)

    def get_ip(self, interface_name=None, interface_uuid=None,
               format='human', version=None, quiet=False):

        # convert version to str, as mongo umable to use int as keys
        if version:
            version = str(version)

        if version and version not in ['4', '6']:
            self.log.error("Version should be '4' or '6'")
            return False

        (interface_name,
         interface_uuid,
         if_dict) = self._get_interface(interface_name,
                                        interface_uuid)

        if not interface_uuid:
            return False

        # if 'version' is unspecified we can proceed only if IPv6 or IPv4
        # configured. Not both.
        if if_dict['4'] and if_dict['6'] and not version:
            self.log.error('Both IPv4 and IPv6 IP addresses are configured.' +
                           'Version should be specified.')
            return False

        ipnum = None

        if not version:
            if if_dict['4']:
                version = '4'
            elif if_dict['6']:
                version = '6'

        if not version:
            if not quiet:
                self.log.error(
                    ('No IP addresses or networks ' +
                     'are configured for interface {}')
                    .format(interface_name)
                )
            return False

        ipnum = if_dict[version]

        if not ipnum:
            if not quiet:
                self.log.error(
                    "No IPv{} address or network are configured for '{}'"
                    .format(version, interface_name))
            return False

        if format == 'num':
            return ipnum
        else:
            self._get_group()
            return self.group.get_ip(interface_uuid, ipnum,
                                     format='human', version=version)

    def get_mac(self):
        try:
            mac = str(self._mongo_db['mac']
                      .find_one({'node': self.DBRef})['mac'])
        except:
            mac = None

        return mac

    def update_status(self, step=None):
        if not bool(step):
            self.log.error("No data to update status of the node.")
            return None

        if not bool(re.match('^[ a-zA-Z0-9\.\-_]+?$', step)):
            self.log.error(("'Step' parameter in contains invalid string."
                            .format(self.name)))
            return None

        status = {'step': step, 'time': datetime.datetime.utcnow()}
        return self.set('status', status)

    def get_status(self, relative=True):
        try:
            status = self._json['status']
            step = str(status['step'])
            time = status['time']
        except:
            return None

        now = datetime.datetime.utcnow()
        tracker_records = []
        tracker_record = {}
        tor_time = datetime.datetime(1, 1, 1)
        perc = 0.0

        if step == 'install.download':
            name = "%20s" % self.boot_params['hostname']
            peer_id = ''.join(["{:02x}".format(ord(l)) for l in name])
            self._mongo_db
            tracker_collection = self._mongo_db['tracker']
            tracker_records = tracker_collection.find({'peer_id': peer_id})

        for doc in tracker_records:
            try:
                tmp_time = doc['updated']
            except:
                continue
            if tmp_time > tor_time:
                tracker_record = doc
                tor_time = tmp_time

        if bool(tracker_record):
            try:
                left = tracker_record['left']
                downloaded = tracker_record['downloaded']
                perc = 100.0*downloaded/(downloaded+left)
            except:
                tor_time = datetime.datetime(1, 1, 1)
                perc = 0.0

        if bool(perc) and (tor_time > time):
            status = ("%s (%.2f%% / last update %isec)"
                      % (step, perc, (now - tor_time).seconds))
        else:
            status = step

        if relative:
            sec = (now - time).seconds
            ret_time = str(datetime.timedelta(seconds=sec))
        else:
            ret_time = str(time)

        return {'status': status, 'time': ret_time}

    def release_resources(self):
        mac = self.get_mac()
        self._mongo_db['switch_mac'].remove({'mac': mac})
        self._mongo_db['mac'].remove({'mac': mac})

        self.del_ip()

        return True

    def render_script(self, name):

        scripts = ['boot', 'install']

        if name not in scripts:

            self.log.error(
                "'{}' is not correct script. Valid options are: '{}'"
                .format(name, scripts)
            )

            return None

        cluster = Cluster(mongo_db=self._mongo_db)
        self._get_group()
        path = cluster.get('path')
        tloader = template.Loader(path + '/templates')

        if cluster.get('frontend_https'):
            protocol = 'https'
        else:
            protocol = 'http'

        server_ip = cluster.get('frontend_address')
        server_port = cluster.get('frontend_port')

        if name == 'boot':
            p = self.boot_params
            p['protocol'] = protocol
            p['server_ip'] = server_ip
            p['server_port'] = server_port
            return tloader.load('templ_nodeboot.cfg').generate(p=p)

        if name == 'install':
            p = self.install_params
            p['protocol'] = protocol
            p['server_ip'] = server_ip
            p['server_port'] = server_port
            res = tloader.load('templ_install.cfg').generate(p=p)

            return res
