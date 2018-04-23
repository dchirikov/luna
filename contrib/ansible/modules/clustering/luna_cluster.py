#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
from ansible.errors import AnsibleError

try:
    import luna
except ImportError:
    raise AnsibleError("luna is not installed")

from luna_ansible.helpers import StreamStringLogger
import traceback
import os
import logging

if luna.__version__ != '1.2':
    raise AnsibleError("Only luna-1.2 is supported")


def luna_cluster_present(data):
    data.pop('state')
    makedhcp = data.pop('makedhcp')
    makedns = data.pop('makedns')
    dhcp_net = data.pop('dhcp_net')
    dhcp_range_start = data.pop('dhcp_range_start')
    dhcp_range_end = data.pop('dhcp_range_end')
    native_dhcp_ha = data.pop('native_dhcp_ha')

    if data['path'] is not None:
        data['path'] = os.path.abspath(data['path'])

    changed = False
    res = True

    try:
        cluster = luna.Cluster()

    except RuntimeError:
        if data['frontend_address'] is None:
            msg = 'frontend_address should be specified on creation'
            return True, False, msg
        init = {}
        for key in data:
            if key in ['nodeprefix', 'nodedigits', 'path', 'user']:
                init[key] = data[key]
        init['create'] = True
        cluster = luna.Cluster(**init)
        changed = True

    try:
        cluster = luna.Cluster()
        out = ''

        for key in data:
            if data[key] is not None and cluster.get(key) != data[key]:
                out += '{}={},'.format(key, data[key])
                changed = True
                res &= cluster.set(key, data[key])

        if makedns:
            if not cluster.makedns():
                return True, False, 'Unable to build DNS config'
            changed = True

        if makedhcp:
            no_ha = not native_dhcp_ha

            if dhcp_net:
                if not (dhcp_range_start and dhcp_range_end):
                    return True, False, ('Unable to build DHCP config. ' +
                                         'Network range should be specified')

            else:
                if dhcp_range_start or dhcp_range_end:
                    return True, False, ('Unable to build DHCP config. ' +
                                         'Network should be specified.')

            need_to_rebuild_dhcp = False

            old_dhcp_net = cluster.get('dhcp_net')
            old_dhcp_range_start = cluster.get('dhcp_range_start')
            old_dhcp_range_end = cluster.get('dhcp_range_end')

            if (old_dhcp_net != dhcp_net
                    or old_dhcp_range_start != dhcp_range_start
                    or old_dhcp_range_end != dhcp_range_end):

                need_to_rebuild_dhcp = True

            if need_to_rebuild_dhcp:

                if not cluster.makedhcp(
                        dhcp_net, dhcp_range_start, dhcp_range_end, no_ha):

                    return True, False, 'Unable to build DHCP config.'

                changed = True

        return not res, changed, str(cluster) + ' ' + out
    except Exception as e:
        return True, False, str(e) + traceback.format_exc()


def luna_cluster_absent(data):
    for k, v in data.items():
        exec('%s = v' % k)
    try:
        cluster = luna.Cluster()
        cluster.delete(force=True)
        return False, True, ''
    except Exception as e:
        return True, False, str(e) + traceback.format_exc()


def main():
    log_string = StreamStringLogger()
    loghandler = logging.StreamHandler(stream=log_string)
    formatter = logging.Formatter('%(levelname)s: %(message)s')
    logger = logging.getLogger()
    loghandler.setFormatter(formatter)
    logger.addHandler(loghandler)

    module = AnsibleModule(
        argument_spec={

            'nodeprefix': {
                'type': 'str',  'default': 'node',   'required': False},

            'nodedigits': {
                'type': 'int',  'default':  3,       'required': False},

            'user': {
                'type': 'str',  'default': 'luna',   'required': False},

            'path': {
                'type': 'str',  'default': None,     'required': False},

            'frontend_address': {
                'type': 'str',  'default': None,     'required': False},

            'frontend_port': {
                'type': 'int',  'default': None,     'required': False},

            'server_port': {
                'type': 'int',  'default': None,     'required': False},

            'tracker_interval': {
                'type': 'int',  'default': None,     'required': False},

            'tracker_min_interval': {
                'type': 'int',  'default': None,     'required': False},

            'tracker_maxpeers': {
                'type': 'int',  'default': None,     'required': False},

            'torrent_listen_port_min': {
                'type': 'int',  'default': None,     'required': False},

            'torrent_listen_port_max': {
                'type': 'int',  'default': None,     'required': False},

            'torrent_pidfile': {
                'type': 'str',  'default': None,     'required': False},

            'lweb_num_proc': {
                'type': 'int',  'default': None,     'required': False},

            'lweb_pidfile': {
                'type': 'str',  'default': None,     'required': False},

            'cluster_ips': {
                'type': 'str',  'default': None,     'required': False},

            'named_include_file': {
                'type': 'str',  'default': None,     'required': False},

            'named_zone_dir': {
                'type': 'str',  'default': None,     'required': False},

            'comment': {
                'type': 'str',  'default': None,     'required': False},

            # dhcpmake related parameters

            'dhcp_net': {
                'type': 'str',  'default': None,     'required': False},

            'dhcp_range_start': {
                'type': 'str',  'default': None,     'required': False},

            'dhcp_range_end': {
                'type': 'str',  'default': None,     'required': False},

            'native_dhcp_ha': {
                'type': 'bool', 'default': False,    'required': False},

            # actions

            'makedns': {
                'type': 'bool', 'default': False,    'required': False},

            'makedhcp': {
                'type': 'bool', 'default': False,    'required': False},

            'state': {
                'type': 'str',
                'default': 'present',
                'choices': ['present', 'absent']
            }
        }
    )

    choice_map = {
        'present': luna_cluster_present,
        'absent': luna_cluster_absent,
    }

    is_error, has_changed, result = choice_map.get(
        module.params['state'])(module.params)

    if not is_error:
        module.exit_json(changed=has_changed, msg=str(log_string), meta=result)
    else:
        module.fail_json(changed=has_changed, msg=str(log_string), meta=result)


if __name__ == '__main__':
    main()
