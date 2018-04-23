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

from bson.dbref import DBRef

from luna import utils
from luna.base import Base
from luna.cluster import Cluster
from luna.network import Network


class Switch(Base):
    """Class for operating with switch records"""

    log = logging.getLogger(__name__)

    def __init__(self, name=None, mongo_db=None, create=False,
                 id=None, network=None, ip=None, read='public',
                 rw='private', oid=None, comment=''):
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

        self.log.debug("function args {}".format(self._debug_function()))

        # Define the schema used to represent switch objects

        self._collection_name = 'switch'
        self._keylist = {
            'read': type(''),
            'rw': type(''),
            'oid': type(''),
            'comment': type(''),
        }

        # Check if this switch is already present in the datastore
        # Read it if that is the case

        switch = self._get_object(name, mongo_db, create, id)

        if create:
            cluster = Cluster(mongo_db=self._mongo_db)

            if not network:
                err_msg = "Network must be provided"
                self.log.error(err_msg)
                raise RuntimeError, err_msg

            if not name:
                err_msg = "Name must be provided"
                self.log.error(err_msg)
                raise RuntimeError, err_msg

            net = Network(name=network, mongo_db=self._mongo_db)
            ip = net.reserve_ip(ip)

            if not ip:
                err_msg = "Could not acquire ip for switch"
                self.log.error(err_msg)
                raise RuntimeError, err_msg

            # Store the new switch in the datastore

            switch = {'name': name, 'network': net.DBRef, 'ip': ip,
                      'read': read, 'rw': rw, 'oid': oid, 'comment': comment}

            self.log.debug("Saving switch '{}' to the datastore"
                           .format(switch))

            self.store(switch)

            # Link this switch to its dependencies and the current cluster

            self.link(cluster)
            self.link(net)

        self.log = logging.getLogger('switch.' + self._name)

    def get(self, key):
        if key == 'ip':
            net_dbref = self._json['network']

            if not net_dbref:
                return None

            net = Network(id=net_dbref.id, mongo_db=self._mongo_db)
            return utils.ip.reltoa(
                net._json['NETWORK'], self._json['ip'], net.version)

        if key == 'network':
            net_dbref = self._json['network']

            if not net_dbref:
                return None

            net = Network(id=net_dbref.id, mongo_db=self._mongo_db)
            return net.name

        return super(Switch, self).get(key)

    def get_rel_ip(self):
        return self._json['ip']

    def set(self, key, value):
        if key == 'ip':
            net = Network(id=self._json['network'].id, mongo_db=self._mongo_db)

            if self._json['ip']:
                net.release_ip(self._json['ip'])

            ip = net.reserve_ip(value)
            ret = super(Switch, self).set('ip', ip)

            return ret

        elif key == 'network':
            net = Network(id=self._json['network'].id, mongo_db=self._mongo_db)
            ip = self._json['ip']

            new_net = Network(name=value, mongo_db=self._mongo_db)
            if net.DBRef == new_net.DBRef:
                return None

            new_ip = ip
            if not new_net.reserve_ip(new_ip):
                return None

            net.release_ip(ip)
            self.unlink(net)

            ret = super(Switch, self).set('network', new_net.DBRef)
            self.link(new_net)

            return ret

        else:
            return super(Switch, self).set(key, value)

    def release_resources(self):
        net_dbref = self._json['network']
        net = Network(id=net_dbref.id, mongo_db=self._mongo_db)
        net.release_ip(self.get('ip'))

        return True
