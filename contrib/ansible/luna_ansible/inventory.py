#!/usr/bin/env python

import os
import sys
import argparse
from ansible.utils.display import Display

display = Display()

from ansible.errors import AnsibleError

try:
    import luna
except ImportError:
    raise AnsibleError("luna is not installed")

if luna.__version__ != '1.2':
    raise AnsibleError("Only luna-1.2 is supported")

try:
    import json
except ImportError:
    import simplejson as json

class LunaInventory(object):

    def __init__(self):
        self.inventory = {}
        self.read_cli_args()

        # Called with `--list`.
        if self.args.list:
            try:
                self.inventory = self.luna_inventory()
            except:
                display.warning('Unable to get data from Luna')
                self.inventory = self.empty_inventory()
        # Called with `--host [hostname]`.
        elif self.args.host:
            # Not implemented, since we return _meta info `--list`.
            self.inventory = self.empty_inventory()
        # If no groups or vars are present, return an empty inventory.
        else:
            self.inventory = self.empty_inventory()

        print json.dumps(self.inventory)

    def luna_inventory(self):
        osimage_suffix = ".osimages.luna"
        group_suffix = ".groups.luna"
        inventory = {}
        inventory['_meta'] = { 'hostvars': {}}
        osimages = {'hosts':[],'vars': {'ansible_connection': 'lchroot' }}
        for osimage in luna.list('osimage'):
            #osimages['hosts'].append(luna.OsImage(osimage).get('path'))
            osimages['hosts'].append(osimage + osimage_suffix)
            osimage_path = luna.OsImage(osimage).get('path')
            inventory['_meta']['hostvars'][osimage + osimage_suffix]= {
                'ansible_host': osimage,
            }

        inventory['osimages.luna'] = osimages

        nodes = {}
        inventory['groups.luna'] = {'hosts': []}

        for g in luna.list('group'):
            group = luna.Group(g)
            hosts = []
            nodes = group.list_nodes()

            for node_name in nodes:
                node = luna.Node(node_name)
                hosts.append(node_name)
                inventory['_meta']['hostvars'][node.show()['name']]={
                    "bmc_ip":node.get_ip('BMC',version=4)}

            inventory[g + group_suffix] = {'hosts': hosts}
            inventory['groups.luna']['hosts'].extend(hosts)

        return inventory

    # Empty inventory for testing.
    def empty_inventory(self):
        return {'_meta': {'hostvars': {}}}

    # Read the command line args passed to the script.
    def read_cli_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--list', action = 'store_true')
        parser.add_argument('--host', action = 'store')
        self.args = parser.parse_args()

# Get the inventory.
