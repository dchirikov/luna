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

import logging

from bson.objectid import ObjectId

from luna import utils
from luna.base import Base
from luna.cluster import Cluster
from luna.network import Network


class OtherDev(Base):
    """Class for other devices"""

    log = logging.getLogger(__name__)

    def __init__(self, name=None, mongo_db=None, create=False, id=None,
                 network=None, ip=None, comment=''):
        """
        network - the network the device is connected to
        ip      - device's ip
        """

        self.log.debug("function args {}".format(self._debug_function()))

        # Define the schema used to represent otherdev objects

        self._collection_name = 'otherdev'
        self._keylist = {'comment': type('')}

        # Check if this device is already present in the datastore
        # Read it if that is the case

        dev = self._get_object(name, mongo_db, create, id)

        if create:
            cluster = Cluster(mongo_db=self._mongo_db)

            if not network:
                connected = {}
            elif not ip:
                err_msg = "IP needs to be specified"
                self.log.error(err_msg)
                raise RuntimeError, err_msg
            else:
                net = Network(name=network, mongo_db=self._mongo_db)
                ipnum = net.reserve_ip(ip, ignore_errors=False)
                if not ipnum:
                    err_msg = "Unable to allocate IP in network"
                    self.log.error(err_msg)
                    raise RuntimeError, err_msg

                connected = {str(net.DBRef.id): ipnum}

            # Store the new device in the datastore

            dev = {'name': name, 'connected': connected, 'comment': comment}

            self.log.debug("Saving dev '{}' to the datastore".format(dev))

            self.store(dev)

            # Link this device to its dependencies and the current cluster

            self.link(cluster)

            if connected and net:
                self.link(net)

        self.log = logging.getLogger('otherdev.' + self._name)

    def get_ip(self, network=None):
        if not network:
            self.log.error("Network needs to be specified")
            return None

        nets = self.get('connected')
        if type(network) == ObjectId and str(network) in nets:
            return nets[str(network)]

        elif type(network) is str:
            for rec in nets:
                net = Network(id=ObjectId(rec), mongo_db=self._mongo_db)
                if net.name == network and nets[rec]:
                    return utils.ip.reltoa(
                        net._json['NETWORK'], nets[rec], net.version)

        else:
            self.log.error("Device '{}' is not attached to network '{}'"
                           .format(self.name, str(network)))
            return None

    def del_net(self, network=None):
        if not network:
            self.log.error("Network needs to be specified")
            return None

        connected = self.get('connected')

        net = Network(network, mongo_db=self._mongo_db)
        if not str(net.id) in connected:
            self.log.error("Device '{}' is not attached to network '{}'"
                           .format(self.name, str(network)))
            return None

        net.release_ip(connected[str(net.id)])
        connected.pop(str(net.id))
        res = self.set('connected', connected)

        self.unlink(net)

        return res

    def list_nets(self):
        nets = []
        for elem in self.get('connected'):
            net = Network(id=ObjectId(elem), mongo_db=self._mongo_db)
            nets.append(net.name)

        return nets

    def set_ip(self, network=None, ip=None):
        if not network:
            self.log.error("Network needs to be specified")
            return None

        if not ip:
            return self.del_net(network=network)

        connected = self.get('connected')

        link = True
        net = Network(name=network, mongo_db=self._mongo_db)
        if str(net.id) in connected:
            net.release_ip(connected[str(net.id)])
            link = False

        ip = net.reserve_ip(ip)
        if not ip:
            return None

        connected[str(net.id)] = ip
        res = self.set('connected', connected)

        if link:
            self.link(net)
        return res

    def release_resources(self):
        connected = self.get('connected')

        for network in connected:
            if connected[network]:
                net = Network(id=ObjectId(network), mongo_db=self._mongo_db)
                net.release_ip(connected[network])

        return True
