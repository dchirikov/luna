import unittest

import luna
import mock
import getpass
from helper_utils import Sandbox


class AddNetToGroupTests(unittest.TestCase):
    """
    Add network to group with nodes
    """

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

        self.node = luna.Node(
            group=self.group.name,
            mongo_db=self.db,
            create=True,
        )

        self.network = luna.Network(
            name="testnet",
            mongo_db=self.db,
            create=True,
            NETWORK='10.50.0.0',
            PREFIX=16,
        )

        self.network6 = luna.Network(
            name="testnet2",
            mongo_db=self.db,
            create=True,
            NETWORK='fe80::',
            PREFIX=64,
            version=6
        )

    def tearDown(self):
        self.sandbox.cleanup()

    def test_add_net_w_nodes_4(self):

        self.group.set_net_to_if('eth0', self.network.name)

        self.node = luna.Node(name=self.node.name, mongo_db=self.db)
        self.network = luna.Network(name=self.network.name, mongo_db=self.db)

        for key in self.node._json['interfaces']:

            if_dict = self.node._json['interfaces'][key]
            self.assertEqual(
                if_dict,
                {'4': 1, '6': None}
            )

    def test_add_net_w_nodes_6(self):

        self.group.set_net_to_if('eth0', self.network6.name)

        self.node = luna.Node(name=self.node.name, mongo_db=self.db)
        self.network = luna.Network(name=self.network6.name, mongo_db=self.db)

        for key in self.node._json['interfaces']:

            if_dict = self.node._json['interfaces'][key]
            self.assertEqual(
                if_dict,
                {'4': None, '6': 1}
            )

    def test_add_net_group_node_net4_net6(self):

        self.group.set_net_to_if('eth0', self.network.name)
        self.group.set_net_to_if('eth0', self.network6.name)

        self.node = luna.Node(name=self.node.name, mongo_db=self.db)
        self.network = luna.Network(name=self.network6.name, mongo_db=self.db)

        for key in self.node._json['interfaces']:

            if_dict = self.node._json['interfaces'][key]
            self.assertEqual(
                if_dict,
                {'4': 1, '6': 1}
            )

    def test_add_net_group_net4_node_net6(self):
        if self.sandbox.dbtype != 'mongo':
            raise unittest.SkipTest(
                'This test can be run only with MondoDB as a backend.'
            )

        self.node.delete()
        self.group = luna.Group(name=self.group.name, mongo_db=self.db)
        self.group.set_net_to_if('eth0', self.network.name)
        self.node = luna.Node(
            group=self.group.name,
            mongo_db=self.db,
            create=True,
        )

        for key in self.node._json['interfaces']:

            if_dict = self.node._json['interfaces'][key]
            self.assertEqual(
                if_dict,
                {'4': 1, '6': None}
            )

        self.group.set_net_to_if('eth0', self.network6.name)

        self.node = luna.Node(name=self.node.name, mongo_db=self.db)

        for key in self.node._json['interfaces']:

            if_dict = self.node._json['interfaces'][key]
            self.assertEqual(
                if_dict,
                {'4': 1, '6': 1}
            )


class DeleteIPTests(unittest.TestCase):
    """
    Test for delete ip addresses from node
    """

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

        self.node = luna.Node(
            group=self.group.name,
            mongo_db=self.db,
            create=True,
        )

        self.network = luna.Network(
            name="testnet",
            mongo_db=self.db,
            create=True,
            NETWORK='10.50.0.0',
            PREFIX=16,
        )

        self.network6 = luna.Network(
            name="testnet2",
            mongo_db=self.db,
            create=True,
            NETWORK='fe80::',
            PREFIX=64,
            version=6
        )

    def tearDown(self):
        self.sandbox.cleanup()

    def test_node_del_ip_net4(self):

        self.group.set_net_to_if('eth0', self.network.name)

        self.node = luna.Node(name=self.node.name, mongo_db=self.db)

        self.node.del_ip('eth0')

        net_json = self.db['network'].find_one({'_id': self.network._id})

        node_json = self.db['node'].find_one({'_id': self.node._id})

        for if_uuid in node_json['interfaces']:
            if_dict = node_json['interfaces'][if_uuid]
            self.assertEqual(if_dict, {'4': None, '6': None})

        self.assertEqual(net_json['freelist'], [{'start': 1, 'end': 65533L}])

    def test_node_del_ip_net6(self):

        self.group.set_net_to_if('eth0', self.network6.name)

        self.node = luna.Node(name=self.node.name, mongo_db=self.db)

        self.node.del_ip('eth0')

        net_json = self.db['network'].find_one({'_id': self.network6._id})

        node_json = self.db['node'].find_one({'_id': self.node._id})

        for if_uuid in node_json['interfaces']:
            if_dict = node_json['interfaces'][if_uuid]
            self.assertEqual(if_dict, {'4': None, '6': None})

        self.assertEqual(net_json['freelist'],
                         [{'start': '1', 'end': '18446744073709551613'}])

    def test_node_del_ip_mistaken(self):

        self.group.set_net_to_if('eth0', self.network6.name)

        self.node = luna.Node(name=self.node.name, mongo_db=self.db)

        self.node.del_ip('eth0')

        self.assertFalse(self.node.del_ip('eth0'))

    def test_node_del_ip_w_version(self):

        self.group.set_net_to_if('eth0', self.network.name)

        self.node = luna.Node(name=self.node.name, mongo_db=self.db)

        self.assertTrue(self.node.del_ip('eth0', version=4))

        node_json = self.db['node'].find_one({'_id': self.node._id})

        for k in node_json['interfaces']:
            self.assertEqual(node_json['interfaces'][k],
                             {'4': None, '6': None})

    def test_node_del_ip_wrong_version(self):

        self.group.set_net_to_if('eth0', self.network6.name)

        self.node = luna.Node(name=self.node.name, mongo_db=self.db)

        self.assertFalse(self.node.del_ip('eth0', version=4))

        node_json = self.db['node'].find_one({'_id': self.node._id})

        for k in node_json['interfaces']:
            self.assertEqual(node_json['interfaces'][k],
                             {'4': None, '6': 1})

    def test_node_del_ip_both_ver(self):
        self.group.set_net_to_if('eth0', self.network.name)
        self.group.set_net_to_if('eth0', self.network6.name)
        self.node = luna.Node(name=self.node.name, mongo_db=self.db)
        self.assertTrue(self.node.del_ip('eth0', version='all'))
        node_json = self.db['node'].find_one({'_id': self.node._id})

        for k in node_json['interfaces']:
            self.assertEqual(node_json['interfaces'][k],
                             {'4': None, '6': None})

        net_json = self.db['network'].find_one({'_id': self.network._id})
        net6_json = self.db['network'].find_one({'_id': self.network6._id})
        self.assertEqual(net_json['freelist'], [{'start': 1, 'end': 65533}])
        self.assertEqual(net6_json['freelist'],
                         [{'start': '1', 'end': '18446744073709551613'}])


class GetIPTests(unittest.TestCase):
    """
    Test for Node.get_ip
    """

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

        self.node = luna.Node(
            group=self.group.name,
            mongo_db=self.db,
            create=True,
        )

        self.network = luna.Network(
            name="testnet",
            mongo_db=self.db,
            create=True,
            NETWORK='10.50.0.0',
            PREFIX=16,
        )

        self.network6 = luna.Network(
            name="testnet2",
            mongo_db=self.db,
            create=True,
            NETWORK='fe80::',
            PREFIX=64,
            version=6
        )

    def tearDown(self):
        self.sandbox.cleanup()

    def test_get_ip_wrong_ver(self):
        self.assertFalse(self.node.get_ip('eth0', version=5))

    def test_wo_uuid_or_name(self):
        self.assertFalse(self.node.get_ip(version=4))

    def test_wrong_uuid(self):
        self.assertFalse(self.node.get_ip(interface_uuid='wrong-uuid'))

    def test_wrong_name(self):
        self.assertFalse(self.node.get_ip(interface_name='wrong-name'))

    def test_by_uuid_net4(self):
        interface_uuid = None
        for k in self.node._json['interfaces']:
            interface_uuid = k

        self.group.set_net_to_if('eth0', self.network.name)

        self.node = luna.Node(name=self.node.name,
                              mongo_db=self.db)

        self.assertEqual(self.node.get_ip(interface_uuid=interface_uuid),
                         '10.50.0.1')

        self.assertEqual(self.node.get_ip(interface_uuid=interface_uuid,
                                          format='num'),
                         1)

        self.assertEqual(self.node.get_ip(interface_uuid=interface_uuid,
                                          version=4),
                         '10.50.0.1')

    def test_by_name_net6(self):
        self.group.set_net_to_if('eth0', self.network6.name)

        self.node = luna.Node(name=self.node.name,
                              mongo_db=self.db)

        self.assertEqual(self.node.get_ip(interface_name='eth0'),
                         'fe80::1')

        self.assertEqual(self.node.get_ip(interface_name='eth0',
                                          format='num'),
                         1)

        self.assertEqual(self.node.get_ip(interface_name='eth0',
                                          version=6),
                         'fe80::1')

    def test_wrong_version6(self):
        interface_uuid = None
        for k in self.node._json['interfaces']:
            interface_uuid = k

        self.group.set_net_to_if('eth0', self.network.name)

        self.node = luna.Node(name=self.node.name,
                              mongo_db=self.db)

        self.assertFalse(self.node.get_ip(interface_uuid=interface_uuid,
                                          version=6))

    def test_wrong_version4(self):
        self.group.set_net_to_if('eth0', self.network6.name)

        self.node = luna.Node(name=self.node.name,
                              mongo_db=self.db)

        self.assertFalse(self.node.get_ip(interface_name='eth0',
                                          version=4))

    def test_ambiguous_ver(self):
        self.group.set_net_to_if('eth0', self.network.name)
        self.group.set_net_to_if('eth0', self.network6.name)

        self.node = luna.Node(name=self.node.name,
                              mongo_db=self.db)

        self.assertFalse(self.node.get_ip(interface_name='eth0'))

    def test_both_vers_confgured(self):
        self.group.set_net_to_if('eth0', self.network.name)
        self.group.set_net_to_if('eth0', self.network6.name)

        self.node = luna.Node(name=self.node.name,
                              mongo_db=self.db)

        self.assertEqual(self.node.get_ip(interface_name='eth0',
                                          version=6),
                         'fe80::1')

        self.assertEqual(self.node.get_ip(interface_name='eth0',
                                          version=4),
                         '10.50.0.1')


class SetIPTests(unittest.TestCase):
    """
    Test for Node.get_ip
    """

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

        self.node = luna.Node(
            group=self.group.name,
            mongo_db=self.db,
            create=True,
        )

        self.network = luna.Network(
            name="testnet",
            mongo_db=self.db,
            create=True,
            NETWORK='10.50.0.0',
            PREFIX=16,
        )

        self.network6 = luna.Network(
            name="testnet2",
            mongo_db=self.db,
            create=True,
            NETWORK='fe80::',
            PREFIX=64,
            version=6
        )

    def tearDown(self):
        self.sandbox.cleanup()

    def test_get_ip_wrong_name(self):
        self.assertFalse(self.node.set_ip(interface_name='wrong-interface',
                                          ip='10.50.0.2'))

    def test_get_ip_wrong_uuid(self):
        self.assertFalse(self.node.set_ip(interface_uuid='wrong-uuid',
                                          ip='10.50.0.2'))

    def test_get_ip_for_unconfigured_if(self):
        self.assertFalse(self.node.set_ip(interface_name='eth0',
                                          ip='10.50.0.2'))

    def test_set_ip_by_name(self):
        self.group.set_net_to_if('eth0', self.network.name)

        self.node = luna.Node(name=self.node.name,
                              mongo_db=self.db)

        self.assertTrue(self.node.set_ip(interface_name='eth0',
                                         ip='10.50.0.2'))

        self.network = luna.Network(name=self.network.name,
                                    mongo_db=self.db)

        self.assertEqual(
            self.network._json['freelist'],
            [{'start': 1, 'end': 1}, {'start': 3, 'end': 65533}],
        )

    def test_set_ip_by_uuid(self):
        interface_uuid = None
        for k in self.node._json['interfaces']:
            interface_uuid = k

        self.group.set_net_to_if('eth0', self.network.name)

        self.node = luna.Node(name=self.node.name,
                              mongo_db=self.db)

        self.assertTrue(self.node.set_ip(interface_uuid=interface_uuid,
                                         ip='10.50.0.2'))

        self.network = luna.Network(name=self.network.name,
                                    mongo_db=self.db)

        self.assertEqual(
            self.network._json['freelist'],
            [{'start': 1, 'end': 1}, {'start': 3, 'end': 65533}],
        )

    def test_set_both_ips(self):
        self.group.set_net_to_if('eth0', self.network.name)
        self.group.set_net_to_if('eth0', self.network6.name)

        self.node = luna.Node(name=self.node.name,
                              mongo_db=self.db)

        self.assertTrue(self.node.set_ip(interface_name='eth0',
                                         ip='10.50.0.2'))

        self.assertTrue(self.node.set_ip(interface_name='eth0',
                                         ip='fe80::2'))

        self.network = luna.Network(name=self.network.name,
                                    mongo_db=self.db)

        self.network6 = luna.Network(name=self.network6.name,
                                     mongo_db=self.db)

        self.assertEqual(
            self.network._json['freelist'],
            [{'start': 1, 'end': 1}, {'start': 3, 'end': 65533}],
        )

        self.assertEqual(
            self.network6._json['freelist'],
            [{'start': 1, 'end': 1}, {'start': 3, 'end': 18446744073709551613}]
        )

    def test_set_ip_force_wo_net_configured(self):
        self.assertFalse(self.node.set_ip(interface_name='eth0',
                                          ip='10.50.0.2', force=True))

    def test_set_ip_force(self):
        self.group.set_net_to_if('eth0', self.network.name)

        self.node = luna.Node(name=self.node.name,
                              mongo_db=self.db)

        self.assertTrue(self.node.set_ip(interface_name='eth0',
                                         ip='10.50.0.2', force=True))

        self.network = luna.Network(name=self.network.name,
                                    mongo_db=self.db)

        self.assertEqual(
            self.network._json['freelist'],
            [{'start': 3, 'end': 65533}],
        )

    def test_set_wrong_ip(self):
        self.group.set_net_to_if('eth0', self.network.name)

        self.node = luna.Node(name=self.node.name,
                              mongo_db=self.db)

        self.assertFalse(self.node.set_ip(interface_name='eth0',
                                          ip='10.40.0.1'))

        self.network = luna.Network(name=self.network.name,
                                    mongo_db=self.db)

        self.assertEqual(
            self.network._json['freelist'],
            [{'start': 2, 'end': 65533}],
        )

        self.assertEqual(self.node.get_ip(interface_name='eth0'),
                         '10.50.0.1')


class ChangeGroupTests(unittest.TestCase):
    """
    Test for Node.get_ip
    """

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

        self.cluster = luna.Cluster(mongo_db=self.db, create=True,
                                    path=self.path, user=getpass.getuser())

        self.osimage = luna.OsImage(name='testosimage', path=self.path,
                                    mongo_db=self.db, create=True)

        self.group = luna.Group(name='testgroup',
                                osimage=self.osimage.name, mongo_db=self.db,
                                interfaces=['eth0'], create=True)

        self.new_group1 = luna.Group(name='new1', osimage=self.osimage.name,
                                     mongo_db=self.db, interfaces=['eth0'],
                                     create=True)

        self.node = luna.Node(group=self.group.name, mongo_db=self.db,
                              create=True)

        self.network11 = luna.Network(name="net11", mongo_db=self.db,
                                      create=True, NETWORK='10.51.0.0',
                                      PREFIX=16)

        self.network61 = luna.Network(name="net61", mongo_db=self.db,
                                      create=True, NETWORK='fe80::',
                                      PREFIX=64, version=6)

    def tearDown(self):
        self.sandbox.cleanup()

    def test_wo_interfaces_configured(self):

        self.assertTrue(self.node.set_group(self.new_group1.name))

        self.node = luna.Node(name=self.node.name, mongo_db=self.db)

        self.group = luna.Group(name=self.group.name,
                                mongo_db=self.db)

        self.new_group1 = luna.Group(name=self.new_group1.name,
                                     mongo_db=self.db)

        self.assertEqual(self.node._json['group'], self.new_group1.DBRef)

        self.assertEqual(
            self.node._json['_use_']['group'],
            {str(self.new_group1._id): 1}
        )

        group_if_uid = None

        for uuid in self.new_group1._json['interfaces']:
            group_if_uid = uuid

        self.assertEqual(
            self.node._json['interfaces'][group_if_uid],
            {'4': None, '6': None}
        )

        self.assertEqual(self.group._json['_usedby_'], {})

    def test_w_interfaces_configured_in_new_group_net4(self):
        self.node = luna.Node(name=self.node.name, mongo_db=self.db)
        self.new_group1.set_net_to_if('eth0', self.network11.name)

        self.assertTrue(self.node.set_group(self.new_group1.name))

        self.node = luna.Node(name=self.node.name, mongo_db=self.db)

        self.group = luna.Group(name=self.group.name,
                                mongo_db=self.db)

        self.new_group1 = luna.Group(name=self.new_group1.name,
                                     mongo_db=self.db)

        self.network11 = luna.Network(name=self.network11.name,
                                      mongo_db=self.db)

        group_if_uid = None

        for uuid in self.new_group1._json['interfaces']:
            group_if_uid = uuid

        self.assertEqual(
            self.node._json['interfaces'][group_if_uid],
            {'4': 1, '6': None}
        )

        self.assertEqual(
            self.network11._json['freelist'],
            [{'start': 2, 'end': 65533}]
        )

    def test_w_interfaces_configured_in_new_group_net6(self):
        self.node = luna.Node(name=self.node.name, mongo_db=self.db)
        self.new_group1.set_net_to_if('eth0', self.network61.name)

        self.assertTrue(self.node.set_group(self.new_group1.name))

        self.node = luna.Node(name=self.node.name, mongo_db=self.db)

        self.group = luna.Group(name=self.group.name,
                                mongo_db=self.db)

        self.new_group1 = luna.Group(name=self.new_group1.name,
                                     mongo_db=self.db)

        self.network61 = luna.Network(name=self.network61.name,
                                      mongo_db=self.db)

        group_if_uid = None

        for uuid in self.new_group1._json['interfaces']:
            group_if_uid = uuid

        self.assertEqual(
            self.node._json['interfaces'][group_if_uid],
            {'4': None, '6': 1}
        )

        self.assertEqual(
            self.network61._json['freelist'],
            [{'start': 2, 'end': 18446744073709551613}]
        )

    def test_w_interfaces_configured_in_old_group_net4(self):
        self.group.set_net_to_if('eth0', self.network11.name)

        self.node = luna.Node(name=self.node.name, mongo_db=self.db)

        self.assertTrue(self.node.set_group(self.new_group1.name))

        self.node = luna.Node(name=self.node.name, mongo_db=self.db)

        self.group = luna.Group(name=self.group.name,
                                mongo_db=self.db)

        self.new_group1 = luna.Group(name=self.new_group1.name,
                                     mongo_db=self.db)

        self.network11 = luna.Network(name=self.network11.name,
                                      mongo_db=self.db)

        group_if_uid = None

        for uuid in self.new_group1._json['interfaces']:
            group_if_uid = uuid

        self.assertEqual(
            self.node._json['interfaces'][group_if_uid],
            {'4': None, '6': None}
        )

        self.assertEqual(
            self.network11._json['freelist'],
            [{'start': 1, 'end': 65533}]
        )

    def test_w_interfaces_configured_in_both_groups_same_net(self):
        self.group.set_net_to_if('eth0', self.network11.name)
        self.new_group1.set_net_to_if('eth0', self.network11.name)

        self.node = luna.Node(name=self.node.name, mongo_db=self.db)

        self.assertTrue(self.node.set_group(self.new_group1.name))

        self.node = luna.Node(name=self.node.name, mongo_db=self.db)

        self.group = luna.Group(name=self.group.name,
                                mongo_db=self.db)

        self.new_group1 = luna.Group(name=self.new_group1.name,
                                     mongo_db=self.db)

        self.network11 = luna.Network(name=self.network11.name,
                                      mongo_db=self.db)

        group_if_uid = None

        for uuid in self.new_group1._json['interfaces']:
            group_if_uid = uuid

        self.assertEqual(
            self.node._json['interfaces'][group_if_uid],
            {'4': 1, '6': None}
        )

        self.assertEqual(
            self.network11._json['freelist'],
            [{'start': 2, 'end': 65533}]
        )

    def test_w_interfaces_configured_in_both_groups_same_net2(self):
        self.group.set_net_to_if('eth0', self.network11.name)
        self.new_group1.set_net_to_if('eth0', self.network11.name)

        self.node = luna.Node(name=self.node.name, mongo_db=self.db)
        self.node.set_ip(interface_name='eth0', ip='10.51.0.2')

        self.assertTrue(self.node.set_group(self.new_group1.name))

        self.node = luna.Node(name=self.node.name, mongo_db=self.db)

        self.group = luna.Group(name=self.group.name,
                                mongo_db=self.db)

        self.new_group1 = luna.Group(name=self.new_group1.name,
                                     mongo_db=self.db)

        self.network11 = luna.Network(name=self.network11.name,
                                      mongo_db=self.db)

        group_if_uid = None

        for uuid in self.new_group1._json['interfaces']:
            group_if_uid = uuid

        self.assertEqual(
            self.node._json['interfaces'][group_if_uid],
            {'4': 2, '6': None}
        )

        self.assertEqual(
            self.network11._json['freelist'],
            [{'start': 1, 'end': 1}, {'start': 3, 'end': 65533}]
        )

    def test_same_net_different_ifs(self):

        self.new_group2 = luna.Group(name='new2', osimage=self.osimage.name,
                                     mongo_db=self.db, interfaces=['em1'],
                                     create=True)

        self.group.set_net_to_if('eth0', self.network11.name)
        self.new_group2.set_net_to_if('em1', self.network11.name)

        self.node = luna.Node(name=self.node.name, mongo_db=self.db)
        self.node.set_ip(interface_name='eth0', ip='10.51.0.2')

        self.assertTrue(self.node.set_group(self.new_group2.name))

        self.node = luna.Node(name=self.node.name, mongo_db=self.db)

        self.group = luna.Group(name=self.group.name,
                                mongo_db=self.db)

        self.new_group2 = luna.Group(name=self.new_group2.name,
                                     mongo_db=self.db)

        self.network11 = luna.Network(name=self.network11.name,
                                      mongo_db=self.db)

        group_if_uid = None

        for uuid in self.new_group2._json['interfaces']:
            group_if_uid = uuid

        self.assertEqual(
            self.node._json['interfaces'][group_if_uid],
            {'4': 2, '6': None}
        )

        self.assertEqual(
            self.network11._json['freelist'],
            [{'start': 1, 'end': 1}, {'start': 3, 'end': 65533}]
        )

    def test_same_ifs_different_nets(self):

        self.new_group2 = luna.Group(name='new2', osimage=self.osimage.name,
                                     mongo_db=self.db, interfaces=['eth0'],
                                     create=True)

        self.network12 = luna.Network(name="net12", mongo_db=self.db,
                                      create=True, NETWORK='10.52.0.0',
                                      PREFIX=16)

        self.group.set_net_to_if('eth0', self.network11.name)
        self.new_group2.set_net_to_if('eth0', self.network12.name)

        self.node = luna.Node(name=self.node.name, mongo_db=self.db)
        self.node.set_ip(interface_name='eth0', ip='10.51.0.2')

        self.assertTrue(self.node.set_group(self.new_group2.name))

        self.node = luna.Node(name=self.node.name, mongo_db=self.db)

        self.group = luna.Group(name=self.group.name,
                                mongo_db=self.db)

        self.new_group2 = luna.Group(name=self.new_group2.name,
                                     mongo_db=self.db)

        self.network11 = luna.Network(name=self.network11.name,
                                      mongo_db=self.db)

        self.network12 = luna.Network(name=self.network12.name,
                                      mongo_db=self.db)

        group_if_uid = None

        for uuid in self.new_group2._json['interfaces']:
            group_if_uid = uuid

        self.assertEqual(
            self.node._json['interfaces'][group_if_uid],
            {'4': 1, '6': None}
        )

        self.assertEqual(
            self.network11._json['freelist'],
            [{'start': 1, 'end': 65533}]
        )

        self.assertEqual(
            self.network12._json['freelist'],
            [{'start': 2, 'end': 65533}]
        )

    def test_add_del_interface_w_node(self):
        self.group.add_interface('eth1')
        self.group.del_interface('eth1')
        self.node = luna.Node(name=self.node.name, mongo_db=self.db)
        self.assertEqual(len(self.node._json['interfaces']), 1)


class GetMacTests(unittest.TestCase):
    """
    Test for Group.get_macs()
    """

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

        self.cluster = luna.Cluster(mongo_db=self.db, create=True,
                                    path=self.path, user=getpass.getuser())

        self.osimage = luna.OsImage(name='testosimage', path=self.path,
                                    mongo_db=self.db, create=True)

        self.group = luna.Group(name='testgroup',
                                osimage=self.osimage.name, mongo_db=self.db,
                                interfaces=['eth0'], create=True)

        self.network = luna.Network(name="cluster", mongo_db=self.db,
                                    create=True, NETWORK='10.141.0.0',
                                    PREFIX=16)

        self.node = luna.Node(
            group=self.group.name, mongo_db=self.db, create=True)
        self.node.set_mac('00:11:22:33:44:55')

        self.group = luna.Group(name=self.group.name, mongo_db=self.db)

    def tearDown(self):
        self.sandbox.cleanup()

    def test_wo_net_configured(self):
        self.assertEqual(self.group.get_macs(self.network), {})

    def test_wo_nodes(self):
        if self.sandbox.dbtype != 'mongo':
            raise unittest.SkipTest(
                'This test can be run only with MongoDB as a backend.'
            )

        self.group.set_net_to_if('eth0', self.network.name)
        self.node.delete()
        self.group = luna.Group(name=self.group.name, mongo_db=self.db)
        self.assertEqual(self.group.get_macs(self.network), {})

    def test_w_another_net(self):
        net1 = luna.Network(name="net1", mongo_db=self.db,
                            create=True, NETWORK='10.149.0.0',
                            PREFIX=16)

        self.group.set_net_to_if('eth0', net1.name)
        self.assertEqual(self.group.get_macs(self.network), {})

    def test_w_single_interface(self):
        self.group.set_net_to_if('eth0', self.network.name)

    def test_w_BOOTIF_wo_net(self):
        if self.sandbox.dbtype != 'mongo':
            raise unittest.SkipTest(
                'This test can be run only with MongoDB as a backend.'
            )
        self.group.add_interface('BOOTIF')
        self.group.set_net_to_if('eth0', self.network.name)
        self.assertEqual(
            self.group.get_macs(self.network),
            {
                'node001': {
                    'ip': '10.141.0.1',
                    'mac': '00:11:22:33:44:55'
                }
            }

        )

    def test_w_BOOTIF_w_net(self):
        if self.sandbox.dbtype != 'mongo':
            raise unittest.SkipTest(
                'This test can be run only with MongoDB as a backend.'
            )
        self.group.add_interface('BOOTIF')
        self.group.set_net_to_if('eth0', self.network.name)
        self.group.set_net_to_if('BOOTIF', self.network.name)
        self.assertEqual(
            self.group.get_macs(self.network),
            {
                'node001': {
                    'ip': '10.141.0.2',
                    'mac': '00:11:22:33:44:55'
                }
            }

        )

    def test_w_BMC(self):
        self.group.add_interface('BMC')
        self.group.set_net_to_if('BMC', self.network.name)
        self.assertEqual(
            self.group.get_macs(self.network),
            {}
        )

    def test_w_several_prov_ifs(self):
        if self.sandbox.dbtype != 'mongo':
            raise unittest.SkipTest(
                'This test can be run only with MongoDB as a backend.'
            )
        self.group.add_interface('eth1')
        self.group.add_interface('BMC')
        self.group.set_net_to_if('eth1', self.network.name)
        self.group.set_net_to_if('BMC', self.network.name)
        self.group.set_net_to_if('eth0', self.network.name)
        self.assertIn(
            self.group.get_macs(self.network)[self.node.name]['ip'],
            ['10.141.0.1', '10.141.0.2', '10.141.0.3']
        )

    def test_node_wo_mac(self):
        self.group.set_net_to_if('eth0', self.network.name)
        self.node.set_mac('')
        self.assertEqual(
            self.group.get_macs(self.network),
            {}
        )

if __name__ == '__main__':
    unittest.main()
