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

from luna.cluster import Cluster
from luna.switch import Switch


class MacUpdater(object):

    def __init__(self, mongo_db, logger=None, interval=30):
        self.log = logger
        self.log.name = 'MacUpdater'

        self._mongo_db = mongo_db
        self.switch_collection = self._mongo_db['switch']
        self.known_mac_col = self._mongo_db['switch_mac']

        aging = interval * 10
        self.known_mac_col.create_index("updated", expireAfterSeconds=aging)

        self.interval = interval
        self.active = True

        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True
        thread.start()

    def run(self):
        counter = self.interval
        cluster = Cluster(mongo_db=self._mongo_db)

        while self.active:
            if counter >= self.interval:
                if cluster.is_active():
                    self.update()
                else:
                    self.log.info("This is passive node. Doing nothing.")
                    time.sleep(60)

                counter = 0

            counter += 1
            time.sleep(1)

    def stop(self):
        self.active = False

    def update(self):
        self.log.info("Updating known mac addresses")
        switches = self.switch_collection.find()
        mac_count = 0

        for switch_doc in switches:
            switch = Switch(id=switch_doc['_id'])
            oid = switch.get('oid')
            ip = switch.get('ip')
            read = switch.get('read')
            switch_id = switch.id

            doc = {'switch_id': switch_id}

            try:
                self.log.debug(("Requesting the following data: "
                                "oid=%s\tip=%s\tcommunity=%s\tswitch_id=%s" %
                                (oid, ip, read, switch_id)))

                vl = netsnmp.VarList(netsnmp.Varbind(oid))
                res = netsnmp.snmpwalk(vl, Version=2, DestHost=ip,
                                       Community=read, UseNumeric=True)

                ifname_oid = '.1.3.6.1.2.1.31.1.1.1.1'  # ifName

                self.log.debug(("Requesting the following data: "
                                "oid=%s\tip=%s\tcommunity=%s\tswitch_id=%s" %
                                (ifname_oid, ip, read, switch_id)))

                vl_ifnames = netsnmp.VarList(netsnmp.Varbind(ifname_oid))
                ifnames = netsnmp.snmpwalk(vl_ifnames, Version=2, DestHost=ip,
                                           Community=read, UseNumeric=True)

                portmap_oid = '.1.3.6.1.2.1.17.1.4.1.2'

                vl_portmap = netsnmp.VarList(netsnmp.Varbind(portmap_oid))
                portmap = netsnmp.snmpwalk(vl_portmap, Version=2, DestHost=ip,
                                           Community=read, UseNumeric=True)

                updated = datetime.datetime.utcnow()

                portmaps = {}
                for i in range(len(vl_portmap)):
                    if vl_portmap[i].iid:
                        pornnum = vl_portmap[i].iid
                    else:
                        pornnum = vl_portmap[i].tag.split('.')[-1:][0]

                    try:
                        portmaps[int(pornnum)] = int(vl_portmap[i].val)
                    except:
                        pass

                portnums = {}
                for i in range(len(vl_ifnames)):
                    if vl_ifnames[i].iid:
                        pornnum = vl_ifnames[i].iid
                    else:
                        pornnum = vl_ifnames[i].tag.split('.')[-1:][0]

                    tmpvar = vl_ifnames[i]
                    try:
                        portnums[int(pornnum)] = str(vl_ifnames[i].val)
                    except:
                        pass

                for i in range(len(vl)):
                    mac = ''
                    port = str(vl[i].val)

                    try:
                        portname = portnums[portmaps[int(vl[i].val)]]
                    except KeyError:
                        portname = port

                    for elem in vl[i].tag.split('.')[-5:]:
                        mac += hex(int(elem)).split('x')[1].zfill(2) + ':'

                    mac += hex(int(vl[i].iid)).split('x')[1].zfill(2)

                    doc['mac'] = mac
                    doc['port'] = port
                    doc['portname'] = portname
                    new_doc = doc.copy()
                    new_doc['updated'] = updated
                    res = self.known_mac_col.find_and_modify(doc,
                                                             {'$set': new_doc},
                                                             upsert=True)
                    if not res:
                        mac_count += 1

            except NameError:
                if self.log:
                    self.log.error("Cannot reach '{}'".format(ip))

            except:
                err_type, err_value, err_traceback = sys.exc_info()

                if self.log:
                    self.log.error('{} in {}'.format(err_type,
                                                     err_traceback.tb_lineno))

        if mac_count > 0:
            self.log.info("Added {} new mac addresses.".format(mac_count))

        return True
