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


def luna_osimage_present(data):

    changed = False
    ret = True

    try:
        osimage = luna.OsImage(name=data['name'])
    except RuntimeError:
        try:
            osimage = luna.OsImage(
                name=data['name'],
                create=True,
                path=data['path'],
                kernver=data['kernver'],
                kernopts=data['kernopts'],
                comment=data['comment'])
            changed = True
        except RuntimeError:
            return True, False, 'Unable to create image'


    for key in ['path', 'kernver', 'kernopts',
                'dracutmodules', 'kernmodules', 'grab_exclude_list',
                'grab_filesystems']:
        if data[key] and data[key] != osimage.get(key):
            ret &= osimage.set(key, data[key])
            changed = True

    if data['comment'] != osimage.get('comment'):
        ret &= osimage.set('comment', data['comment'])
        changed = True

    if data['pack']:
        changed = True
        if data['copy_boot']:
            ret &= osimage.copy_boot()
        else:
            ret &= osimage.pack_boot()
        ret &= osimage.create_tarball()
        ret &= osimage.create_torrent()

    return not ret, changed, osimage.get('name')


def luna_osimage_absent(data):
    name = data['name']

    try:
        osimage = luna.OsImage(name)
    except RuntimeError:
        return False, False, name

    res = osimage.delete()

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

            'path': {
                'type': 'str', 'required': False},

            'kernver': {
                'type': 'str', 'default': '', 'required': False},

            'kernopts': {
                'type': 'str', 'default': '', 'required': False},

            'comment': {
                'type': 'str', 'default': '', 'required': False},

            'dracutmodules': {
                'type': 'str', 'default': '', 'required': False},

            'kernmodules': {
                'type': 'str', 'default': '', 'required': False},

            'grab_exclude_list': {
                'type': 'str', 'default': '', 'required': False},

            'grab_filesystems': {
                'type': 'str', 'default': '', 'required': False},

            'pack': {
                'type': 'bool', 'default': False, 'required': False},

            'copy_boot': {
                'type': 'bool', 'default': False, 'required': False},

            'state': {
                'type': 'str', 'default': 'present',
                'choices': ['present', 'absent']}
        }
    )

    choice_map = {
        "present": luna_osimage_present,
        "absent": luna_osimage_absent,
    }

    is_error, has_changed, result = choice_map.get(
        module.params['state'])(module.params)

    if not is_error:
        module.exit_json(changed=has_changed, msg=str(log_string), meta=result)
    else:
        module.fail_json(changed=has_changed, msg=str(log_string), meta=result)


if __name__ == '__main__':
    main()
