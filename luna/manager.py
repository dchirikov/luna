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

import tornado.web
import tornado.gen

from bson.dbref import DBRef

import luna
from luna import utils


class Manager(tornado.web.RequestHandler):

    def initialize(self, params):
        self.protocol = params['protocol']
        self.server_ip = params['server_ip']
        self.server_port = params['server_port']
        self.mongo = params['mongo_db']
        self.log = params['app_logger']


    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        step = self.get_argument('step')

        if step == 'boot':
            nodes = luna.list('node')
            p = {
                'protocol': self.protocol,
                'server_ip': self.server_ip,
                'server_port': self.server_port,
                'nodes': nodes
            }

            self.render("templ_ipxe.cfg", p=p)

        elif step == 'discovery':
            hwdata = self.get_argument('hwdata', default=None)
            if not hwdata:
                self.send_error(400)  # Bad Request
                return

            macs = set(hwdata.split('|'))

            # Node name selected manualy in ipxe
            req_nodename = self.get_argument('node', default=None)
            if req_nodename:
                self.log.info("Node '{}' was chosen in iPXE"
                              .format(req_nodename))
                req_nodename = str(req_nodename)
                try:
                    node = luna.Node(name=req_nodename, mongo_db=self.mongo)
                except:
                    self.log.error("No such node '{}' exists"
                                   .format(req_nodename))
                    self.send_error(400)
                    return

                mac = None
                for mac in macs:
                    if mac:
                        mac = str(mac.lower())
                        self.log.info("Node '{}' trying to set '{}' as mac"
                                      .format(req_nodename, mac))

                        if node.set_mac(mac):
                            node.update_status('boot.mac_assigned')
                            break

                        self.log.error("MAC: '{}' looks wrong.".format(mac))

            # need to find node for given macs.
            # first step - trying to find in known macs
            found_node = None
            for mac in macs:
                if not mac:
                    continue

                mac = mac.lower()
                try:
                    found_node = self.mongo['mac'].find_one({'mac': mac}, {'_id': 0, 'node': 1})['node']
                except:
                    continue

                if found_node:
                    break

            # second step. now try to find in learned switch macs
            # if we have switch/port configured
            if not found_node:
                mac_from_cache = None

                for mac in macs:
                    mac_cursor = self.mongo['switch_mac'].find({'mac': mac})

                    # first search mac in switch_mac using
                    # portnames like 'Gi2/0/26'
                    for elem in mac_cursor:
                        switch_id = elem['switch_id']
                        portname = elem['portname']

                        try:
                            node_id = self.mongo['node'].find_one({'switch': DBRef('switch', switch_id), 'port': portname}, {})['_id']
                            mac_from_cache = mac
                        except:
                            continue

                        if mac_from_cache:
                            break

                    if mac_from_cache:
                        break

                    # now search mac in switch_mac using portnumbers
                    for elem in mac_cursor:
                        switch_id = elem['switch_id']
                        port = elem['port']

                        try:
                            node_id = self.mongo['node'].find_one({'switch': DBRef('switch', switch_id), 'port': port}, {})['_id']
                            mac_from_cache = mac
                        except:
                            continue

                        if mac_from_cache:
                            break

                    if mac_from_cache:
                        break

                if not mac_from_cache:
                    self.log.info("Cannot find '{}' in learned macs."
                                  .format("', '".join([mac for mac in macs])))
                    # did not find in learned macs
                    self.send_error(404)
                    return

                # here we should have node_id and mac_from_cache
                try:
                    node = luna.Node(id=node_id, mongo_db=self.mongo)
                    utils.helpers.set_mac_node(mac_from_cache, node.DBRef)
                    found_node = node.DBRef
                except:
                    # should not be here
                    self.log.info("Cannot create node object for '{}' and '{}'"
                                  .format(found_name_from_learned, self.mongo))
                    self.send_error(404)
                    return

            # here we should have found_node
            try:
                node = luna.Node(id=found_node.id, mongo_db=self.mongo)
            except:
                # should not be here
                self.log.info("Cannot create node object for '{}' and '{}'"
                              .format(found_node, self.mongo))
                self.send_error(404)
                return

            # found node finally
            boot_params = node.boot_params

            boot_params['server_ip'] = self.server_ip
            boot_params['server_port'] = self.server_port
            boot_params['protocol'] = self.protocol

            boot_type = self.get_argument('type', default='ipxe')
            if boot_type == 'ipxe':
                node.update_status('boot.request')
                self.render("templ_nodeboot.cfg", p=boot_params)

            elif boot_type == 'syslinux':
                node.update_status('boot.request')
                self.render("templ_nodeboot_syslinux.cfg", p=boot_params)

            else:
                self.send_error(404)

        elif step == 'install':
            node_name = self.get_argument('node', default=None)
            if not node_name:
                self.log.error("Node name must be provided")
                self.send_error(400)
                return

            node_name = str(node_name)

            try:
                node = luna.Node(name=node_name, mongo_db=self.mongo)
            except:
                self.log.error("No such node '{}' exists".format(node_name))
                self.send_error(400)
                return

            status = self.get_argument('status', default='')

            if status:
                node.update_status(status)
                self.finish()
                return

            install_params = node.install_params
            if not install_params['torrent']:
                self.send_error(404)
                return

            install_params['protocol'] = self.protocol
            install_params['server_ip'] = self.server_ip
            install_params['server_port'] = self.server_port

            node.update_status('install.request')

            self.render("templ_install.cfg", p=install_params)
