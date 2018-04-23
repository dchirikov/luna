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


def luna_switch_present(data):
    data.pop('state')
    name = data.pop('name')
    changed = False
    ret = True

    try:
        switch = luna.Switch(name=name)
    except RuntimeError:
        if data['network'] is None:
            err_msg = "Network needs to be specified"
            return True, changed, err_msg
        if data['ip'] is None:
            err_msg = "IP address needs to be specified"
            return True, changed, err_msg
        args = {}
        for key in data:
            if data[key] is not None:
                args[key] = data[key]
        args['name'] = name
        args['create'] = True
        switch = luna.Switch(**args)
        changed = True

    # we need to check keys in particular order
    # can't change ip before network
    keys = ['read', 'rw', 'oid', 'comment', 'network', 'ip']
    for key in keys:
        if data[key] is not None and switch.get(key) != data[key]:
            changed = True
            ret &= switch.set(key, data[key])

    return not ret, changed, str(switch)


def luna_switch_absent(data):
    name = data['name']
    try:
        switch = luna.Switch(name=name)
    except RuntimeError:
        return False, False, name

    res = switch.delete()

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
            'network': {
                'type': 'str', 'default': None, 'required': False},
            'ip': {
                'type': 'str', 'default': None, 'required': False},
            'read': {
                'type': 'str', 'default': None, 'required': False},
            'rw': {
                'type': 'str', 'default': None, 'required': False},
            'oid': {
                'type': 'str', 'default': '.1.3.6.1.2.1.17.7.1.2.2.1.2',
                'required': False},
            'comment': {
                'type': 'str', 'default': None, 'required': False},
            'state': {
                'type': 'str', 'default': 'present',
                'choices': ['present', 'absent']}
        }
    )

    choice_map = {
        "present": luna_switch_present,
        "absent": luna_switch_absent,
    }

    is_error, has_changed, result = choice_map.get(
        module.params['state'])(module.params)

    if not is_error:
        module.exit_json(changed=has_changed, msg=str(log_string), meta=result)
    else:
        module.fail_json(changed=has_changed, msg=str(log_string), meta=result)


if __name__ == '__main__':
    main()
