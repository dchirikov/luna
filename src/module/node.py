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

from config import *
import logging
import json
from bson.dbref import DBRef
from bson.objectid import ObjectId
from luna.utils import set_mac_node
from luna.base import Base
from luna.cluster import Cluster
from luna.network import Network
from luna.osimage import OsImage
from luna.bmcsetup import BMCSetup
from luna.switch import Switch

class Node(Base):
    """
    Class for operating with node records
    """
    _logger = logging.getLogger(__name__)
    def __init__(self, name = None, mongo_db = None, create = False, id = None,
            group = None, localboot = False, setupbmc = True, service = False):
        """
        name    - can be ommited
        group   - group belongs to; should be specified
            Flags
        localboot - boot from localdisk
        setupbmc - whether we need to setup ipmi on install
        service   - do not perform install but boot to installer (dracut environment)
        """
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        self._collection_name = 'node'
        if not bool(name) and bool(create):
            name = self._generate_name(mongo_db = mongo_db)
        mongo_doc = self._check_name(name, mongo_db, create, id)
        self._keylist = {'port': type(''), 'localboot': type(True), 'setupbmc': type(True), 'service': type(True)}
        if create:
            cluster = Cluster(mongo_db = self._mongo_db)
            group = Group(group, mongo_db = self._mongo_db)
            mongo_doc = {'name': name, 'group': group.DBRef, 'interfaces': None,
                    'mac': None, 'switch': None, 'port': None,
                    'localboot': localboot, 'setupbmc': setupbmc, 'service': service}
            self._logger.debug("mongo_doc: '{}'".format(mongo_doc))
            self._name = name
            self._id = self._mongo_collection.insert(mongo_doc)
            self._DBRef = DBRef(self._collection_name, self._id)
            for interface in group._get_json()['interfaces']:
                self.add_ip(interface)
            self.add_bmc_ip()
            self.link(group)
            self.link(cluster)
        else:
            self._name = mongo_doc['name']
            self._id = mongo_doc['_id']
            self._DBRef = DBRef(self._collection_name, self._id)
        self._logger = logging.getLogger(__name__ + '.' + self._name)

    def _generate_name(self, mongo_db):
        cluster = Cluster(mongo_db)
        prefix = cluster.get('nodeprefix')
        digits = cluster.get('nodedigits')
        back_links = cluster.get_back_links()
        max_num = 0
        for link in back_links:
            if not link['collection'] == self._collection_name:
                continue
            node = Node(id = link['DBRef'].id, mongo_db = mongo_db)
            name = node.name
            nnode = int(name.lstrip(prefix))
            if nnode > max_num:
                max_num = nnode
        ret_name = prefix + str(max_num + 1).zfill(digits)
        return ret_name

    def change_group(self, new_group_name = None):
        if not bool(new_group_name):
            self._logger.error("Group needs to be specified")
            return None
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        new_group = Group(new_group_name, mongo_db = self._mongo_db)
        json = self._get_json()
        old_group = Group(id = json['group'].id, mongo_db = self._mongo_db)
        old_group_interfaces = old_group._get_json()['interfaces']
        for interface in old_group_interfaces:
            self.del_ip(interface)
        self.del_bmc_ip()
        self.unlink(old_group)
        res = self._mongo_collection.update({'_id': self._id}, {'$set': {'group': new_group.DBRef}}, multi=False, upsert=False)
        self.link(new_group)
        self.add_bmc_ip()
        new_group_interfaces = new_group._get_json()['interfaces']
        for interface in new_group_interfaces:
            self.add_ip(interface)
        return res['err']

    def change_ip(self, interface = None, reqip = None):
        if not bool(interface):
            self._logger.error("'interfaces' should be specified")
            return None
        if not bool(reqip):
            self._logger.error("IP address should be specified")
            return None
        self_group_name = self._get_json()['group']
        group = Group(id = self_group_name.id, mongo_db = self._mongo_db)
        if not bool(group.get_num_ip(interface, reqip)):
            return None
        if self.del_ip(interface):
            return self.add_ip(interface, reqip)
        return None

    def change_bmc_ip(self, reqip = None):
        if not bool(reqip):
            self._logger.error("IP address should be specified")
            return None
        self_group_name = self._get_json()['group']
        group = Group(id = self_group_name.id, mongo_db = self._mongo_db)
        if not bool(group.get_num_bmc_ip(reqip)):
            return None
        if self.del_bmc_ip():
            return self.add_bmc_ip(reqip)
        return None

    def add_ip(self, interface = None, reqip = None):
        if not bool(interface):
            self._logger.error("'interface' should be specified")
            return None
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        json = self._get_json()
        group = Group(id = json['group'].id, mongo_db = self._mongo_db)
        group_interfaces = group._get_json()['interfaces']
        try:
            node_interfaces = json['interfaces']
        except:
            node_interfaces = None
        try:
            group_interfaces[interface]
        except:
            self._logger.error("No such interface '{}' for group configured.".format(interface))
            return None
        try:
            old_ip = node_interfaces[interface]
        except:
            old_ip = None
        if bool(old_ip):
            self._logger.error("IP is already configured for interface '{}'.".format(interface))
            return None
        if not bool(node_interfaces):
            node_interfaces = {}
        ip = group._reserve_ip(interface, reqip)
        if not bool(ip):
            self._logger.error("Cannot reserve ip for interface '{}'.".format(interface))
        node_interfaces[interface] = ip
        res = self._mongo_collection.update({'_id': self._id}, {'$set': {'interfaces': node_interfaces}}, multi=False, upsert=False)
        return not 'err' in res

    def del_ip(self, interface = None):
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        json = self._get_json()
        group = Group(id = json['group'].id, mongo_db = self._mongo_db)
        try:
            mongo_doc = json['interfaces'].copy()
        except:
            self._logger.error("No interfaces found")
            return None
        if not bool(mongo_doc):
            self._logger.error("All interfaces are already deleted")
            return None
        if not bool(interface):
            for iface in json['interfaces']:
                ip = json['interfaces'][iface]
                group._release_ip(iface, ip)
                mongo_doc.pop(iface)
            res = self._mongo_collection.update({'_id': self._id}, {'$set': {'interfaces': mongo_doc}}, multi=False, upsert=False)
            return not 'err' in res
        try:
            ip = json['interfaces'][interface]
        except:
            self._logger.error("No such interface '{}' found. If it already deleted?".format(interface))
            return True
        group._release_ip(interface, ip)
        mongo_doc.pop(interface)
        res = self._mongo_collection.update({'_id': self._id}, {'$set': {'interfaces': mongo_doc}}, multi=False, upsert=False)
        return not 'err' in res

    def add_bmc_ip(self, reqip = None):
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        json = self._get_json()
        group = Group(id = json['group'].id, mongo_db = self._mongo_db)
        ip = 0
        try:
            ip = json['bmcnetwork']
        except:
            pass
        if bool(ip):
            self._logger.error("IP is already assigned on bmc network")
            return None
        ip = group._reserve_bmc_ip(reqip)
        if not bool(ip):
            self._logger.error("Cannot reserve ip for bmc interface")
            return None
        mongo_doc = ip
        res = self._mongo_collection.update({'_id': self._id}, {'$set': {'bmcnetwork': mongo_doc}}, multi=False, upsert=False)
        return not 'err' in res

    def del_bmc_ip(self):
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        json = self._get_json()
        group = Group(id = json['group'].id, mongo_db = self._mongo_db)
        try:
            ip = json['bmcnetwork']
        except:
            self._logger.error("No IP configured on bmc network")
            return None
        res = group._release_bmc_ip(ip)
        if bool(res):
            mongo_doc = None
        res = self._mongo_collection.update({'_id': self._id}, {'$set': {'bmcnetwork': mongo_doc}}, multi=False, upsert=False)
        return not 'err' in res

    def set_mac(self, mac = None):
        import re
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        if type(mac) == type('') and re.match('(([a-fA-F0-9]{2}:){4}([a-fA-F0-9]{2}))', mac):
            mac = mac.lower()
            set_mac_node(mac, self.DBRef, (self._mongo_db))
            #res = self._mongo_collection.update({'_id': self._id}, {'$set': {'mac': mac}}, multi=False, upsert=False)
            return True
        return None

    def get_mac(self):
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        try:
            mac = str(self._mongo_db['mac'].find_one({'node': self.DBRef})['mac'])
        except:
            mac = None
        return mac
 
    def clear_mac(self):
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        mac = self.get_mac()
        self._mongo_db['switch_mac'].remove({'mac': mac})
        res = self._mongo_db['mac'].remove({'mac': mac})
        return res['ok']

    def set_switch(self, name):
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        switch = Switch(name)
        res = self._mongo_collection.update({'_id': self._id}, {'$set': {'switch': switch.DBRef}}, multi=False, upsert=False)
        if res['ok'] == 1:
            self.link(switch.DBRef)
        return bool(res['ok'])

    def clear_switch(self):
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        json = self._get_json()
        try:
            switch_id = json['switch'].id
        except:
            return None
        switch = Switch(id = switch_id)
        res = self._mongo_collection.update({'_id': self._id}, {'$set': {'switch': None}}, multi=False, upsert=False)
        if res['ok'] == 1:
            self.unlink(switch.DBRef)
        return bool(res['ok'])
 
    def set_port(self, num):
        self.set('port', num)

    def clear_port(self):
        self.set('port', '')

    def delete(self):
        """
        Delete node
        """
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        mac = self.get_mac()
        back_links = self.get_back_links(resolve=True)
        if len(back_links) > 0:
            #back_links = self.get_back_links(resolve=True)
            self._logger.error("Current object is being written as a dependency for the following objects:")
            for elem in back_links:
                self._logger.error(json.dumps(elem, sort_keys=True ))
            return None
        links = self.get_links(resolve=True)
        for link in links:
            self.unlink(link['DBRef'])
        self._mongo_db['switch_mac'].remove({'mac': mac})
        self._mongo_db['mac'].remove({'mac': mac})
        self.del_bmc_ip()
        self.del_ip()
        ret = self._mongo_collection.remove({'_id': self._id}, multi=False)
        self._wipe_vars()
        return not 'err' in ret

    def get_interfaces(self):
        try:
            return self._get_json()['interfaces'].keys()
        except:
            return {}

    def get_human_ip(self, interface):
        json = self._get_json()
        group = Group(id = json['group'].id, mongo_db = self._mongo_db)
        try:
            ipnum = json['interfaces'][interface]
        except:
            # self._logger.error("No IPADDR for interface '{}' configured".format(interface)) 
            return None
        return group.get_human_ip(interface, ipnum)

    def get_rel_ip(self, interface):
        json = self._get_json()
        #group = Group(id = json['group'].id, mongo_db = self._mongo_db)
        try:
            num_ip = json['interfaces'][interface]
        except:
            self._logger.error("No such interface '{}' for node '{}' configured".format(interface, self.name)) 
            return None
        return num_ip

    def get_human_bmc_ip(self):
        json = self._get_json()
        group = Group(id = json['group'].id, mongo_db = self._mongo_db)
        try:
            ipnum = json['bmcnetwork']
        except:
            self._logger.error("No IPADDR for interface bmc configured")
            return None
        return group.get_human_bmc_ip(ipnum)

    def get_rel_bmc_ip(self):
        json = self._get_json()
        #group = Group(id = json['group'].id, mongo_db = self._mongo_db)
        try:
            num_ip = json['bmcnetwork']
        except:
            self._logger.error("No BMC interface for node '{}' configured".format(self.name))
            return None
        return num_ip

    """
    @property
    def kernel(self):
        return "compute-vmlinuz-3.10.0-327.3.1.el7.x86_64"

    @property
    def initrd(self):
        return "compute-initramfs-3.10.0-327.3.1.el7.x86_64"

    @property
    def kernopts(self):
        return 'luna.ip=enp0s3:10.141.0.1:16' # luna.ip=dhcp
    """

    @property
    def boot_params(self):
        """
        will return dictionary with all needed params for booting:
        kernel, initrd, kernel opts, ip, net, prefix
        """
        params = {}
        group = Group(id = self.get('group').id, mongo_db = self._mongo_db)
        group_params = group.boot_params()
        params['boot_if'] = group_params['boot_if']
        params['kernel_file'] = group_params['kernel_file']
        params['initrd_file'] = group_params['initrd_file']
        params['kern_opts'] = group_params['kern_opts']
        params['boot_if'] = group_params['boot_if']
        params['net_prefix'] = group_params['net_prefix']
        if (params['boot_if']):
            params['ip'] = self.get_human_ip(params['boot_if'])
        params['name'] = self.name
        params['service'] = int(self.get('service'))
        params['localboot'] = self.get('localboot')
        return params

    @property
    def install_params(self):
        params = {}
        group = Group(id = self.get('group').id, mongo_db = self._mongo_db)
        params = group.install_params
        if bool(params['torrent_if']):
            params['torrent_if_ip'] = self.get_human_ip(params['torrent_if'])
        for interface in params['interfaces']:
            params['interfaces'][interface] = params['interfaces'][interface].strip() + "\n" + "IPADDR=" + self.get_human_ip(interface)
        if params['bmcsetup']:
            try:
                ip = self.get_human_bmc_ip()
                params['bmcsetup']['ip'] = ip
            except:
                pass
        params['name'] = self.name
        if params['domain']:
            params['hostname'] = self.name + "." +  params['domain']
        else:
            params['hostname'] = self.name
        params['setupbmc'] = self.get('setupbmc')
        return params

class Group(Base):
    """
    Class for operating with group records
    """
    _logger = logging.getLogger(__name__)
    def __init__(self, name = None, mongo_db = None, create = False, id = None,
            prescript = None, bmcsetup = None, bmcnetwork = None,
            partscript = None, osimage = None, interfaces = None, postscript = None, boot_if = None, torrent_if = None):
        """
        prescript   - preinstall script
        bmcsetup    - bmcsetup options
        bmcnetwork  - used for bmc networking
        partscript  - parition script
        osimage     - osimage
        interfaces  - list of the newtork interfaces
        postscript  - postinstall script
        """
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        self._collection_name = 'group'
        mongo_doc = self._check_name(name, mongo_db, create, id)
        self._keylist = {'prescript': type(''), 'partscript': type(''), 'postscript': type(''), 'boot_if': type(''), 'torrent_if': type('')}
        if create:
            cluster = Cluster(mongo_db = self._mongo_db)
            (bmcobj, bmcnetobj) = (None, None)
            if bool(bmcsetup):
                bmcobj = BMCSetup(bmcsetup).DBRef
            if bool(bmcnetwork):
                bmcnetobj = Network(bmcnetwork, mongo_db = self._mongo_db).DBRef
            osimageobj = OsImage(osimage)
            if bool(interfaces) and type(interfaces) is not type([]):
                self._logger.error("'interfaces' should be list")
                raise RuntimeError
            if_dict = {}
            if not bool(interfaces):
                interfaces = []
            for interface in interfaces:
                if_dict[interface] = {'network': None, 'params': ''}
            if not bool(partscript):
                partscript = "mount -t ramfs ramfs /sysroot"
            if not bool(prescript):
                prescript = ""
            if not bool(postscript):
                postscript = ""
            mongo_doc = {'name': name, 'prescript':  prescript, 'bmcsetup': bmcobj, 'bmcnetwork': bmcnetobj,
                               'partscript': partscript, 'osimage': osimageobj.DBRef, 'interfaces': if_dict,
                               'postscript': postscript, 'boot_if': boot_if, 'torrent_if': torrent_if}
            self._logger.debug("mongo_doc: '{}'".format(mongo_doc))
            self._name = name
            self._id = self._mongo_collection.insert(mongo_doc)
            self._DBRef = DBRef(self._collection_name, self._id)
            self.link(cluster)
            if bmcobj:
                self.link(bmcobj)
            if bmcnetobj:
                self.link(bmcnetobj)
            self.link(osimageobj)
        else:
            self._name = mongo_doc['name']
            self._id = mongo_doc['_id']
            self._DBRef = DBRef(self._collection_name, self._id)
        self._logger = logging.getLogger('group.' + self._name)
 
    def osimage(self, osimage_name):
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        osimage = OsImage(osimage_name)
        old_dbref = self._get_json()['osimage']
        self.unlink(old_dbref)
        res = self._mongo_collection.update({'_id': self._id}, {'$set': {'osimage': osimage.DBRef}}, multi=False, upsert=False)
        self.link(osimage.DBRef)
        return not 'err' in res

    def bmcsetup(self, bmcsetup_name):
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        bmcsetup = None
        if bool(bmcsetup_name):
            bmcsetup = BMCSetup(bmcsetup_name)
        old_dbref = self._get_json()['bmcsetup']
        if bool(old_dbref):
            self.unlink(old_dbref)
        if bool(bmcsetup):
            res = self._mongo_collection.update({'_id': self._id}, {'$set': {'bmcsetup': bmcsetup.DBRef}}, multi=False, upsert=False)
            self.link(bmcsetup.DBRef)
        else:
            res = self._mongo_collection.update({'_id': self._id}, {'$set': {'bmcsetup': None}}, multi=False, upsert=False)
        return not 'err' in res

    def set_bmcnetwork(self, bmcnet):
        old_bmcnet_dbref = self._get_json()['bmcnetwork']
        net = Network(bmcnet, mongo_db = self._mongo_db)
        reverse_links = self.get_back_links()
        if bool(old_bmcnet_dbref):
            self._logger.error("Network is already defined for BMC interface")
            return None
        res = self._mongo_collection.update({'_id': self._id}, {'$set': {'bmcnetwork': net.DBRef}}, multi=False, upsert=False)
        self.link(net.DBRef)
        for link in reverse_links:
            if link['collection'] != 'node':
                continue
            node = Node(id=link['DBRef'].id, mongo_db = self._mongo_db)
            node.add_bmc_ip()
        return not 'err' in res

    def del_bmcnetwork(self):
        old_bmcnet_dbref = self._get_json()['bmcnetwork']
        if bool(old_bmcnet_dbref):
            reverse_links = self.get_back_links()
            for link in reverse_links:
                if link['collection'] != 'node':
                    continue
                node = Node(id=link['DBRef'].id, mongo_db = self._mongo_db)
                node.del_bmc_ip()
            self.unlink(old_bmcnet_dbref)
        res = self._mongo_collection.update({'_id': self._id}, {'$set': {'bmcnetwork': None}}, multi=False, upsert=False)
        return not 'err' in res

    
    def show_bmc_if(self, brief = False):
        bmcnetwork = self._get_json()['bmcnetwork']
        if not bool(bmcnetwork):
            return ''
        (NETWORK, PREFIX) = ("", "")
        try:
            net = Network(id = bmcnetwork.id, mongo_db = self._mongo_db)
            NETWORK = net.get('NETWORK')
            PREFIX =  str(net.get('PREFIX'))
        except:
            pass
        if brief:
            return "[" +net.name + "]:"+ NETWORK + "/" + PREFIX
        return NETWORK + "/" + PREFIX



    def show_if(self, interface, brief = False):
        interfaces = self._get_json()['interfaces']
        try:
            params = interfaces[interface]
        except:
            self._logger.error("Interface '{}' does not exist".format(interface))
            return ""
        (outstr, NETWORK, PREFIX) = ("", "", "")
        try:
            net = Network(id = params['network'].id, mongo_db = self._mongo_db)
            NETWORK = net.get('NETWORK')
            PREFIX =  str(net.get('PREFIX'))
        except:
            pass
        if NETWORK:
            if brief:
                return "[" +net.name + "]:" + NETWORK + "/" + PREFIX
            outstr = "NETWORK=" + NETWORK + "\n"
            outstr += "PREFIX=" + PREFIX
        if params['params'] and not brief:
            outstr += "\n" + params['params']
        return outstr.rstrip()

    def add_interface(self, interface):
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        interfaces = self._get_json()['interfaces']
        old_parms = None
        try:
            old_parms = interfaces[interface]
        except:
            pass
        if bool(old_parms):
            self._logger.error("Interface already exists")
            return None
        interfaces[interface] = {'network': None, 'params': ''}
        res = self._mongo_collection.update({'_id': self._id}, {'$set': {'interfaces': interfaces}}, multi=False, upsert=False)
        if 'err' in res:
            self._logger.error("Error adding interface '{}'".format(interface))
            return None
        return True

    def get_if_parms(self, interface):
        interfaces = self._get_json()['interfaces']
        try:
            interfaces[interface]
        except:
            self._logger.error("Interface '{}' does not exist".format(interface))
            return None
        return interfaces[interface]['params']

    def list_interfaces(self):
        json = self._get_json()
        try:
            interfaces = json['interfaces']
        except:
            self._logger.error("No interfaces for group '{}' configured.".format(self.name))
            interfaces = {}
        try:
            bmcnet = json['bmcnetwork']
        except:
            self._logger.error("No network for BMC interface for group '{}' configured.".format(self.name))
            bmcnet = None
        return {'interfaces': interfaces, 'bmcnetwork': bmcnet}

    def get_rel_ips_for_net(self, netobjid):
        rel_ips = {}

        def add_to_dict(key, val):
            try:
                rel_ips[key]
                self._logger.error("Duplicate ip detected in '{}'. Can not put '{}'".format(self.name, key))
            except:
                rel_ips[key] = val
                
        json = self._get_json()
        if_dict = self.list_interfaces()
        bmcif =  if_dict['bmcnetwork']
        ifs = if_dict['interfaces']
        if bool(bmcif):
            if bmcif.id == netobjid:
                try:
                    node_links = json[usedby_key]
                except KeyError:
                    node_links = None
                for node_id in node_links['node']:
                    node = Node(id = ObjectId(node_id))
                    add_to_dict(node.name, node.get_rel_bmc_ip())

        if bool(if_dict):
            for interface in ifs:
                if ifs[interface]['network'].id == netobjid:
                    try:
                        node_links = json[usedby_key]
                    except KeyError:
                        node_links = None
                    for node_id in node_links['node']:
                        node = Node(id = ObjectId(node_id))
                        add_to_dict(node.name, node.get_rel_ip(interface))
        return rel_ips
                        

    def set_if_parms(self, interface, parms = ''):
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        interfaces = self._get_json()['interfaces']
        try:
            interfaces[interface]
        except:
            self._logger.error("Interface '{}' does not exist".format(interface))
            return None
        interfaces[interface]['params'] = parms
        res = self._mongo_collection.update({'_id': self._id}, {'$set': {'interfaces': interfaces}}, multi=False, upsert=False)
        if 'err' in res:
            self._logger.error("Error setting network parameters for interface '{}'".format(interface))
            return None
        return True

    def set_net_to_if(self, interface, network):
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        interfaces = self._get_json()['interfaces']
        net = Network(network, mongo_db = self._mongo_db)
        try:
            old_parms = interfaces[interface]
        except:
            old_parms = None
            self._logger.error("Interface '{}' does not exist".format(interface))
            return None
        try:
            old_net = old_parms['network']
        except:
            old_net = None
        if bool(old_net):
            self._logger.error("Network is already defined for this interface '{}'".format(interface))
            return None
        interfaces[interface]['network'] = net.DBRef
        res = self._mongo_collection.update({'_id': self._id}, {'$set': {'interfaces': interfaces}}, multi=False, upsert=False)
        if 'err' in res:
            self._logger.error("Error adding network for interface '{}'".format(interface))
            return None
        self.link(net.DBRef)
        reverse_links = self.get_back_links()
        for link in reverse_links:
            if link['collection'] != 'node':
                continue
            node = Node(id=link['DBRef'].id, mongo_db = self._mongo_db)
            node.add_ip(interface)
        return True

    def del_net_from_if(self, interface):
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        interfaces = self._get_json()['interfaces']
        try:
            old_parms = interfaces[interface]
        except:
            old_parms = None
            self._logger.error("Interface '{}' does not exist".format(interface))
            return None
        try:
            net_dbref = old_parms['network']
        except:
            net_dbref = None
            self._logger.error("Network is not configured for interface '{}'".format(interface))
            return None
        if not bool(net_dbref):
            self._logger.error("Network is not configured for interface '{}'".format(interface))
            return None
        reverse_links = self.get_back_links()
        for link in reverse_links:
            if link['collection'] != 'node':
                continue
            node = Node(id=link['DBRef'].id, mongo_db = self._mongo_db)
            node.del_ip(interface)
        self.unlink(net_dbref)
        interfaces[interface]['network'] = None
        res = self._mongo_collection.update({'_id': self._id}, {'$set': {'interfaces': interfaces}}, multi=False, upsert=False)
        if 'err' in res:
            self._logger.error("Error adding network for interface '{}'".format(interface))
            return None
        return True

    def del_interface(self, interface):
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        self.del_net_from_if(interface)
        interfaces = self._get_json()['interfaces']
        interfaces.pop(interface)
        res = self._mongo_collection.update({'_id': self._id}, {'$set': {'interfaces': interfaces}}, multi=False, upsert=False)
        if 'err' in res:
            self._logger.error("Error deleting interface '{}'".format(interface))
            return None
        return True

    def _reserve_ip(self, interface = None, ip = None):
        if not bool(interface):
            self._logger.error("Interface needs to be specified")
            return None
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        try:
            net_dbref = self._get_json()['interfaces'][interface]['network']
        except:
            self._logger.error("No such interface '{}'".format(interface))
            return None
        if not bool(net_dbref):
            self._logger.error("No network configured for interface '{}'".format(interface))
            return None
        net = Network(id = net_dbref.id, mongo_db = self._mongo_db)
        return net.reserve_ip(ip)

    def _release_ip(self, interface, ip):
        if not bool(interface):
            self._logger.error("Interface needs to be specified")
            return None
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        try:
            net_dbref = self._get_json()['interfaces'][interface]['network']
        except:
            self._logger.error("No such interface '{}'".format(interface))
            return None
        net = Network(id = net_dbref.id, mongo_db = self._mongo_db)
        return net.release_ip(ip)

    def _reserve_bmc_ip(self, ip = None):
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        try:
            net_dbref = self._get_json()['bmcnetwork']
        except:
            self._logger.error("No bmc network configured")
            return None
        if not bool(net_dbref):
            self._logger.error("No network configured for BMC interface")
            return None
        net = Network(id = net_dbref.id, mongo_db = self._mongo_db)
        return net.reserve_ip(ip)

    def _release_bmc_ip(self, ip):
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        try:
            net_dbref = self._get_json()['bmcnetwork']
        except:
            self._logger.error("No bmc network configured")
            return None
        net = Network(id = net_dbref.id, mongo_db = self._mongo_db)
        return net.release_ip(ip)

    def get_human_ip(self, interface, ipnum):
        interfaces = self._get_json()['interfaces']
        dbref = None
        try:
            dbref = interfaces[interface]['network']
        except:
            self._logger.error("Interface is not configured for '{}'".format(interface))
            return None
        if not bool(dbref):
            return None
        net = Network(id = dbref.id, mongo_db = self._mongo_db)
        return net.relnum_to_ip(ipnum)

    def get_num_ip(self, interface, ip):
        interfaces = self._get_json()['interfaces']
        dbref = None
        try:
            dbref = interfaces[interface]['network']
        except:
            self._logger.error("Interface is not configured for '{}'".format(interface))
            return None
        if not bool(dbref):
            return None
        net = Network(id = dbref.id, mongo_db = self._mongo_db)
        return net.ip_to_relnum(ip)

    def get_human_bmc_ip(self, ipnum):
        dbref = None
        try:
            dbref = self._get_json()['bmcnetwork']
        except:
            self._logger.error("Interface is not configured for BMC")
            return None
        if not bool(dbref):
            return None
        net = Network(id = dbref.id, mongo_db = self._mongo_db)
        return net.relnum_to_ip(ipnum)

    def get_num_bmc_ip(self, ip):
        dbref = None
        try:
            dbref = self._get_json()['bmcnetwork']
        except:
            self._logger.error("Interface is not configured for BMC")
            return None
        if not bool(dbref):
            return None
        net = Network(id = dbref.id, mongo_db = self._mongo_db)
        return net.ip_to_relnum(ip)

    def boot_params(self):
        params = {}
        params['boot_if'] = None
        params['net_prefix'] = None
        osimage = OsImage(id = self.get('osimage').id, mongo_db = self._mongo_db)
        try:
            params['kernel_file'] = osimage.get('kernfile')
        except:
            params['kernel_file'] = ""
        try:
            params['initrd_file'] = osimage.get('initrdfile')
        except:
            params['initrd_file'] = ""
        try:
            params['kern_opts'] = osimage.get('kernopts')
        except:
            params['kern_opts'] = ""
        try:
            params['boot_if'] = self.get('boot_if')
        except:
            params['boot_if'] = ""
            params['net_prefix'] = ""
            return params
        interfaces = self._get_json()['interfaces']
        try:
            if_params = interfaces[params['boot_if']]
        except:
            self._logger.error("Boot interface '{}' does not present in configured interface list '{}'.".format(params['boot_if'], interfaces.keys()))
            params['boot_if'] = ""
            params['net_prefix'] = ""
            return params
        net = None
        try:
            if_net = if_params['network']
            net = Network(id = if_net.id, mongo_db = self._mongo_db)
        except:
            pass
        if not bool(net):
            self._logger.error("Boot interface '{}' has no network configured".format(params['boot_if']))
            params['boot_if'] = ""
            params['net_prefix'] = ""
            return params
        params['net_prefix'] = net.get('PREFIX')
        return params

    @property
    def install_params(self):
        params = {}
        params['prescript'] = self.get('prescript')
        params['partscript'] = self.get('partscript')
        params['postscript'] = self.get('postscript')
        try:
            params['boot_if'] = self.get('boot_if')
        except:
            params['boot_if'] = ''
        try:
            params['torrent_if'] = self.get('torrent_if')
        except:
            params['torrent_if'] = ''
        json = self._get_json()
        if bool(params['torrent_if']):
            try:
                net_dbref = json['interfaces'][params['torrent_if']]['network']
                net = Network(id = net_dbref.id, mongo_db = self._mongo_db)
                params['torrent_if_net_prefix'] = str(net.get('PREFIX'))
            except:
                params['torrent_if'] = ''
        try:
            net_dbref = json['interfaces'][self.get('boot_if')]['network']
            net = Network(id = net_dbref.id, mongo_db = self._mongo_db)
            params['domain'] = str(net.name)
        except:
            params['domain'] = ""
        params['interfaces'] = {}
        try:
            interfaces = json['interfaces'].keys()
            for interface in interfaces:
                params['interfaces'][str(interface)] = str(self.get_if_parms(interface))
        except:
            pass
        try:
            interfaces = json['interfaces'].keys()
            for interface in interfaces:
                net_dbref = json['interfaces'][interface]['network']
                net = Network(id = net_dbref.id, mongo_db = self._mongo_db)
                params['interfaces'][str(interface)] = params['interfaces'][str(interface)].strip() + "\n" + "PREFIX=" + str(net.get('PREFIX'))
        except:
            pass
        osimage = OsImage(id = self.get('osimage').id, mongo_db = self._mongo_db)
        try:
            params['torrent'] = osimage.get('torrent') + ".torrent"
            params['tarball'] = osimage.get('tarball') + ".tgz"
        except:
            params['torrent'] = ""
            params['tarball'] = ""
        params['kernver'] = osimage.get('kernver')
        params['kernopts'] = osimage.get('kernopts')
        params['bmcsetup'] = {}
        if self.get('bmcsetup'):
            bmcsetup = BMCSetup(id = self.get('bmcsetup').id, mongo_db = self._mongo_db)
            params['bmcsetup']['mgmtchannel'] = bmcsetup.get('mgmtchannel') or 1
            params['bmcsetup']['netchannel'] = bmcsetup.get('netchannel') or 1
            params['bmcsetup']['userid'] = bmcsetup.get('userid') or 3
            params['bmcsetup']['user'] = bmcsetup.get('user') or "ladmin"
            params['bmcsetup']['password'] = bmcsetup.get('password') or "ladmin"
            try:
                net_dbref = json['bmcnetwork']
                net = Network(id = net_dbref.id, mongo_db = self._mongo_db)
                params['bmcsetup']['netmask'] = net.get('NETMASK')
            except:
                params['bmcsetup']['netmask'] = ''
        return params
