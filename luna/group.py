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
import uuid

from bson.objectid import ObjectId

from luna import utils
from luna.base import Base
from luna.cluster import Cluster
from luna.network import Network
from luna.osimage import OsImage
from luna.bmcsetup import BMCSetup


class Group(Base):
    """Class for operating with group records"""

    log = logging.getLogger(__name__)

    def __init__(self, name=None, mongo_db=None, create=False,
                 id=None, prescript='', bmcsetup=None,
                 partscript='', osimage=None, interfaces=[],
                 postscript='', torrent_if=None, domain=None,
                 comment=''):
        """
        prescript   - preinstall script
        bmcsetup    - bmcsetup options
        partscript  - parition script
        osimage     - osimage
        interfaces  - list of the newtork interfaces
        postscript  - postinstall script
        """

        self.log.debug("function args {}".format(self._debug_function()))

        # Define the schema used to represent group objects

        self._collection_name = 'group'
        self._keylist = {
            'prescript': type(''),
            'partscript': type(''),
            'postscript': type(''),
            'torrent_if': type(''),
            'comment': type(''),
        }

        # Check if this group is already present in the datastore
        # Read it if that is the case

        group = self._get_object(name, mongo_db, create, id)

        if create:
            cluster = Cluster(mongo_db=self._mongo_db)
            osimageobj = OsImage(osimage, mongo_db=self._mongo_db)

            (bmcobj, domainobj) = (None, None)
            if bmcsetup:
                bmcobj = BMCSetup(bmcsetup, mongo_db=self._mongo_db).DBRef

            if domain:
                domainobj = Network(domain, mongo_db=self._mongo_db).DBRef

            if interfaces and type(interfaces) is not list:
                err_msg = "'interfaces' should be list"
                self.log.error(err_msg)
                raise RuntimeError, err_msg

            if not interfaces:
                interfaces = []

            if_dict = {}
            for interface in interfaces:
                if_dict[uuid.uuid4().hex] = {
                    'name': interface,
                    'network': {
                        '4': None,
                        '6': None
                    },
                    'params': ''
                }

            if not partscript:
                partscript = "mount -t tmpfs tmpfs /sysroot"

            if not postscript:
                postscript = ("cat << EOF >> /sysroot/etc/fstab\n"
                              "tmpfs   /       tmpfs    defaults        0 0\n"
                              "EOF")

            # Store the new group in the datastore

            group = {
                'name': name, 'prescript':  prescript,
                'bmcsetup': bmcobj, 'partscript': partscript,
                'osimage': osimageobj.DBRef, 'interfaces': if_dict,
                'postscript': postscript, 'domain': domainobj,
                'torrent_if': torrent_if, 'comment': comment,
            }

            self.log.debug("Saving group '{}' to the datastore".format(group))

            self.store(group)

            # Link this group to its dependencies and the current cluster

            self.link(cluster)

            if bmcobj:
                self.link(bmcobj)

            if domainobj:
                self.link(domainobj)

            self.link(osimageobj)

        self.log = logging.getLogger('group.' + self._name)
        self._networks = {}

    @property
    def boot_params(self):
        params = {}

        osimage = OsImage(id=self.get('osimage').id, mongo_db=self._mongo_db)
        params['kernel_file'] = osimage.get('kernfile')
        params['initrd_file'] = osimage.get('initrdfile')
        params['kern_opts'] = osimage.get('kernopts')
        params['domain'] = ''
        params['net'] = {}
        domaindbref = self.get('domain')

        if domaindbref:

            domainnet = self._get_network(netid=domaindbref.id)

            params['domain'] = domainnet.name

        if_list = self.list_ifs()
        bootif_uuid = None

        if 'BOOTIF' in if_list:
            bootif_uuid = if_list['BOOTIF']

        if not bootif_uuid:
            return params

        interfaces = self.get('interfaces')

        if not 'network' in interfaces[bootif_uuid]:
            return params

        for ver in ['4', '6']:
            if interfaces[bootif_uuid]['network'][ver]:
                params['net'][ver] = {}
                net_id = interfaces[bootif_uuid]['network'][ver].id
                net = self._get_network(netid=net_id)
                params['net'][ver]['prefix'] = str(net.get('PREFIX'))
                params['net'][ver]['mask'] = str(net.get('NETMASK'))

        if bootif_uuid and not params['net']:
            self.log.warning('No network is configured for BOOTIF')

        return params

    @property
    def install_params(self):
        params = {}
        params['prescript'] = self.get('prescript')
        params['partscript'] = self.get('partscript')
        params['postscript'] = self.get('postscript')
        params['torrent_if'] = self.get('torrent_if')
        params['domain'] = ''

        domaindbref = self.get('domain')

        if domaindbref:
            domainnet = self._get_network(netid=domaindbref.id)

            params['domain'] = domainnet.name

        interfaces = self.get('interfaces')
        if_list = self.list_ifs()

        # now find torrent_if name and net prefix

        if params['torrent_if'] and not params['torrent_if'] in if_list.keys():

            self.log.error(
                ('No such interface {}. Unable to ' +
                 'set torrent_if').format(params['torrent_if'])
            )

            params['torrent_if'] = ''

        params['interfaces'] = {}

        for nic_uuid in interfaces:
            nic_name = interfaces[nic_uuid]['name']

            params['interfaces'][nic_name] = {}

            nicopts = self.get_if_params(nic_name).strip()

            params['interfaces'][nic_name]['options'] = nicopts

            for ver in ['4', '6']:
                params['interfaces'][nic_name][ver] = {
                    'prefix': '',
                    'netmask': '',
                    'ip': '',
                }
                if 'network' in interfaces[nic_uuid]:

                    net_prefix = ""
                    net_mask = ""

                    if not interfaces[nic_uuid]['network'][ver]:
                        continue

                    net_id = interfaces[nic_uuid]['network'][ver].id

                    net = self._get_network(netid=net_id)

                    net_prefix = str(net.get('PREFIX'))
                    net_mask = str(net.get('NETMASK'))

                    params['interfaces'][nic_name][ver]['prefix'] = net_prefix
                    params['interfaces'][nic_name][ver]['netmask'] = net_mask

        osimage = OsImage(id=self.get('osimage').id, mongo_db=self._mongo_db)

        params['kernver'] = osimage.get('kernver')
        params['kernopts'] = osimage.get('kernopts')
        params['torrent'] = osimage.get('torrent')
        params['tarball'] = osimage.get('tarball')

        if params['torrent']:
            params['torrent'] += ".torrent"
        else:
            params['torrent'] = ''

        if params['tarball']:
            params['tarball'] += ".tgz"
        else:
            params['tarball'] = ''

        params['bmcsetup'] = {}
        if self.get('bmcsetup'):

            bmc = BMCSetup(id=self.get('bmcsetup').id, mongo_db=self._mongo_db)
            params['bmcsetup']['mgmtchannel'] = bmc.get('mgmtchannel') or 1
            params['bmcsetup']['netchannel'] = bmc.get('netchannel') or 1
            params['bmcsetup']['userid'] = bmc.get('userid') or 3
            params['bmcsetup']['user'] = bmc.get('user') or "ladmin"
            params['bmcsetup']['password'] = bmc.get('password') or "ladmin"

        return params

    def osimage(self, osimage_name):
        osimage = OsImage(osimage_name, mongo_db=self._mongo_db)

        old_image = self.get('osimage')
        self.unlink(old_image)

        res = self.set('osimage', osimage.DBRef)
        self.link(osimage.DBRef)

        return res

    def bmcsetup(self, bmcsetup_name=None):
        bmcsetup = None
        old_bmc = self.get('bmcsetup')

        if bmcsetup_name:
            bmcsetup = BMCSetup(bmcsetup_name, mongo_db=self._mongo_db)

        if old_bmc:
            self.unlink(old_bmc)

        if bmcsetup:
            res = self.set('bmcsetup', bmcsetup.DBRef)
            self.link(bmcsetup.DBRef)
        else:
            res = self.set('bmcsetup', None)

        return res

    def get_net_name_for_if(self, interface_name, version='4'):

        if version not in ['4', '6']:
            self.log.error("Only IPv4 and IPv6 are supported")
            return False

        interfaces_dict = self.get('interfaces')
        if_list = self.list_ifs()
        if interface_name not in if_list:
            self.log.error(
                "Interface '{}' does not exist".format(interface_name)
            )
            return ''

        nic_uuid = if_list[interface_name]
        nic = interfaces_dict[nic_uuid]
        if nic['network'][version]:
            net_id = nic['network'][version].id
            net = self._get_network(netid=net_id)
            return net.name
        else:
            return ''

    def list_ifs(self):
        """
        Inverts 'interfaces' dictionary
        Returns dictionary like {'eth0': 'uuid'}
        """
        interfaces = self.get('interfaces')
        if_list = {}
        for elem in interfaces:
            if_list[interfaces[elem][u'name']] = elem
        return if_list

    def rename_interface(self, interface_name, interface_new_name):
        interfaces = self.get('interfaces')
        if_list = self.list_ifs()

        if interface_name not in if_list.keys():
            self.log.error(
                "Interface '{}' does not exist".format(interface_name)
            )
            return None

        if interface_new_name in if_list.keys():
            self.log.error(
                "Interface '{}' already exists".format(interface_new_name)
            )
            return None

        interface_uuid = if_list[interface_name]
        interfaces[interface_uuid]['name'] = interface_new_name

        res = self.set('interfaces', interfaces)

        if not res:
            self.log.error(
                "Could not rename interface '{}'".format(interface_name)
            )
        if res:
            if interface_name == 'BOOTIF':
                self.log.info('No boot interface for nodes ' +
                              'in the group configured. ' +
                              'DHCP will be used during provisioning.')

            elif interface_name == 'BMC':
                self.log.warning('An interface named \'BMC\' ' +
                                 'needs to be defined ' +
                                 'in order to have node\'s BMC configured.')

        return res

    def show_if(self, interface_name=None, interface_uuid=None):

        if not interface_name and not interface_uuid:
            self.log.error("Interface should be specified")
            return False

        interfaces = self.get('interfaces')
        if_list = self.list_ifs()

        if not interface_uuid:
            try:
                interface_uuid = if_list[interface_name]
            except KeyError:
                self.log.error(
                    "Interface '{}' does not exist".format(interface_name)
                )
                return False

        if not interface_uuid in interfaces.keys():
            self.log.error(
                "Interface with UUID {} does not exist".format(interface_uuid)
            )
            return False

        if interface_name not in if_list.keys():
            return None

        params = {
            'options': interfaces[interface_uuid]['params'],
            'name': interfaces[interface_uuid]['name'],
            'network': {
                '4': {
                    'name': '',
                    'network': '',
                    'prefix': '',
                    'netmask': '',
                },
                '6': {
                    'name': '',
                    'network': '',
                    'prefix': '',
                    'netmask': '',
                },
            },

        }

        for ver in ['4', '6']:

            assigned_net_dbref = interfaces[interface_uuid]['network'][ver]

            if not assigned_net_dbref:
                continue

            assigned_net_obj = self._get_network(netid=assigned_net_dbref.id)

            params['network'][ver]['name'] = assigned_net_obj.name

            params['network'][ver]['network'] = assigned_net_obj.get('NETWORK')

            params['network'][ver]['prefix'] = str(
                assigned_net_obj.get('PREFIX')
            )

            params['network'][ver]['netmask'] = str(
                assigned_net_obj.get('NETMASK')
            )

        return params

    def add_interface(self, interface_name):
        interface_dict = self.get('interfaces')
        if_list = self.list_ifs()
        if interface_name in if_list.keys():
            self.log.error(
                "Interface '{}' already exists".format(interface_name)
            )
            return None

        interface_dict[uuid.uuid4().hex] = {'name': interface_name,
                                            'network': {
                                                '4': None,
                                                '6': None,
                                                },
                                            'params': ''}

        res = self.set('interfaces', interface_dict)

        if not res:
            self.log.error(
                "Could not add interface '{}'".format(interface_name)
            )

        reverse_links = self.get_back_links()
        for link in reverse_links:
            if link['collection'] == 'node':
                node_obj = Node(id=link['DBRef'].id, mongo_db=self._mongo_db)
                node_obj.add_interface(interface_name)

        return res

    def get_if_params(self, interface_name):
        interfaces_dict = self.get('interfaces')
        if_list = self.list_ifs()
        if interface_name not in if_list.keys():
            self.log.error(
                "Interface '{}' does not exist".format(interface_name)
            )
            return None
        interface_uuid = if_list[interface_name]
        return interfaces_dict[interface_uuid]['params']

    def set_if_params(self, interface_name, params=''):
        interfaces_dict = self.get('interfaces')
        if_list = self.list_ifs()
        if interface_name not in if_list.keys():
            self.log.error(
                "Interface '{}' does not exist".format(interface_name)
            )
            return None

        interface_uuid = if_list[interface_name]
        interfaces_dict[interface_uuid]['params'] = params.strip()
        res = self.set('interfaces', interfaces_dict)

        if not res:
            self.log.error("Could not configure '{}'".format(interface_name))

        return res

    def get_allocated_ips(self, net):

        interfaces = self.get('interfaces')

        if not isinstance(net, Network):
            self.log.error("net should be Network class. Unable to proceed.")
            return False

        ver = net.version

        # get all the interfaces with desired net configured in format:
        # {'uuid1': 'eth0', 'uuid2': 'BMC'}
        interfaces_with_net = {}
        for ifuuid in interfaces:
            interface = interfaces[ifuuid]
            if interface['network'][str(ver)] == net.DBRef:
                interfaces_with_net[ifuuid] = interface['name']

        # check if lower() will not cause name conflict
        # no bmc and BMC are configured at the same time
        lowered = False
        lower_names = [s.lower() for s in interfaces_with_net.values()]
        lower_names.sort()

        lower_names_set = list(set(lower_names))
        lower_names_set.sort()

        if lower_names_set == lower_names:
            lowered = True

        # enumerate all the node in group now

        ips = {}

        if not self.get(usedby_key) or not 'node' in self.get(usedby_key):
            # No nodes in group. Returning empty list
            return ips

        for node_id in self.get(usedby_key)['node']:
            node_id = ObjectId(node_id)
            node = Node(id=node_id, group=self, mongo_db=self._mongo_db)
            for ifuuid in interfaces_with_net:
                hostname = node.name
                ifname = interfaces_with_net[ifuuid]

                # add *-ifname if we have more that one interface
                # with this net configured, for example:
                # node001-eth0, node001-bmc
                if len(interfaces_with_net) > 1:

                    suffix = "-" + ifname

                    if lowered:
                        suffix = suffix.lower()

                    hostname += suffix
                    self.log.warning(
                        ('Several interfaces for {} in network {} ' +
                         'are configured. ' +
                         'Using suffix: {}.')
                        .format(node.name, net.name, hostname)
                    )

                ipnum = node.get_ip(interface_name=ifname,
                                    format='num', version=ver)

                if hostname in ips:
                    self.log.error(("Duplicate IP detected in the group '{}'."
                                    "Could not process '{}'")
                                   .format(self.name, hostname))
                else:
                    ips[hostname] = ipnum

        return ips

    def get_macs(self, net):

        interfaces = self.get('interfaces')

        if not isinstance(net, Network):
            self.log.error("net should be Network class. Unable to preceed.")
            return False

        ver = net.version

        if not self.get(usedby_key) or not 'node' in self.get(usedby_key):
            self.log.warning(
                'No nodes are configured in provisioning network.')
            # No nodes in group. Returning empty list
            return {}

        # get all the interfaces with desired net configured in format:
        # {'uuid1': 'eth0', 'uuid2': 'BMC'}
        interfaces_with_net = {}
        for ifuuid in interfaces:
            interface = interfaces[ifuuid]
            if interface['network'][str(ver)] == net.DBRef:
                if interface['name'] == 'BMC':
                    self.log.info('Can\'t use BMC interface for provisioning.')
                    continue
                interfaces_with_net[ifuuid] = interface['name']

        if not interfaces_with_net:
            self.log.warning('No interfaces configured ' +
                             'in provisioning network')
            return {}

        if_uuids = interfaces_with_net.keys()
        if_name = None
        # First try to find BOOTIF
        for if_uuid in if_uuids:
            if interfaces_with_net[if_uuid] == 'BOOTIF':
                self.log.info('Group has BOOTIF configured ' +
                              'in provisioning network.')
                if_name = 'BOOTIF'
                break

        # Then try to find any (first) interface with desired net configured
        if not if_name:
            if len(interfaces_with_net.keys()) > 1:
                self.log.warning('Several interfaces configured in ' +
                                 'provisioning network. Taking arbitrary.')
                # just take the first one
            if_uuid = interfaces_with_net.keys()[0]
            if_name = interfaces_with_net[if_uuid]

        # Should never happen
        if not (if_uuid and if_name):
            self.log.error('Unable to find UUID for provisionining interface.')
            return {}

        reverse_links = self.get_back_links()

        nodes = {}

        for link in reverse_links:
            if link['collection'] == 'node':
                node_obj = Node(
                    id=link['DBRef'].id, group=self, mongo_db=self._mongo_db)

                ip = node_obj.get_ip(
                    interface_uuid=if_uuid, version=str(net.version))

                mac = node_obj.get_mac()

                if not (ip and mac):
                    continue

                tmp = {'ip': ip, 'mac': mac}
                nodes[node_obj.name] = tmp

        return nodes

    def set_net_to_if(self, interface_name, network_name):

        interfaces_dict = self.get('interfaces')
        if_list = self.list_ifs()

        if interface_name not in if_list.keys():
            self.log.error(
                "Interface '{}' does not exist".format(interface_name)
            )
            return False

        interface_uuid = if_list[interface_name]

        network_obj = Network(network_name, mongo_db=self._mongo_db)
        version = str(network_obj.version)

        if interfaces_dict[interface_uuid]['network'][version]:

            self.log.error(
                "Network IPv{} is already defined for interface '{}'"
                .format(version, interface_name)
            )

            return False

        interfaces_dict[interface_uuid]['network'][version] = network_obj.DBRef

        res = self.set('interfaces', interfaces_dict)

        if not res:
            self.log.error("Error adding network for interface '{}'"
                           .format(interface_name))
            return False

        self.link(network_obj)
        self._invalidate_network(network_obj.id)

        reverse_links = self.get_back_links()

        # Now we need to assign ip for every node in group
        nodes = {}
        for link in reverse_links:
            if link['collection'] == 'node':
                node_obj = Node(id=link['DBRef'].id, mongo_db=self._mongo_db)
                nodes[node_obj.name] = node_obj

        nodenames = nodes.keys()
        nodenames.sort()
        for nodename in nodenames:
                node_obj = nodes[nodename]
                node_obj.add_ip(interface_name)

        return True

    def del_net_from_if(self, interface_name, network_name=None):

        interfaces_dict = self.get('interfaces')
        if_list = self.list_ifs()

        if interface_name not in if_list.keys():
            self.log.error(
                "Interface '{}' does not exist".format(interface_name)
            )
            return False

        net = None
        if network_name:
            net = self._get_network(netname=network_name)

        interface_uuid = if_list[interface_name]

        # create temporary dict for storing configured networks
        nets_configured = {'4': None, '6': None}
        nets_configured['4'] = interfaces_dict[interface_uuid]['network']['4']
        nets_configured['6'] = interfaces_dict[interface_uuid]['network']['6']

        # if both IPv4 and IPv6 configured and no network_name specified
        if not net and nets_configured['4'] and nets_configured['6']:
            self.log.error(
                 ("Both IPv4 and IPv6 networks are configured for group. " +
                  "Need to specify network name.")
            )
            return False

        # if network_name is not the same as configured for interface
        if net and nets_configured[str(net.version)] != net.DBRef:
            self.log.error(
                "Network '{}' is not configured for interface '{}'"
                .format(network_name, interface_name))
            return False

        # now we can find IPv4 or IPv6 we will deal with
        if net:
            version = net.version
        else:
            version = '4'
            if nets_configured['6']:
                version = '6'
            net = self._get_network(netid=nets_configured[version].id)

        reverse_links = self.get_back_links()
        for link in reverse_links:
            if link['collection'] == 'node':
                node = Node(id=link['DBRef'].id, mongo_db=self._mongo_db)
                node.del_ip(interface_name, version)

        self.unlink(net.DBRef)
        self._invalidate_network(net)
        interfaces_dict[interface_uuid]['network'][str(version)] = None
        res = self.set('interfaces', interfaces_dict)
        if not res:
            self.log.error("Error deleting network for interface '{}'"
                           .format(interface_name))
            return False

        return True

    def del_interface(self, interface_name):
        interfaces = self.show_if(interface_name)

        if_list = self.list_ifs()

        if interface_name not in if_list.keys():
            self.log.error(
                "Interface '{}' does not exist".format(interface_name)
            )
            return False

        netnames = []

        for ver in ['4', '6']:
            netname = interfaces['network'][ver]['name']
            if netname:
                netnames.append(netname)

        for network_name in netnames:
            self.del_net_from_if(interface_name, network_name=network_name)

        reverse_links = self.get_back_links()
        for link in reverse_links:
            if link['collection'] == 'node':
                node_obj = Node(id=link['DBRef'].id, mongo_db=self._mongo_db)
                node_obj.del_interface(interface_name)

        interfaces_dict = self.get('interfaces')

        interface_uuid = if_list[interface_name]

        interfaces_dict.pop(interface_uuid)

        res = self.set('interfaces', interfaces_dict)
        if not res:
            self.log.error(
                "Error deleting interface '{}'".format(interface_name)
            )
            return False

        return True

    def manage_ip(self, interface_uuid=None,
                  ip=None, release=False, version=None):
        """
        operations with IP: add/delete
        """

        if version:
            version = str(version)

        if version and version not in ['4', '6']:
            self.log.error("Only IPv4 and IPv6 are supported")
            return False

        if interface_uuid not in self.get('interfaces'):
            self.log.error("Interface {} does not exixt"
                .format(interface_uuid))
            return False

        interface_name = self.get('interfaces')[interface_uuid]['name']

        net4_dbref = self.get('interfaces')[interface_uuid]['network']['4']
        net6_dbref = self.get('interfaces')[interface_uuid]['network']['6']

        if not version:
            if net4_dbref and net6_dbref:
                self.log.error(
                    ("Both IPv4 and IPv6 " +
                     "are configured for the interface {}. " +
                     "Version needs to be specified.")
                    .format(interface_name)
                )
                return False

        if not version and not net4_dbref and not net6_dbref:
            self.log.warning("Network is not configured for the interface {}."
                .format(interface_name))
            return False

        net_dbref = net4_dbref
        if not version:
            if net6_dbref:
                net_dbref = net6_dbref
        else:
            if int(version) == 6:
                net_dbref = net6_dbref

        if not net_dbref:

            self.log.warning(
                "Network IPv{} is not configured for the interface {}."
                .format(version, interface_name)
            )

            return False

        net_obj = Network(id=net_dbref.id, mongo_db=self._mongo_db)
        self._invalidate_network(net_obj)

        if release and ip:
            return net_obj.release_ip(ip)

        else:
            return net_obj.reserve_ip(ip)

    def get_ip(self, interface_uuid=None, ip=None, format='num', version='4'):
        """
        Convert from relative numbers to human-readable IPs and back
        """

        if version not in ['4', '6']:
            self.log.error("Only IPv4 and IPv6 are supported")
            return False

        if not interface_uuid:
            self.log.error("Interface should be specified")
            return None

        if not ip:
            self.log.error("IP should be specified")
            return None

        if (self.get('interfaces')
                and interface_uuid in self.get('interfaces')):

            net_dbref = (self.get('interfaces')[interface_uuid]
                                               ['network']
                                               [version])
        else:
            net_dbref = None

        if not net_dbref:
            interface_name = ''
            if interface_uuid:
                interface_name = self.get('interfaces')[interface_uuid]['name']
            self.log.warning("Network is not configured for {} interface"
                             .format(interface_name))
            return None

        net_obj = self._get_network(net_dbref.id)

        if ip and format is 'human':
            iphuman = utils.ip.reltoa(
                net_obj._json['NETWORK'], ip, net_obj.version
            )
            return iphuman

        elif ip and format is 'num':
            ipnum = utils.ip.atorel(
                ip, net_obj._json['NETWORK'], net_obj.get('PREFIX'),
                net_obj.version
            )
            return ipnum

        return None

    def set_domain(self, domain_name=None):

        newnet, oldnet = None, None
        newnet_dbref = None

        if domain_name:
            newnet = self._get_network(netname=domain_name)
            newnet_dbref = newnet.DBRef

        if 'domain' in self._json and self._json['domain']:
            oldnet = self._get_network(self._json['domain'].id)

        if oldnet:
            self.unlink(oldnet)
            self._invalidate_network(oldnet.id)

        if newnet:
            self.link(newnet)
            self._invalidate_network(newnet.id)

        self.set('domain', newnet_dbref)

        return True

    def release_resources(self):
        self.set_domain(domain_name=None)

    def list_nodes(self):
        reverse_links = self.get_back_links()
        interfaces = self.list_ifs().keys()
        nodes = {}
        cursor = self._mongo_db['mac'].find()
        macs = {}
        for elem in cursor:
            macs[elem['node'].id] = str(elem['mac'])
        for link in reverse_links:
            if link['collection'] == 'node':
                node = Node(
                    id=link['DBRef'].id,
                    mongo_db=self._mongo_db,
                    group=self
                )
                nodes[node.name] = {}
                if node.id in macs:
                    nodes[node.name]['mac'] = macs[node.id]
                else:
                    nodes[node.name]['mac'] = None
                tmp = {}
                for interface in interfaces:
                    tmp[interface] = {}
                    for ver in [4, 6]:
                        ip = node.get_ip(interface, version=ver, quiet=True)
                        tmp[interface][ver] = ip
                nodes[node.name]['interfaces'] = tmp
        return nodes

    def _get_network(self, netid=None, netname=None):
        if not (netid or netname):
            self.log.error('netid or netname should be specified')
            return False
        if netid and netid in self._networks:
            return self._networks[netid]['object']
        if netname:
            for elem in self._networks:
                if self._networks[elem]['name'] == netname:
                    return self._networks[elem]['object']
        netobj = Network(name=netname, id=netid, mongo_db=self._mongo_db)
        tmp = {'name': netobj.name, 'object': netobj}
        self._networks[netid] = tmp

        return self._networks[netid]['object']

    def _invalidate_network(self, netid):
        if netid in self._networks:
            self._networks.pop(netid)
            return True
        return False

    def clone(self, name):

        osimage_dbref = self.get('osimage')
        osimage = OsImage(id=osimage_dbref.id, mongo_db=self._mongo_db)
        bmcsetup_name = None
        bmcsetup_dbref = self.get('bmcsetup')

        if bmcsetup_dbref:
            bmcsetup = BMCSetup(id=bmcsetup_dbref.id, mongo_db=self._mongo_db)
            bmcsetup_name = bmcsetup.name

        pre = self.get('prescript')
        post = self.get('postscript')
        part = self.get('partscript')

        comment = self.get('comment')

        if_list = self.list_ifs().keys()

        domain_dbref = self.get('domain')
        domain_name = None
        if domain_dbref:
            domain_net = Network(id=domain_dbref.id, mongo_db=self._mongo_db)
            domain_name = domain_net.name

        torrent_if = self.get('torrent_if')

        if not torrent_if:
            torrent_if = None

        group = Group(
            name=name,
            create=True,
            bmcsetup=bmcsetup_name,
            osimage=osimage.name,
            interfaces=if_list,
            prescript=pre,
            partscript=part,
            postscript=post,
            torrent_if=torrent_if,
            domain=domain_name,
            mongo_db=self._mongo_db,
        )
        group.set('comment', comment)

        for if_name in if_list:
            if_dict = self.show_if(if_name)
            for ver in ['4', '6']:
                if not if_dict['network'][ver]['name']:
                    continue
                group.set_net_to_if(if_name, if_dict['network'][ver]['name'])

        return group


from luna.node import Node
