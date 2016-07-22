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
from bson.objectid import ObjectId
from luna.base import Base
from luna.cluster import Cluster
from luna.network import Network

class OtherDev(Base):
    """
    Class for other devices
    """
    def __init__(self, name = None, mongo_db = None, create = False, id = None, network = None,
            ip = None):
        """
        netwwork - network device connected
        ip       - ip of the switch
        """
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        self._collection_name = 'otherdev'
        mongo_doc = self._check_name(name, mongo_db, create, id)
        self._keylist = {}
        if create:
            cluster = Cluster(mongo_db = self._mongo_db)
            passed_vars = inspect.currentframe().f_locals
            for key in self._keylist:
                if type(passed_vars[key]) is not self._keylist[key]:
                    self._logger.error("Argument '{}' should be '{}'".format(key, self._keylist[key]))
                    raise RuntimeError
            if not bool(network):
                connected = {}
            else:
                if not bool(ip):
                    self._logger.error("IP needs to be specified")
                    raise RuntimeError
                net = Network(name = network, mongo_db = self._mongo_db)
                ip = net.reserve_ip(ip)
                connected = {str(net.DBRef.id): ip}
            mongo_doc = { 'name': name, 'connected': connected}
            self._logger.debug("mongo_doc: '{}'".format(mongo_doc))
            self._name = name
            self._id = self._mongo_collection.insert(mongo_doc)
            self._DBRef = DBRef(self._collection_name, self._id)
            self.link(cluster)
            if bool(connected):
                self.link(net)
        else:
            self._name = mongo_doc['name']
            self._id = mongo_doc['_id']
            self._DBRef = DBRef(self._collection_name, self._id)

    def get_ip(self, network_name = None):
        if not bool(network_name):
            self._logger.error("Network needs to be specified")
            return None
        nets = self._get_json()['connected']
        if type(network_name) == ObjectId:
            try:
                return nets[str(network_name)]
            except:
                self._logger.error("Cannot find configured IP in the network '{}' for '{}'".format(str(network_name), self.name))
                return None
        for rec in nets:
            net = Network(id = ObjectId(rec), mongo_db = self._mongo_db)
            if net.name == network_name:
                return net.relnum_to_ip(nets[rec])
        return None

    def del_net(self, network = None):
        if not bool(network):
            self._logger.error("Network should be specified")
            return None

        obj_json = self._get_json()
        net = Network(network, mongo_db = self._mongo_db)
        rel_ip = None
        try:
            rel_ip = obj_json['connected'][str(net.id)]
        except:
            self._logger.error("Cannot find configured IP in the network '{}' for '{}'".format(network, self.name))
            return None
        net.release_ip(net.relnum_to_ip(rel_ip))
        obj_json['connected'].pop(str(net.id))
        ret = self._mongo_collection.update({'_id': self._id}, {'$set': obj_json}, multi=False, upsert=False)
        self.unlink(net)
        return not 'err' in ret

    def list_nets(self):
        obj_json = self._get_json()
        nets = []
        for elem in obj_json['connected']:
            nets.append(Network(id = ObjectId(elem), mongo_db = self._mongo_db).name)
        return nets

    def set_ip(self, network = None, ip = None):
        if not bool(network):
            self._logger.error("Network should be specified")
            return None
        if not bool(ip):
            return self.del_net(network = network)
        obj_json = self._get_json()
        net = Network(name = network, mongo_db = self._mongo_db)
        try:
            old_rel_ip = obj_json['connected'][str(net.DBRef.id)]
        except:
            old_rel_ip = None
        if old_rel_ip:
            net.release_ip(net.relnum_to_ip(old_rel_ip))
        new_ip = net.reserve_ip(ip)
        if not new_ip:
            return None
        obj_json['connected'][str(net.DBRef.id)] = new_ip
        ret = self._mongo_collection.update({'_id': self._id}, {'$set': obj_json}, multi=False, upsert=False)
        if not old_rel_ip:
            self.link(net)

    def delete(self):
        obj_json = self._get_json()
        for network in obj_json['connected']:
            net = Network(id = ObjectId(network), mongo_db = self._mongo_db)
            net.release_ip(obj_json['connected'][network])
            self.unlink(net)
        return super(OtherDev, self).delete()

