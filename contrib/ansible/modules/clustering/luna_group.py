#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
from ansible.errors import AnsibleError

try:
    import luna
except ImportError:
    raise AnsibleError("luna is not installed")

from luna_ansible.helpers import StreamStringLogger
import logging

if luna.__version__ != '1.2':
    raise AnsibleError("Only luna-1.2 is supported")


def luna_group_present(data):
    data.pop('state')
    name = data.pop('name')

    # perform interface data checking, make sure networks are exist,
    # interface names are unique, etc.
    #
    interfaces = data.pop('interfaces')
    tmp_interfaces = {}
    for elem in interfaces:

        if not 'name' in elem:
            return True, False, "No name for interface defined"

        if_name = elem['name']

        if if_name in tmp_interfaces.keys():
            err_msg = "Duplicate name for interface '{}'".format(if_name)
            return True, False, err_msg

        tmp_interfaces[if_name] = {}

        if 'params' in elem:
            tmp_interfaces[if_name]['params'] = elem['params']
        else:
            tmp_interfaces[if_name]['params'] = None

        nets = {'4': None, '6': None}

        if not 'networks' in elem:
            tmp_interfaces[if_name]['networks'] = nets
            continue

        for network in elem['networks']:
            try:
                net = luna.Network(name=network)
            except RuntimeError:
                err_msg = "No such network '{}'".format(network)
                return True, False, err_msg

            if net.version in nets:
                err_msg = "The can be only one v4 and one v6 network"
                return True, False, err_msg

            nets[str(net.version)] = net.name

        tmp_interfaces[if_name]['networks'] = nets

    data['interfaces'] = tmp_interfaces

    changed = False
    ret = True

    try:
        group = luna.Group(name=name)

    except RuntimeError:
        args = data.copy()

        if args['osimage'] is None:
            err_msg = "OsImage should be specified"
            return True, False, err_msg

        args['name'] = name
        args['create'] = True
        args['interfaces'] = data['interfaces'].keys()
        group = luna.Group(**args)
        changed = True

    keys = ['prescript', 'postscript', 'partscript', 'torrent_if', 'comment']
    group_show = group.show()

    for key in keys:
        if data[key] is None:
            continue
        if group_show[key] != data[key]:
            ret &= group.set(key, data[key])
            changed = True

    # FIXME
    # need to change API in luna
    if (data['domain'] is not None
            and group_show['domain'] != '[' + data['domain'] + ']'):
        ret &= group.set_domain(data['domain'])
        changed = True

    if (data['bmcsetup'] is not None
            and group_show['bmcsetup'] != '[' + data['bmcsetup'] + ']'):
        ret &= group.bmcsetup(data['bmcsetup'])
        changed = True

    if (data['osimage'] is not None
            and group_show['osimage'] != '[' + data['osimage'] + ']'):
        ret &= group.osimage(data['osimage'])
        changed = True

    # make sure sets of the interfaces are the same
    ansible_ifs = set(data['interfaces'].keys())
    configured_ifs = set(group.list_ifs().keys())

    ifs_to_delete = [e for e in configured_ifs if e not in ansible_ifs]
    ifs_to_add = [e for e in ansible_ifs if e not in configured_ifs]

    for interface in ifs_to_delete:
        changed = True
        ret &= group.del_interface(interface)

    for interface in ifs_to_add:
        changed = True
        ret &= group.add_interface(interface)

    # now make sure we have same nets assigned
    for interface in ansible_ifs:
        if_json = group.show_if(interface)
        if_params = data['interfaces'][interface]['params']

        if (if_params is not None
                and if_params != group.get_if_params(interface)):
            ret &= group.set_if_params(interface, if_params)
            changed = True

        for net_ver in ['4', '6']:
            ansible_net = data['interfaces'][interface]['networks'][net_ver]
            configured_net = if_json['network'][net_ver]['name'] or None

            if ansible_net == configured_net:
                continue

            if ansible_net is None:
                group.del_net_from_if(interface, configured_net)
                changed = True
            else:
                if configured_net is not None:
                    ret &= group.del_net_from_if(interface, configured_net)
                ret &= group.set_net_to_if(interface, ansible_net)
                changed = True

    return not ret, changed, ""


def luna_group_absent(data):
    name = data['name']
    try:
        group = luna.Group(name=name)
    except RuntimeError:
        return False, False, name

    res = group.delete()

    return not res, res, name


def main():
    log_string = StreamStringLogger()
    loghandler = logging.StreamHandler(stream=log_string)
    formatter = logging.Formatter('%(levelname)s: %(message)s')
    logger = logging.getLogger()
    loghandler.setFormatter(formatter)
    logger.addHandler(loghandler)

    module = AnsibleModule(
        argument_spec={
            'name': {
                'type': 'str', 'required': True},
            'osimage': {
                'type': 'str', 'required': False},
            'bmcsetup': {
                'type': 'str', 'required': False},
            'domain': {
                'type': 'str', 'default': None, 'required': False},
            'interfaces': {
                'type': 'list', 'default': [], 'required': False},
            'torrent_if': {
                'type': 'str', 'default': None, 'required': False},
            'prescript': {
                'type': 'str', 'default': None, 'required': False},
            'postscript': {
                'type': 'str', 'default': None, 'required': False},
            'partscript': {
                'type': 'str', 'default': None, 'required': False},
            'comment': {
                'type': 'str', 'default': None, 'required': False},
            'state': {
                'type': 'str', 'default': 'present',
                'choices': ['present', 'absent']}
        }
    )

    choice_map = {
        'present': luna_group_present,
        'absent': luna_group_absent,
    }

    is_error, has_changed, result = choice_map.get(
        module.params['state'])(module.params)

    if not is_error:
        module.exit_json(changed=has_changed, msg=str(log_string), meta=result)
    else:
        module.fail_json(changed=has_changed, msg=str(log_string), meta=result)


if __name__ == '__main__':
    main()
