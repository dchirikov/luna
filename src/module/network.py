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
import struct
import socket
from bson.dbref import DBRef
from luna.base import Base
from luna.cluster import Cluster

class Network(Base):
    """
    Class for operating with ifcfg records

    """
    _logger = logging.getLogger(__name__)
    def __init__(self, name = None, mongo_db = None, create = False, id = None, NETWORK = None, PREFIX = None, ns_hostname = None, ns_ip = None):
        """
        create  - should be True if we need create osimage
        NETWORK - network
        PREFIX  - should be specified network bits or
        """
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        self._collection_name = 'network'
        self._keylist = {'NETWORK': long, 'PREFIX': type(0), 'ns_hostname': type(''), 'ns_ip': type('')}
        mongo_doc = self._check_name(name, mongo_db, create, id)
        if create:
            cluster = Cluster(mongo_db = self._mongo_db)
            num_net = self.get_base_net(NETWORK, PREFIX)
            if not num_net:
                self._logger.error("Cannot compute NETWORK/PREFIX")
                raise RuntimeError
            if not ns_hostname:
                ns_hostname = self._guess_ns_hostname()
            freelist = [{'start': 1, 'end': (1<<(32-PREFIX))-2}]
            mongo_doc = {'name': name, 'NETWORK': num_net, 'PREFIX': PREFIX, 'freelist': freelist, 'ns_hostname': ns_hostname, 'ns_ip': None}
            self._logger.debug("mongo_doc: '{}'".format(mongo_doc))
            self._name = name
            self._id = self._mongo_collection.insert(mongo_doc)
            self._DBRef = DBRef(self._collection_name, self._id)
            self.link(cluster)
            if not ns_ip:
                ns_ip = self.relnum_to_ip(freelist[0]['end'])
            if not ns_ip:
                self._logger.error("Cannot configure IP address for NS")
            else:
                self.set('ns_ip', ns_ip)
        else:
            self._name = mongo_doc['name']
            self._id = mongo_doc['_id']
            self._DBRef = DBRef(self._collection_name, self._id)
        self._logger = logging.getLogger(__name__ + '.' + self._name)

    def _guess_ns_hostname(self):
        ns_hostname = socket.gethostname().split('.')[0]
        if ns_hostname[-1:].isdigit():
            import re
            index = re.match('.*?([0-9]+)$', ns_hostname).group(1)
            guessed_name = ns_hostname.split(index)[0]
            guessed_ip = None
            try:
                guessed_ip = socket.gethostbyname(guessed_name)
            except:
                pass
            if guessed_ip:
                self._logger.info("Guessed that NS server should be '" + guessed_name + "', but not '" + ns_hostname + "'. Please change if it is not true.")
                return guessed_name
        return ns_hostname

    def absnum_to_ip(self, numip):
        try:
            ip = socket.inet_ntoa(struct.pack('>L', numip))
        except:
            self._logger.error("Cannot compute numeric ip = '{}' to human readable".format(numip))
            return None
        return ip

    def ip_to_absnum(self, ip):
        try:
            absnum = struct.unpack('>L', (socket.inet_aton(ip)))[0]
        except:
            self._logger.error("Cannot compute ip = '{}'".format(ip))
            return None
        return absnum

    def relnum_to_ip(self, numip):
        num_net = self._get_json()['NETWORK']
        return self.absnum_to_ip(num_net + numip)

    def ip_to_relnum(self, ip):
        num_net = self._get_json()['NETWORK']
        num_ip = self.ip_to_absnum(ip)
        if not self.ip_in_net(ip):
            self._logger.error("Ip = '{}' is not in network.".format(ip))
            return None
        return num_ip - num_net

    def get_base_net(self, address, prefix):
        if type(prefix) is not int:
            self._logger.error("'prefix' should be integer")
            return None
        if prefix not in range(1,32):
            self._logger.error("'prefix' should be 1>= and <=32")
            return None
        if type(address) is long or type(address) is int:
            net_num = address
        else:
            try:
                net_num = struct.unpack('>L', (socket.inet_aton(address)))[0]
            except socket.error:
                self._logger.debug("'{}' does not looks like valid ip-address".format(address))
                return None
        mask_num = ((1<<32) -1) ^ ((1<<(33-prefix)-1) -1)
        return net_num & mask_num

    def ip_in_net(self, ip):
        if type(ip) is int:
            num_ip = ip
        else:
            num_ip = self.ip_to_absnum(ip)
        num_net = self._get_json()['NETWORK']
        prefix = self._get_json()['PREFIX']
        return self.get_base_net(num_net, prefix) == self.get_base_net(ip, prefix)

    def set(self, key, value):
        if not bool(key) or type(key) is not str :
            self._logger.error("Field should be specified")
            return None
        if not key in self._keylist:
            self._logger.error("Cannot change '{}' field".format(key))
            return None
        obj_json = self._get_json()
        if key == 'ns_ip':
            ns_ip = self.ip_to_relnum(value)
            if not ns_ip:
                self._logger.error("Cannot configure IP address for NS")
                return None
            old_ip = None
            try:
                old_ip = self.get('ns_ip')
            except:
                pass
            if bool(old_ip):
                self.release_ip(old_ip)
            self.reserve_ip(ns_ip)
            obj_json = self._get_json()
            obj_json['ns_ip'] = ns_ip
        if key == 'ns_hostname':
            obj_json['ns_hostname'] = value
        if key == 'NETWORK':
            prefix = self._get_json()['PREFIX']
            network = self.get_base_net(value, prefix)
            if not bool(network):
                self._logger.error("Cannot compute NETWORK for entered '{}'".format(value))
                return None
            obj_json['NETWORK'] = network
            obj_json['PREFIX'] = prefix
        if key == 'PREFIX':
            network = self._get_json()['NETWORK']
            new_network = self.get_base_net(network, value)
            if not bool(new_network):
                self._logger.error("Cannot compute NETWORK for prefix = '{}'".format(value))
                raise RuntimeError
            if not self._set_uplimit_ip(value):
                self._logger.error("Cannot set PREFIX as some IPs are reserved out of the new border.".format(value))
                raise RuntimeError
            obj_json['NETWORK'] = network
            obj_json['PREFIX'] = value
        ret = self._mongo_collection.update({'_id': self._id}, {'$set': obj_json}, multi=False, upsert=False)
        return not 'err' in ret

    def get(self, key):
        if not key or type(key) is not str:
            return None
        obj_json = self._get_json()
        if key == 'NETWORK':
            return self.absnum_to_ip(obj_json[key])
        if key == 'NETMASK':
            prefix = obj_json['PREFIX']
            prefix_num = ((1<<32) -1) ^ ((1<<(33-prefix)-1) -1)
            return socket.inet_ntoa(struct.pack('>L', (prefix_num)))
        if key == 'PREFIX':
            return obj_json['PREFIX']
        if key == 'ns_ip':
            return self.relnum_to_ip(obj_json['ns_ip'])
        return super(Network, self).get(key)

    def _get_next_ip(self):
        obj_json = self._get_json()
        try:
            freelist = obj_json['freelist']
        except:
            return None
        if not bool(freelist):
            self._logger.error("No more IPs avalilable")
            return None
        first_elem = freelist[0]
        if first_elem['start'] == first_elem['end']:
            freelist.pop(0)
            res = self._save_free_list(freelist)
            if not res:
                self._logger.error("Error during saving to MongoDB")
                return None
            return first_elem['start']
        freelist[0] = {'start': first_elem['start'] + 1, 'end': first_elem['end']}
        res = self._save_free_list(freelist)
        if not res:
            self._logger.error("Error during saving to MongoDB")
            return None
        return first_elem['start']

    def _get_ip(self, ip1, ip2 = None):

        def change_elem(num, elem):
            find = False
            if num not in range(elem['start'], elem['end']+1):
                return ( find, [elem] )
            find = True
            if elem['end'] == elem['start']:
                return ( find, None )
            if num == elem['start']:
                return ( find, [{'start': elem['start'] + 1, 'end': elem['end']}] )
            if num == elem['end']:
                return ( find, [{'start': elem['start'], 'end': elem['end'] - 1}] )
            return ( find, [{'start': elem['start'], 'end': num-1}, {'start': num+1, 'end': elem['end']}] )
 
        obj_json = self._get_json()
        if not bool(ip2):
            ip2 = ip1
        try:
            freelist = obj_json['freelist']
        except:
            return None
        if not bool(freelist):
            self._logger.error("No more IPs avalilable")
            return None
        start = freelist[0]['start']
        finish = freelist[-1]['end']
        if ip1 not in range(start, finish + 1):
            self._logger.error("Requested IP '{}' is out of range".format(ip1))
            return None
        if ip2 not in range(start, finish + 1):
            self._logger.error("Requested IP '{}' is out of range".format(ip2))
            return None
        # find if ip1 and ip2 fit in any free range:
        for elem in freelist:
            if ip1 in range(elem['start'], elem['end']+1) and ip2 not in range(elem['start'], elem['end']+1):
                self._logger.error("No free range for IPs.")
                return None
        ret_array = [0 ,0]
        for num in range(ip1, ip2+1):
            new_list = []
            find = False
            for elem in freelist:
                new_elem = change_elem(num, elem)
                if new_elem[0]:
                    if num == ip1:
                        ret_array = [num, num]
                    ret_array[1] = num
                    find = True
                if not new_elem[1]:
                    continue
                new_list.extend(new_elem[1])
            freelist = new_list[:]
        ret = self._save_free_list(freelist)
        if not ret:
            return None
        if find:
            if ret_array[0] == ret_array[1]:
                return ret_array[0]
            else:
                return ret_array
        self._logger.error("Requested IP '{}' is out of free range".format(num))
        return None
 
    def _set_uplimit_ip(self, prefix):
        border = (1<<(32-prefix))-1
        obj_json = self._get_json()
        try:
            freelist = obj_json['freelist']
        except:
            return None
        last_elem = freelist[-1]
        if last_elem['start'] > border:
            self._logger.error("Cannot cut list of free IPs. Requested cut to '{}'".format(border))
            return False
        freelist[-1] = {'start': last_elem['start'], 'end': border}
        return self._save_free_list(freelist)

    def _save_free_list(self, freelist):
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        res = self._mongo_collection.update({'_id': self._id}, {'$set': {'freelist': freelist}}, multi=False, upsert=False)
        if 'err' in res:
            self._logger.error("Error while saving list of free IPs: '{}'".format(freelist))
        return not 'err' in res
 
    def reserve_ip(self, ip1 = None, ip2 = None):
        if type(ip1) is str:
            ip1 = self.ip_to_relnum(ip1)
        if type(ip2) is str:
            ip2 = self.ip_to_relnum(ip2)
        if bool(ip2):
            if ip2 <= ip1:
                self._logger.error("Wrong range definition.")
                return None
            return self._get_ip(ip1, ip2)
        if bool(ip1):
            return self._get_ip(ip1)
        return self._get_next_ip()

    def release_ip(self, ip1, ip2 = None):
        if type(ip1) is str:
            ip1 = self.ip_to_relnum(ip1)
        if not bool(ip2):
            ip2 = ip1
        else:
            if ip2 <= ip1:
                self._logger.error("Wrong range definition.")
                return None
        if type(ip2) is str:
            ip2 = self.ip_to_relnum(ip2)
        obj_json = self._get_json()
        try:
            freelist = obj_json['freelist']
        except:
            return None
        res = True
        for num in range(ip1, ip2 + 1):
            insert_elem = {'start': num, 'end': num}
            filled_list = []
            for elem in freelist:
                try:
                    prev_end = filled_list[-1]['end']
                except:
                    prev_end = 0
                next_start = elem['start']
                if num in range(prev_end + 1, next_start):
                    filled_list.extend([insert_elem])
                filled_list.extend([elem])
            prefix = self._get_json()['PREFIX']
            upborder = (1<<(32-prefix))-1
            if num <= upborder and num > freelist[-1]['end']:
                filled_list.extend([insert_elem])
            if len(freelist) == len(filled_list):
                self._logger.error("Cannot release IP. '{}' is already in list: '{}'".format(num, freelist))
                res = False
                next
                #return False
            defrag_list = []
            defrag_list.extend([filled_list.pop(0)])
            for key in filled_list:
                if defrag_list[-1]['end'] == (key['start'] - 1):
                    defrag_list[-1]['end'] = key['end']
                else:
                    defrag_list.extend([key])
            freelist = defrag_list[:]
        self._save_free_list(freelist)
        return res
 
    def get_used_ips(self):
        obj_json = self._get_json()
        try:
            freelist = obj_json['freelist'][:]
        except:
            return None
        lastip = freelist[-1]['start']
        ips = []
        for i in range(1,lastip):
            if i in range(freelist[0]['start'], freelist[0]['end']+1):
                continue
            if i > freelist[0]['end']:
                freelist.pop(0)
            ips.extend([self.relnum_to_ip(i)])
        return ips
    
    def resolve_used_ips(self):
        from luna.node import Group, Node
        from luna.switch import Switch
        from luna.otherdev import OtherDev
        from bson.objectid import ObjectId
        obj_json = self._get_json()
        try:
            rev_links = obj_json[usedby_key]
        except:
            self._logger.error("No IP addresses for network '{}' configured.".format(self.name))
            return None
        out_dict = {}

        def add_to_out_dict(name, ip):
            try:
                out_dict[name]
                self._logger.error("Duplicate name '{}' in network '{}' detected".format(name, self.name))
            except:
                out_dict[name] = self.relnum_to_ip(ip)

        for elem in rev_links:
            if elem == "group":
                for grp_id in rev_links[elem]:
                    group = Group(id = ObjectId(grp_id), mongo_db = self._mongo_db)
                    tmp_dict = group.get_rel_ips_for_net(self.id)
                    for nodename in tmp_dict:
                        add_to_out_dict(nodename, tmp_dict[nodename])
            if elem == "switch":
                for switch_id in rev_links[elem]:
                    switch = Switch(id = ObjectId(switch_id), mongo_db = self._mongo_db)
                    add_to_out_dict(switch.name, switch.get_rel_ip())
            if elem == "otherdev":
                for otherdev_id in rev_links[elem]:
                    otherdev = OtherDev(id = ObjectId(otherdev_id), mongo_db = self._mongo_db)
                    add_to_out_dict(otherdev.name, otherdev.get_ip(self.id))
        add_to_out_dict(obj_json['ns_hostname'], obj_json['ns_ip'])
        return out_dict
