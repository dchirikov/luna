import unittest

import luna
import copy
import mock
import getpass
import datetime

from helper_utils import Sandbox


class NodeCreateTests(unittest.TestCase):

    @mock.patch('rpm.TransactionSet')
    @mock.patch('rpm.addMacro')
    def setUp(self,
              mock_rpm_addmacro,
              mock_rpm_transactionset,
              ):

        print

        packages = [
            {'VERSION': '3.10', 'RELEASE': '999-el0', 'ARCH': 'x86_64'},
        ]
        mock_rpm_transactionset.return_value.dbMatch.return_value = packages

        self.sandbox = Sandbox()
        self.db = self.sandbox.db
        self.path = self.sandbox.path

        self.cluster = luna.Cluster(
            mongo_db=self.db,
            create=True,
            path=self.path,
            user=getpass.getuser()
        )

        self.osimage = luna.OsImage(
            name='testosimage',
            path=self.path,
            mongo_db=self.db,
            create=True
        )
        self.group = luna.Group(
            name='testgroup',
            osimage=self.osimage.name,
            mongo_db=self.db,
            interfaces=['eth0'],
            create=True,
        )

    def tearDown(self):
        self.sandbox.cleanup()

    def test_create_node_with_defaults(self):

        node = luna.Node(
            group=self.group.name,
            mongo_db=self.db,
            create=True,
        )

        doc = self.db['node'].find_one({'_id': node._id})

        expected = {
            'name': 'node001',
            'localboot': False,
            'setupbmc': True,
            'switch': None,
            'service': False,
            '_use_': {
                'cluster': {str(self.cluster._id): 1},
                'group': {str(self.group._id): 1},
            },
            'group': self.group.DBRef,
            'comment': ''
        }

        if_uuid = None

        for uuid in self.group._json['interfaces']:
            if_uuid = uuid

        expected['interfaces'] = {if_uuid: {'4': None, '6': None}}

        for attr in expected:
            self.assertEqual(doc[attr], expected[attr])

    def test_create_named_node(self):

        node = luna.Node(
            name='n01',
            group=self.group.name,
            mongo_db=self.db,
            create=True,
        )

        doc = self.db['node'].find_one({'_id': node._id})

        expected = {
            'name': 'n01',
        }

        for attr in expected:
            self.assertEqual(doc[attr], expected[attr])

    def test_delete_node(self):
        if self.sandbox.dbtype != 'mongo':
            raise unittest.SkipTest(
                'This test can be run only with MongoDB as a backend.'
            )

        node = luna.Node(
            name='n02',
            group=self.group.name,
            mongo_db=self.db,
            create=True,
        )

        nodeid = node._id
        node.delete()

        doc = self.db['node'].find_one({'_id': nodeid})
        self.assertIsNone(doc)

    def test_create_node_exhausted_ips(self):
        net = luna.Network(
            'net',
            mongo_db=self.db,
            create=True,
            NETWORK='10.50.0.0',
            PREFIX=16,
        )

        tight_net = luna.Network(
            'tight_net',
            mongo_db=self.db,
            create=True,
            NETWORK='10.51.0.0',
            PREFIX=30,
        )

        self.group.add_interface('eth1')

        self.group.set_net_to_if('eth0', net.name)
        self.group.set_net_to_if('eth1', tight_net.name)

        node = luna.Node(
            group=self.group.name,
            mongo_db=self.db,
            create=True,
        )

        with self.assertRaises(RuntimeError):
            luna.Node(
                group=self.group.name,
                mongo_db=self.db,
                create=True,
            )
        tight_net = luna.Network(
                name=tight_net.name, mongo_db=self.db)

        net = luna.Network(
                name=net.name, mongo_db=self.db)

        self.group = luna.Group(
                name=self.group.name, mongo_db=self.db)

        self.assertEqual(tight_net._json['freelist'], [])
        self.assertEqual(net._json['freelist'], [{'start': 2, 'end': 65533}])
        self.assertEqual(len(self.group._json['_usedby_']['node']), 1)


class NodeChangeTests(unittest.TestCase):

    @mock.patch('rpm.TransactionSet')
    @mock.patch('rpm.addMacro')
    def setUp(self,
              mock_rpm_addmacro,
              mock_rpm_transactionset,
              ):

        packages = [
            {'VERSION': '3.10', 'RELEASE': '999-el0', 'ARCH': 'x86_64'},
        ]
        mock_rpm_transactionset.return_value.dbMatch.return_value = packages

        print

        self.sandbox = Sandbox()
        self.db = self.sandbox.db
        self.path = self.sandbox.path

        self.cluster = luna.Cluster(
            mongo_db=self.db,
            create=True,
            path=self.path,
            user=getpass.getuser()
        )
        self.cluster.set('path', self.path)

        self.osimage = luna.OsImage(
            name='testosimage',
            path=self.path,
            mongo_db=self.db,
            create=True
        )

        self.group = luna.Group(
            name='testgroup',
            osimage=self.osimage.name,
            mongo_db=self.db,
            interfaces=['eth0'],
            create=True,
        )

        self.group_new = luna.Group(
            name='testgroup_new',
            osimage=self.osimage.name,
            mongo_db=self.db,
            interfaces=['eth0'],
            create=True,
        )

        self.node = luna.Node(
            group=self.group.name,
            mongo_db=self.db,
            create=True,
        )

    def tearDown(self):
        self.sandbox.cleanup()

    def test_change_group(self):
        start_dict = self.db['node'].find_one({'_id': self.node._id})

        self.node.set_group(self.group_new.name)
        expected_dict = copy.deepcopy(start_dict)
        expected_dict['group'] = self.group_new.DBRef
        expected_dict['_use_']['group'] = {
            u'' + str(self.group_new._id): 1,
        }

        actual_dict = self.db['node'].find_one({'_id': self.node._id})
        if_uuid = None
        for uuid in self.group_new._json['interfaces']:
            if_uuid = uuid
        expected_dict['interfaces'] = {if_uuid: {'4': None, '6': None}}
        self.assertEqual(expected_dict, actual_dict)

        self.node.set_group(self.group.name)

        end_dict = self.db['node'].find_one({'_id': self.node._id})
        self.assertEqual(start_dict, end_dict)

    def test_set_mac(self):
        self.node.set_mac('00:01:02:aa:bb:cc')
        d = self.db['mac'].find({'mac': '00:01:02:aa:bb:cc'})
        self.assertEqual(d.count(), 1)
        for e in d:
            self.assertEqual(self.node.DBRef, e['node'])

    def test_change_mac(self):
        if self.sandbox.dbtype != 'mongo':
            raise unittest.SkipTest(
                'This test can be run only with MongoDB as a backend.'
            )

        self.node.set_mac('00:01:02:aa:bb:cc')
        node2 = luna.Node(
            group=self.group.name,
            mongo_db=self.db,
            create=True,
        )
        node2.set_mac('00:01:02:aa:bb:cc')
        d = self.db['mac'].find({'mac': '00:01:02:aa:bb:cc'})
        self.assertEqual(d.count(), 1)
        for e in d:
            self.assertEqual(node2.DBRef, e['node'])

    def test_clear_mac(self):
        if self.sandbox.dbtype != 'mongo':
            raise unittest.SkipTest(
                'This test can be run only with MongoDB as a backend.'
            )
        self.node.set_mac('00:01:02:aa:bb:cc')
        self.node.set_mac('')
        d = self.db['mac'].find()
        self.assertEqual(d.count(), 0)

    def test_get_mac(self):
        if self.sandbox.dbtype != 'mongo':
            raise unittest.SkipTest(
                'This test can be run only with MongoDB as a backend.'
            )
        mac = '00:01:02:aa:bb:cc'
        self.node.set_mac(mac)
        self.assertEqual(self.node.get_mac(), mac)

    def test_set_switch(self):
        if self.sandbox.dbtype != 'mongo':
            raise unittest.SkipTest(
                'This test can be run only with MongoDB as a backend.'
            )
        net = luna.Network(
            'testnet',
            mongo_db=self.db,
            create=True,
            NETWORK='10.50.0.0',
            PREFIX=16,
        )

        switch = luna.Switch(
            'test1',
            network=net.name,
            mongo_db=self.db,
            create=True,
        )

        self.node.set_switch(switch.name)
        d1 = self.db['node'].find_one({'name': self.node.name})
        d2 = self.db['switch'].find_one({'name': switch.name})
        self.assertEqual(d1['switch'], switch.DBRef)
        self.assertEqual(len(d2['_usedby_']['node']), 1)
        self.assertEqual(d2['_usedby_']['node'][str(self.node._id)], 1)

    def test_change_switch(self):
        if self.sandbox.dbtype != 'mongo':
            raise unittest.SkipTest(
                'This test can be run only with MongoDB as a backend.'
            )
        net = luna.Network(
            'testnet',
            mongo_db=self.db,
            create=True,
            NETWORK='10.50.0.0',
            PREFIX=16,
        )

        switch1 = luna.Switch(
            'test1',
            network=net.name,
            mongo_db=self.db,
            create=True,
        )

        switch2 = luna.Switch(
            'test2',
            network=net.name,
            mongo_db=self.db,
            create=True,
        )

        self.node.set_switch(switch1.name)
        self.node.set_switch(switch2.name)
        d1 = self.db['node'].find_one({'name': self.node.name})
        d2 = self.db['switch'].find_one({'name': switch1.name})
        d3 = self.db['switch'].find_one({'name': switch2.name})
        self.assertEqual(d1['switch'], switch2.DBRef)
        self.assertEqual(len(d2['_usedby_']), 0)
        self.assertEqual(len(d3['_usedby_']['node']), 1)
        self.assertEqual(d1['switch'], switch2.DBRef)

    def test_node_change_group(self):

        # create 3 groups

        group1 = self.group

        group2 = luna.Group(
            name='testgroup2',
            osimage=self.osimage.name,
            mongo_db=self.db,
            interfaces=['eth0'],
            create=True,
        )

        group3 = luna.Group(
            name='testgroup3',
            osimage=self.osimage.name,
            mongo_db=self.db,
            interfaces=['eth1'],
            create=True,
        )

        group4 = luna.Group(
            name='testgroup4',
            osimage=self.osimage.name,
            mongo_db=self.db,
            interfaces=['eth3'],
            create=True,
        )

        # create 3 networks

        net1 = luna.Network(
            'testnet1',
            mongo_db=self.db,
            create=True,
            NETWORK='10.50.0.0',
            PREFIX=16,
        )

        net2 = luna.Network(
            'testnet2',
            mongo_db=self.db,
            create=True,
            NETWORK='10.51.0.0',
            PREFIX=16,
        )

        net3 = luna.Network(
            'testnet3',
            mongo_db=self.db,
            create=True,
            NETWORK='10.52.0.0',
            PREFIX=16,
        )

        # assign 2 networks to interfaces
        # group1: {'eth0': net1}
        # group2  {'eth0': net1, 'em1':  net2}
        # group3  {'em1':  net1, 'eth1': net2}
        # group4  {'eth3': net3}

        group2.add_interface('em1')
        group3.add_interface('em1')

        group1.set_net_to_if('eth0', net1.name)
        group2.set_net_to_if('eth0', net1.name)
        group3.set_net_to_if('eth1', net2.name)
        group4.set_net_to_if('eth3', net3.name)

        group2.set_net_to_if('em1', net2.name)
        group3.set_net_to_if('em1', net1.name)

        self.node = luna.Node(
            name=self.node.name,
            mongo_db=self.db,
        )

        # create 9 more nodes

        nodes = []
        for i in range(10):
            nodes.append(luna.Node(
                group=self.group,
                create=True,
                mongo_db=self.db,
            ))

        # will do tests with node005

        node005 = luna.Node(
            'node005',
            mongo_db=self.db,
            group=self.group
        )

        # check did we get desired config
        node_json = self.db['node'].find_one({'name': node005.name})
        net1_json = self.db['network'].find_one({'name': net1.name})

        self.assertEqual(node_json['group'], group1.DBRef)
        for k in node_json['interfaces']:
            self.assertEqual(node_json['interfaces'][k], {'4': 5, '6': None})
        self.assertEqual(len(net1_json['freelist']), 1)
        self.assertEqual(net1_json['freelist'][0]['start'], 12)
        #node_json['interfaces'], net1_json['freelist']

        #
        # change group first time:
        #
        self.assertEqual(node005.set_group(group2.name), True)
        # updating group objects
        group1 = luna.Group(
            name=group1.name,
            mongo_db=self.db,
        )
        group2 = luna.Group(
            name=group2.name,
            mongo_db=self.db,
        )

        node_json = self.db['node'].find_one({'name': node005.name})
        group2_json = self.db['group'].find_one({'name': group2.name})
        net1_json = self.db['network'].find_one({'name': net1.name})
        net2_json = self.db['network'].find_one({'name': net2.name})

        # should be 2 interfaces now
        self.assertEqual(len(node_json['interfaces']), 2)
        #  those interfaces should be the ones from group2
        for uid in node_json['interfaces']:
            self.assertIn(uid, group2_json['interfaces'].keys())
        # check if eth0 has the same IP adress:
        eth0_uuid = ''
        em1_uuid = ''
        for if_uid in group2_json['interfaces']:
            if group2_json['interfaces'][if_uid]['name'] == 'eth0':
                eth0_uuid = if_uid
            if group2_json['interfaces'][if_uid]['name'] == 'em1':
                em1_uuid = if_uid
        # check if we found
        self.assertIsNot(eth0_uuid, '')
        self.assertIsNot(em1_uuid, '')
        # should be 5
        self.assertEqual(node_json['interfaces'][eth0_uuid], {'4': 5, '6': None})
        # another should be 1
        self.assertEqual(node_json['interfaces'][em1_uuid], {'4': 1, '6': None})

        # check network
        self.assertEqual(net1_json['freelist'], [{'start': 12, 'end': 65533}])
        self.assertEqual(net2_json['freelist'], [{'start': 2, 'end': 65533}])

        #
        # change group second time
        #
        self.assertEqual(node005.set_group(group3.name), True)
        # fetch the data from DB
        node_json = self.db['node'].find_one({'name': node005.name})
        group3_json = self.db['group'].find_one({'name': group3.name})
        net1_json = self.db['network'].find_one({'name': net1.name})
        net2_json = self.db['network'].find_one({'name': net2.name})
        # try to find uuids of the interfaces
        eth1_uuid = ''
        em1_uuid = ''
        for if_uid in group3_json['interfaces']:
            if group3_json['interfaces'][if_uid]['name'] == 'eth1':
                eth1_uuid = if_uid
            if group3_json['interfaces'][if_uid]['name'] == 'em1':
                em1_uuid = if_uid
        # check if we found
        self.assertIsNot(eth1_uuid, '')
        self.assertIsNot(em1_uuid, '')
        # should be 1
        self.assertEqual(node_json['interfaces'][eth1_uuid], {'4': 1, '6': None})
        # another should be 5
        self.assertEqual(node_json['interfaces'][em1_uuid], {'4': 5, '6': None})

        #
        # change group third time
        #
        self.assertEqual(node005.set_group(group4.name), True)
        node_json = self.db['node'].find_one({'name': node005.name})
        net1_json = self.db['network'].find_one({'name': net1.name})
        net2_json = self.db['network'].find_one({'name': net2.name})
        net3_json = self.db['network'].find_one({'name': net3.name})
        self.assertEqual(
            net1_json['freelist'],
            [{'start': 5, u'end': 5}, {'start': 12, 'end': 65533}]
        )
        self.assertEqual(
            net2_json['freelist'],
            [{'start': 1, 'end': 65533}]
        )
        self.assertEqual(
            net3_json['freelist'],
            [{'start': 2, 'end': 65533}]
        )

    def test_update_status(self):
        self.assertIsNone(self.node.update_status())
        self.assertIsNone(self.node.update_status('#$#%'))
        self.assertTrue(self.node.update_status('status1'))

        doc = self.db['node'].find_one({'_id': self.node._id})

        self.assertEqual(doc['status']['step'], 'status1')
        self.assertEqual(
            type(doc['status']['time']),
            datetime.datetime
        )

    def test_get_status(self):
        self.assertIsNone(self.node.get_status())
        self.assertTrue(self.node.update_status('status1'))

        self.assertEqual(self.node.get_status()['status'], 'status1')
        self.assertTrue(self.node.get_status()['time'])

        self.assertEqual(
            self.node.get_status(relative=False)['status'],
            'status1',
        )

        self.assertTrue(
            self.node.get_status(relative=False)['time']
        )

    def test_get_status_tracker(self):
        name = "%20s" % self.node.name
        peerid = ''.join(["{:02x}".format(ord(l)) for l in name])
        self.assertTrue(self.node.update_status('install.download'))
        now = datetime.datetime.today()
        doc2insert = {
            'peer_id': peerid,
            'updated': now,
            'downloaded': 2,
            'left': 1
        }
        self.db['tracker'].insert(doc2insert)
        self.assertEqual(
            self.node.get_status()['status'][:39],
            'install.download (66.67% / last update '
        )


class NodeBootInstallTests(unittest.TestCase):

    @mock.patch('rpm.TransactionSet')
    @mock.patch('rpm.addMacro')
    def setUp(self,
              mock_rpm_addmacro,
              mock_rpm_transactionset,
              ):

        print

        packages = [
            {'VERSION': '3.10', 'RELEASE': '999-el0', 'ARCH': 'x86_64'},
        ]
        mock_rpm_addmacro.return_value = True
        mock_rpm_transactionset.return_value.dbMatch.return_value = packages

        self.sandbox = Sandbox()
        self.db = self.sandbox.db
        self.path = self.sandbox.path

        self.cluster = luna.Cluster(
            mongo_db=self.db,
            create=True,
            path=self.path,
            user=getpass.getuser()
        )
        self.cluster.set('path', self.path)
        self.cluster.set('frontend_address', '127.0.0.1')

        self.osimage = luna.OsImage(
            name='testosimage',
            path=self.path,
            mongo_db=self.db,
            create=True
        )

        self.net1 = luna.Network(
            'testnet1',
            mongo_db=self.db,
            create=True,
            NETWORK='10.50.0.0',
            PREFIX=16,
        )

        self.net2 = luna.Network(
            'testnet2',
            mongo_db=self.db,
            create=True,
            NETWORK='10.51.0.0',
            PREFIX=16,
        )

        self.group = luna.Group(
            name='testgroup',
            osimage=self.osimage.name,
            mongo_db=self.db,
            interfaces=['eth0'],
            create=True,
        )

        self.group_new = luna.Group(
            name='testgroup_new',
            osimage=self.osimage.name,
            mongo_db=self.db,
            interfaces=['eth0'],
            create=True,
        )

        self.node = luna.Node(
            group=self.group.name,
            mongo_db=self.db,
            create=True,
        )

        self.boot_expected_dict = {
            'domain': '',
            'initrd_file': '',
            'mac': '',
            'kernel_file': '',
            'localboot': 0,
            'name': 'node001',
            'service': 0,
            'net': {},
            'hostname': 'node001',
            'kern_opts': '',
            'bootproto': 'dhcp'
        }

        self.install_expected_dict = {
            'torrent_if': '',
            'setupbmc': True,
            'partscript': 'mount -t tmpfs tmpfs /sysroot',
            'name': 'node001',
            'tarball': '',
            'bmcsetup': {},
            'interfaces': {
                'BOOTIF': {
                    'options': '',
                    '4': {
                        'ip': '',
                        'netmask': '',
                        'prefix': '',
                    },
                    '6': {
                        'ip': '',
                        'netmask': '',
                        'prefix': '',
                    }
                },
                'eth0': {
                    'options': '',
                    '4': {
                        'ip': '',
                        'netmask': '',
                        'prefix': '',
                    },
                    '6': {
                        'ip': '',
                        'netmask': '',
                        'prefix': '',
                    }
                }
            },
            'prescript': '',
            'domain': '',
            'hostname': 'node001',
            'postscript': (
                'cat << EOF >> /sysroot/etc/fstab\n'
                + 'tmpfs   /       tmpfs    defaults        0 0\n'
                + 'EOF'
            ),
            'kernopts': '',
            'kernver': '3.10-999-el0.x86_64',
            'torrent': '',
            'mac': '',
        }


    def tearDown(self):
        self.sandbox.cleanup()

    def test_boot_params_default(self):

        self.assertEqual(
            self.node.boot_params,
            self.boot_expected_dict,
        )

    def test_boot_params_w_net_and_mac_assigned(self):
        if self.sandbox.dbtype != 'mongo':
            raise unittest.SkipTest(
                'This test can be run only with MongoDB as a backend.'
            )

        mac = '00:11:22:33:44:55'
        self.group.set_net_to_if('eth0', self.net1.name)
        self.group.add_interface('BOOTIF')
        self.group.set_net_to_if('BOOTIF', self.net2.name)
        self.node.set_mac(mac)

        self.node = luna.Node(
            name=self.node.name,
            mongo_db=self.db,
        )

        self.boot_expected_dict['bootproto'] = 'static'
        self.boot_expected_dict['mac'] = mac
        self.boot_expected_dict['net']['4'] = {}
        self.boot_expected_dict['net']['4']['prefix'] = '16'
        self.boot_expected_dict['net']['4']['mask'] = '255.255.0.0'
        self.boot_expected_dict['net']['4']['ip'] = '10.51.0.1'

        self.assertEqual(
            self.node.boot_params,
            self.boot_expected_dict,
        )

    def test_boot_params_w_bootif_wo_net(self):

        self.group.add_interface('BOOTIF')

        self.node = luna.Node(
            name=self.node.name,
            mongo_db=self.db,
        )

        self.assertEqual(
            self.node.boot_params,
            self.boot_expected_dict,
        )

    def test_boot_params_w_net_wo_mac_assigned(self):

        self.group.set_net_to_if('eth0', self.net1.name)
        self.group.add_interface('BOOTIF')
        self.group.set_net_to_if('BOOTIF', self.net2.name)

        self.node = luna.Node(
            name=self.node.name,
            mongo_db=self.db,
        )

        self.assertEqual(
            self.node.boot_params,
            self.boot_expected_dict,
        )

    def test_install_params_default(self):

        self.install_expected_dict['interfaces'].pop('BOOTIF')

        self.assertEqual(
            self.node.install_params,
            self.install_expected_dict,
        )

    def test_install_params_w_nets(self):

        self.group.set_net_to_if('eth0', self.net1.name)
        self.group.add_interface('BOOTIF')
        self.group.set_net_to_if('BOOTIF', self.net2.name)

        self.node = luna.Node(
            name=self.node.name,
            mongo_db=self.db,
        )

        self.install_expected_dict['interfaces']['BOOTIF']['4'] = {
            'ip': '10.51.0.1',
            'netmask': '255.255.0.0',
            'prefix': '16',
        }
        self.install_expected_dict['interfaces']['eth0']['4'] = {
            'ip': '10.50.0.1',
            'netmask': '255.255.0.0',
            'prefix': '16',
        }

        self.assertEqual(
            self.node.install_params,
            self.install_expected_dict,
        )

    def test_install_params_w_bmc(self):

        self.maxDiff = None

        bmcsetup = luna.BMCSetup(
            name='bmcsetup1',
            mongo_db=self.db,
            create=True,
        )

        self.install_expected_dict['interfaces'].pop('BOOTIF')

        self.group.bmcsetup(bmcsetup.name)

        self.install_expected_dict['bmcsetup'] = {
            'netchannel': 1,
            'mgmtchannel': 1,
            'userid': 3,
            'user': 'ladmin',
            'password': 'ladmin'
        }

        self.node = luna.Node(
            name=self.node.name,
            mongo_db=self.db,
        )

        self.assertEqual(
            self.node.install_params,
            self.install_expected_dict,
        )

    def test_install_scripts(self):
        self.assertIsNone(self.node.render_script('non_exist'))
        self.assertEqual(self.node.render_script('boot').split()[0], '#!ipxe')
        self.assertEqual(
            self.node.render_script('install').split()[0],
            '#!/bin/bash'
        )

if __name__ == '__main__':
    unittest.main()
