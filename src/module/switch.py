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
import sys
import time
import threading
import netsnmp
import datetime
import inspect

from bson.dbref import DBRef
from luna.base import Base
from luna.cluster import Cluster
from luna.network import Network

class Switch(Base):
    """
    Class for operating with switch records
    """
    def __init__(self, name = None, mongo_db = None, create = False, id = None, network = None,
            ip = None, read = 'public', rw = 'private', oid = None):
        """
        ip      - ip of the switch
        read    - read community
        rw      - rw community
        oid     - could be, for instance
                .1.3.6.1.2.1.17.7.1.2.2.1.2
                .1.3.6.1.2.1.17.4.3.1.2
                .1.3.6.1.2.1.17.7.1.2.2
                .1.3.6.1.2.1.17.4.3.1.2
        """
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        self._collection_name = 'switch'
        mongo_doc = self._check_name(name, mongo_db, create, id)
        self._keylist = { 'ip': type(''), 'read': type(''), 'rw': type(''), 'oid': type(''), 'network': type('')}
        if create:
            cluster = Cluster(mongo_db = self._mongo_db)
            passed_vars = inspect.currentframe().f_locals
            for key in self._keylist:
                if type(passed_vars[key]) is not self._keylist[key]:
                    self._logger.error("Argument '{}' should be '{}'".format(key, self._keylist[key]))
                    raise RuntimeError
            net = Network(name = network, mongo_db = self._mongo_db)
            ip = net.reserve_ip(ip)
            if not bool(ip):
                self._logger.error("Could not acquire ip for switch.")
                raise RuntimeError
            mongo_doc = { 'name': name, 'network': net.DBRef, 'ip': ip, 'read': read, 'rw': rw, 'oid': oid}
            self._logger.debug("mongo_doc: '{}'".format(mongo_doc))
            self._name = name
            self._id = self._mongo_collection.insert(mongo_doc)
            self._DBRef = DBRef(self._collection_name, self._id)
            self.link(cluster)
            self.link(net)
        else:
            self._name = mongo_doc['name']
            self._id = mongo_doc['_id']
            self._DBRef = DBRef(self._collection_name, self._id)

    def get(self, key):
        if key == 'ip':
            dbref = None
            try:
                dbref = self._get_json()['network']
            except:
                self._logger.error("Network is not defined for switch")
                return None
            if not bool(dbref):
                return None
            net = Network(id = dbref.id, mongo_db = self._mongo_db)
            return net.relnum_to_ip(self._get_json()['ip'])
        return super(Switch, self).get(key)

    def get_rel_ip(self):
        dbref = None
        try:
            dbref = self._get_json()['network']
        except:
            self._logger.error("Network is not defined for switch")
            return None
        if not bool(dbref):
            return None
        return self._get_json()['ip']

    def set(self, key, value):
        if not bool(key) or type(key) is not str :
            self._logger.error("Field should be specified")
            return None
        if not key in self._keylist:
            self._logger.error("Cannot change '{}' field".format(key))
            return None
        obj_json = self._get_json()
        if key == 'ip':
            net_dbref = obj_json['network']
            old_ip = obj_json['ip']
            net = Network(id = net_dbref.id, mongo_db = self._mongo_db)
            if not net.ip_in_net(value):
                self._logger.error("This IP: '{}' does not belong to defined network.".format(value))
                return None
            if old_ip:
                net.release_ip(old_ip)
            ip = net.reserve_ip(value)
            obj_json['ip'] = ip
            ret = self._mongo_collection.update({'_id': self._id}, {'$set': obj_json}, multi=False, upsert=False)
            return not 'err' in ret
        if key == 'network':
            old_net_dbref = obj_json['network']
            old_net = Network(id = old_net_dbref.id, mongo_db = self._mongo_db)
            old_ip_rel = obj_json['ip']
            old_ip_human_readable = self.get('ip')
            new_net = Network(name = value, mongo_db = self._mongo_db)
            if old_net.DBRef == new_net.DBRef:
                return None
            new_ip_rel = old_ip_rel
            new_ip_human_readable = new_net.relnum_to_ip(new_ip_rel)
            if not new_net.reserve_ip(new_ip_human_readable):
                return None
            old_net.release_ip(old_ip_human_readable)
            obj_json['network'] = new_net.DBRef
            ret = self._mongo_collection.update({'_id': self._id}, {'$set': obj_json}, multi=False, upsert=False)
            self.link(new_net)
            self.unlink(old_net)
            return not 'err' in ret
        return super(Switch, self).set(key, value)

    def delete(self):
        obj_json = self._get_json()
        net_dbref = obj_json['network']
        net = Network(id = net_dbref.id, mongo_db = self._mongo_db)
        ip_human_readable = self.get('ip')
        net.release_ip(ip_human_readable)
        self.unlink(net)
        return super(Switch, self).delete()

class MacUpdater(object):

    def __init__(self, mongo_db, logger = None, interval = 30):
        self._mongo_db = mongo_db
        self.switch_collection = self._mongo_db['switch']
        self.known_mac_collection = self._mongo_db['switch_mac']

        aging = interval * 2
        self.logger = logger
        self.interval = interval
        self.logger.name = 'MacUpdater'
        self.active = True
        self.known_mac_collection.create_index("updated", expireAfterSeconds = aging )
        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True
        thread.start()
 
    def run(self):
        counter = self.interval
        cluster = Cluster(mongo_db = self._mongo_db)
        while self.active:
            if counter >= self.interval:
                if cluster.is_active():
                    self.update()
                else:
                    self.logger.info("This is passive node. Doing nothing.")
                    time.sleep(60)
                counter = 0
            counter += 1
            time.sleep(1)

    def stop(self):
        self.active = False

    def update(self):
        self.logger.info("Updating known mac addresses")
        switches = self.switch_collection.find()
        mac_count = 0
        for switch in switches:
            obj_switch = Switch(id = switch['_id'])
            oid = obj_switch.get('oid')
            ip = obj_switch.get('ip')
            read = obj_switch.get('read')
            switch_id = obj_switch.id
            mongo_doc = {}
            mongo_doc['switch_id'] = switch_id
            try:
                self.logger.debug("Requesting following data: oid=%s\tip=%s\tcommunity=%s\tswitch_id=%s" % (oid, ip, read, switch_id))
                varlist = netsnmp.VarList(netsnmp.Varbind(oid))
                res = netsnmp.snmpwalk(varlist, Version = 1,  DestHost = ip, Community = read)
                updated = datetime.datetime.utcnow()
                for i in range(len(varlist)):
                    mac = ''
                    port = str(varlist[i].val)
                    for elem in varlist[i].tag.split('.')[-6:]:
                        mac += hex(int(elem)).split('x')[1].zfill(2) + ':'
                    mac = mac[:-1].lower()
                    mongo_doc['mac'] = mac
                    mongo_doc['port'] = port
                    mongo_doc_updated = mongo_doc.copy()
                    mongo_doc_updated['updated'] = updated
                    res = self.known_mac_collection.find_and_modify(mongo_doc, {'$set': mongo_doc_updated}, upsert = True)
                    if not bool(res):
                        mac_count += 1
            except NameError:
                if self.logger:
                    self.logger.error("Cannot reach '{}'".format(ip))
            except:
                err = sys.exc_info()[0]
                if self.logger:
                    self.logger.error(err)
        self.logger.info("Was added {} new mac addresses.".format(mac_count))
        return True
