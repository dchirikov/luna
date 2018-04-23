#!/usr/bin/env python
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
import pymongo
import uuid
from luna.utils.helpers import get_con_options
from luna.config import db_name

log = logging.getLogger(__file__)
log.info('Luna migration script to db v1.2')

try:
    mclient = pymongo.MongoClient(**get_con_options())
    mdb = mclient[db_name]
except:
    log.error("Unable to connect to MongoDB.")
    raise RuntimeError


def modify_objects(mdb, collection=None, fun=None):

    if not (collection and fun):
        log.error('collection and fun need to be specified')
        return False

    log.info('Migrating collection {}'.format(collection))

    mongo_collection = mdb[collection]

    objects = mongo_collection.find()
    new_jsons = []

    for json in objects:
        new_json = fun(json)
        if new_json:
            new_jsons.append(new_json)

    for json in new_jsons:

        log.info('Converting {}'.format(json['name']))

        mongo_collection.update(
            {'_id': json['_id']},
            json,
            multi=False, upsert=False
        )


def migrate_group(json):
    interfaces = {}

    # if we have 'domain' key, we don't need to migrate
    if 'domain' in json:
        log.warning('Do not need to migrate {}'.format(json['name']))
        return False

    if 'interfaces' in json:
        for if_name in json['interfaces']:
            if_dict = json['interfaces'][if_name]

            v4_net = None
            params = ''

            if 'network' in if_dict:
                v4_net = if_dict['network']

            if 'params' in if_dict:
                params = if_dict['params']

            interfaces[uuid.uuid4().hex] = {
                'name': if_name,
                'network': {
                    '4': v4_net,
                    '6': None
                },
                'params': params
            }

    json.pop('boot_if')
    bmcnetwork = json.pop('bmcnetwork')
    if bmcnetwork:
        interfaces[uuid.uuid4().hex] = {
            'name': 'BMC',
            'network': {
                '4': bmcnetwork,
                '6': None
            },
            'params': params
        }

    json['interfaces'] = interfaces
    json['domain'] = None
    json['comment'] = None

    return json


def migrate_network(json):

    # if we have 'version' key, we don't need to migrate
    if 'version' in json:
        log.warning('Do not need to migrate {}'.format(json['name']))
        return False

    json['version'] = 4
    json['include'] = None
    json['rev_include'] = None
    json['comment'] = None

    return json


def migrate_node(json):

    # already migrated
    old_interfaces = json['interfaces']
    old_ip = type(old_interfaces[old_interfaces.keys()[0]])
    if not 'bmcnetwork' in json and type(old_ip) == dict:
        log.warning('Do not need to migrate {}'.format(json['name']))
        return False

    from luna import Group

    #interfaces = json.pop('interfaces')
    #bmcnet = json.pop('bmcnetwork')
    group = Group(id=json['group'].id)
    if_names = group.list_ifs()

    interfaces = {}
    for if_name in if_names:
        if if_name == 'BMC':
            try:
                ip = json['bmcnetwork']
            except KeyError:
                ip = None
        else:
            try:
                ip = json['interfaces'][if_name]
            except KeyError:
                ip = None

        if ip:
            ip = int(ip)

        interfaces[if_names[if_name]] = {
            '4': ip,
            '6': None
        }

    json['interfaces'] = interfaces
    if 'bmcnetwork' in json:
        json.pop('bmcnetwork')

    json['comment'] = None

    return json


def migrate_cluster(json):

    # nothing to change
    if 'db_version' in json and json['db_version'] == 1.2:
        log.warning('Do not need to migrate {}'.format(json['name']))
        return False

    json['db_version'] = 1.2
    json['comment'] = None
    json['frontend_https'] = False
    return json


def migrate_osimage(json):
    from luna import Cluster

    # nothing to change
    if 'grab_exclude_list' in json:
        log.warning('Do not need to migrate {}'.format(json['name']))
        return False

    cluster = Cluster()

    if not cluster:
        raise RuntimeError

    grab_list_path = cluster.get('path') + '/templates/grab_default_centos.lst'

    with open(grab_list_path) as lst:
        grab_list_content = lst.read()

    json['grab_exclude_list'] = grab_list_content
    json['grab_filesystems'] = '/,/boot'
    json['comment'] = None

    return json

def add_comment(json):
    if 'comment' in json:
        log.warning('Do not need to migrate {}'.format(json['name']))
        return False
    json['comment'] = None
    return json


modify_objects(mdb, 'group', migrate_group)
modify_objects(mdb, 'network', migrate_network)
modify_objects(mdb, 'node', migrate_node)
modify_objects(mdb, 'cluster', migrate_cluster)
modify_objects(mdb, 'osimage', migrate_osimage)
modify_objects(mdb, 'osimage', add_comment)
modify_objects(mdb, 'switch', add_comment)
modify_objects(mdb, 'otherdev', add_comment)
modify_objects(mdb, 'bmcsetup', add_comment)
