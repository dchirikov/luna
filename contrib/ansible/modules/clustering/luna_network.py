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


def luna_network_present(data):
        name = data['name']
        network = data['network']
        prefix = data['prefix']
        ns_hostname = data['ns_hostname']
        ns_ip = data['ns_ip']

        changed = False
        try:
            net = luna.Network(name=name)
        except RuntimeError:
            net = luna.Network(
                name=name, create=True, NETWORK=network, PREFIX=prefix)
                #ns_hostname=ns_hostname, ns_ip=ns_ip)
            changed = True

        version = luna.utils.ip.get_ip_version(network)
        res = True

        if ns_hostname and (ns_hostname != net.get('ns_hostname')):
            changed = True
            res &= net.set('ns_hostname', ns_hostname)

        for key in ['comment', 'include', 'rev_include']:
            if data[key] != net.get(key):
                changed = True
                res &= net.set(key, data[key])

        if ns_ip and (ns_ip != net.get('ns_ip')):
            changed = True
            res &= net.set('ns_ip', ns_ip)

        if luna.utils.ip.ntoa(
                luna.utils.ip.get_num_subnet(network, prefix, version),
                version) != net.get('NETWORK'):
            changed = True
            res &= net.set('NETWORK', network)

        if prefix != net.get('PREFIX'):
            changed = True
            res &= net.set('PREFIX', prefix)

        return False, changed, str(net)


def luna_network_absent(data):
    name = data['name']

    try:
        net = luna.Network(name)
    except RuntimeError:
        return False, False, name

    res = net.delete()

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
                'type': 'str', 'required': False},

            'prefix': {
                'type': 'int', 'required': False},

            'ns_hostname': {
                'type': 'str', 'default': None, 'required': False},

            'ns_ip': {
                'type': 'str', 'default': None, 'required': False},

            'comment': {
                'type': 'str', 'default': '', 'required': False},

            'include': {
                'type': 'str', 'default': '', 'required': False},

            'rev_include': {
                'type': 'str', 'default': '', 'required': False},

            'state': {
                'type': 'str', 'default': 'present',
                'choices': ['present', 'absent']}
        }
    )

    choice_map = {
        "present": luna_network_present,
        "absent": luna_network_absent,
    }

    is_error, has_changed, result = choice_map.get(
        module.params['state'])(module.params)

    if not is_error:
        module.exit_json(changed=has_changed, msg=str(log_string), meta=result)
    else:
        module.fail_json(changed=has_changed, msg=str(log_string), meta=result)


if __name__ == '__main__':
    main()
