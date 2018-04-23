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


def luna_otherdev_present(data):
    data.pop('state')
    name = data.pop('name')
    changed = False
    ret = True
    if not data['connected']:
        err_msg = ("Need to specify at least one IP and network " +
                   "device is connected to")
        return True, changed, err_msg

    if 'network' not in data['connected'][0]:
        err_msg = ("Network to which device is connected " +
                   "needs to be specified")
        return True, changed, err_msg

    if 'ip' not in data['connected'][0]:
        err_msg = ("IP of the device " +
                   "needs to be specified")
        return True, changed, err_msg

    try:
        otherdev = luna.OtherDev(name=name)
    except RuntimeError:
        args = {
            'name': name,
            'create': True,
            'network': data['connected'][0]['network'],
            'ip': data['connected'][0]['ip'],
        }
        otherdev = luna.OtherDev(**args)
        changed = True

    if (data['comment'] is not None
            and data['comment'] != otherdev.get('comment')):
        otherdev.set('comment', data['comment'])
        changed = True

    ansible_nets = {}
    for elem in data['connected']:
        if elem['network'] in ansible_nets:
            err_msg = ('Network {} specified multiple times'
                       .format(elem[elem['network']]))
            return True, changed, err_msg

        ansible_nets[elem['network']] = elem['ip']

    configured_nets = otherdev.list_nets()

    del_nets = [n for n in configured_nets if n not in ansible_nets]

    for net in del_nets:
        ret &= otherdev.del_net(net)
        changed = True

    for net in ansible_nets:
        ip = ansible_nets[net]
        if otherdev.get_ip(net) != ip:
            ret &= otherdev.set_ip(net, ip)
            changed = True

    return not ret, changed, str(otherdev)


def luna_otherdev_absent(data):
    name = data['name']
    try:
        otherdev = luna.OtherDev(name=name)
    except RuntimeError:
        return False, False, name

    res = otherdev.delete()

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
            'connected': {
                'type': 'list', 'default': None, 'required': False},
            'comment': {
                'type': 'str', 'default': None, 'required': False},
            'state': {
                'type': 'str', 'default': 'present',
                'choices': ['present', 'absent']}
        }
    )

    choice_map = {
        "present": luna_otherdev_present,
        "absent": luna_otherdev_absent,
    }

    is_error, has_changed, result = choice_map.get(
        module.params['state'])(module.params)

    if not is_error:
        module.exit_json(changed=has_changed, msg=str(log_string), meta=result)
    else:
        module.fail_json(changed=has_changed, msg=str(log_string), meta=result)


if __name__ == '__main__':
    main()
