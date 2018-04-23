import unittest

import luna
import mock
import getpass
from helper_utils import Sandbox


class NetworkCreateTests(unittest.TestCase):

    def setUp(self):

        print

        self.sandbox = Sandbox()
        self.db = self.sandbox.db
        self.path = self.sandbox.path

        self.cluster = luna.Cluster(mongo_db=self.db, create=True,
                                    path=self.path, user=getpass.getuser())

    def tearDown(self):
        self.sandbox.cleanup()

    def test_create_network_with_defaults(self):
        net = luna.Network(name='testnet', mongo_db=self.db, create=True,
                           NETWORK='172.16.1.0', PREFIX=24)
        self.assertIsInstance(net, luna.Network)

    def test_create_duplicate_network(self):
        net = luna.Network(name='testnet', mongo_db=self.db, create=True,
                           NETWORK='172.16.1.0', PREFIX=24)
        self.assertRaises(
            RuntimeError,
            luna.Network, name='testnet2', mongo_db=self.db, create=True,
            NETWORK='172.16.1.1', PREFIX=24
        )

    def test_create_network_ipv6(self):
        net = luna.Network(name='testnet', mongo_db=self.db, create=True,
                           NETWORK='fd12:3456:789a:1::1', PREFIX='64',
                           version=6)
        self.assertIsInstance(net, luna.Network)

    def test_create_duplicate_network_ipv6(self):
        net = luna.Network(name='testnet', mongo_db=self.db, create=True,
                           NETWORK='fd12:3456:789a:1::1', PREFIX='64',
                           version=6)
        self.assertRaises(
            RuntimeError,
            luna.Network, name='testnet2', mongo_db=self.db, create=True,
            NETWORK='fd12:3456:789a:1::2', PREFIX=64
        )

    def test_create_network_check(self):
        net = luna.Network(name='testnet', mongo_db=self.db, create=True,
                           NETWORK='172.16.1.0', PREFIX=24)
        net = luna.Network(name='testnet', mongo_db=self.db)

        self.assertIsInstance(net, luna.Network)
        self.assertEqual(net.maxbits, 32)
        self.assertEqual(net.version, 4)
        expected_dict = {
            'name': 'testnet',
            'freelist': [{u'start': 1, u'end': 253L}],
            'ns_ip': 254,
            'PREFIX': 24,
            '_usedby_': {},
            'version': 4,
            'NETWORK': 2886729984L}
        doc = self.db['network'].find_one({'name': net.name})
        for key in expected_dict.keys():
            self.assertEqual(doc[key], expected_dict[key])

    def test_create_network_check_ipv6(self):
        net = luna.Network(name='testnet', mongo_db=self.db, create=True,
                           NETWORK='fd12:3456:789a:1::1', PREFIX=64,
                           version=6)
        net = luna.Network(name='testnet', mongo_db=self.db)

        self.assertIsInstance(net, luna.Network)
        self.assertEqual(net.maxbits, 128)
        self.assertEqual(net.version, 6)
        expected_dict = {
            'name': 'testnet',
            'freelist': [{'start': '1', 'end': '18446744073709551613'}],
            'ns_ip': '18446744073709551614',
            'PREFIX': 64,
            '_usedby_': {},
            'version': 6,
            'NETWORK': '336389205813283084628800618700287770624'}
        doc = self.db['network'].find_one({'name': net.name})
        for key in expected_dict.keys():
            self.assertEqual(doc[key], expected_dict[key])


class NetworkReadTests(unittest.TestCase):

    def setUp(self):

        print

        self.sandbox = Sandbox()
        self.db = self.sandbox.db
        self.path = self.sandbox.path

        self.cluster = luna.Cluster(mongo_db=self.db, create=True,
                                    path=self.path, user=getpass.getuser())

    def tearDown(self):
        self.sandbox.cleanup()

    def test_read_non_existing_network(self):
        self.assertRaises(RuntimeError, luna.Network, mongo_db=self.db)

    def test_read_network(self):
        luna.Network(name='testnet', mongo_db=self.db, create=True,
                     NETWORK='172.16.1.0', PREFIX='24')
        net = luna.Network(name='testnet', mongo_db=self.db)
        self.assertIsInstance(net, luna.Network)


class NetworkAttributesTests(unittest.TestCase):

    def setUp(self):

        print

        self.sandbox = Sandbox()
        self.db = self.sandbox.db
        self.path = self.sandbox.path

        self.cluster = luna.Cluster(mongo_db=self.db, create=True,
                                    path=self.path, user=getpass.getuser())

        self.net = luna.Network(name='test', mongo_db=self.db, create=True,
                                NETWORK='172.16.1.0', PREFIX='24',
                                ns_hostname='controller',
                                ns_ip='172.16.1.254')

    def tearDown(self):
        self.sandbox.cleanup()

    def test_get_network(self):
        self.assertEqual(self.net.get('NETWORK'), '172.16.1.0')

    def test_get_netmask(self):
        self.assertEqual(self.net.get('NETMASK'), '255.255.255.0')

    def test_get_PREFIX(self):
        self.assertEqual(self.net.get('PREFIX'), '24')

    def test_get_ns_ip(self):
        self.assertEqual(self.net.get('ns_ip'), '172.16.1.254')

    def test_change_ns_ip(self):
        json = self.net._json
        self.assertEqual(json['ns_ip'], 254)
        self.assertEqual(
            json['freelist'],
            [{'start': 1, 'end': 253}]
        )
        self.assertTrue(self.net.set('ns_ip', '172.16.1.253'))
        self.assertEqual(json['ns_ip'], 253)
        self.assertEqual(
            json['freelist'],
            [{'start': 1, 'end': 252}, {'start': 254, 'end': 254}]
        )

    def test_get_other_key(self):
        self.assertEqual(self.net.get('name'), 'test')

    def test_reserve_ip(self):
        self.net.reserve_ip('172.16.1.3')
        net = self.net._json
        self.assertEqual(net['freelist'], [{'start': 1, 'end': 2},
                                           {'start': 4, 'end': 253}])

    def test_reserve_ip_range(self):
        self.net.reserve_ip('172.16.1.4', '172.16.1.6')
        net = self.net._json
        self.assertEqual(net['freelist'], [{'start': 1, 'end': 3},
                                           {'start': 7, 'end': 253}])

    def test_release_ip(self):
        self.net.release_ip('172.16.1.254')
        net = self.net._json
        self.assertEqual(net['freelist'], [{'start': 1, 'end': 254}])

    def test_release_ip_range(self):
        self.net.release_ip('172.16.1.250', '172.16.1.254')
        net = self.net._json
        self.assertEqual(net['freelist'], [{'start': 1, 'end': 254}])


class NetworkAttributesTestsIPv6(unittest.TestCase):

    def setUp(self):

        print

        self.sandbox = Sandbox()
        self.db = self.sandbox.db
        self.path = self.sandbox.path

        self.cluster = luna.Cluster(mongo_db=self.db, create=True,
                                    path=self.path, user=getpass.getuser())

        self.net = luna.Network(name='test', mongo_db=self.db, create=True,
                                NETWORK='fdee:172:30:128::', PREFIX=64,
                                ns_hostname='controller',
                                ns_ip='fdee:172:30:128::254:254',
                                version=6)

    def tearDown(self):
        self.sandbox.cleanup()

    def test_get_network(self):
        self.assertEqual(self.net.get('NETWORK'), 'fdee:172:30:128::')

    def test_get_netmask(self):
        self.assertEqual(self.net.get('NETMASK'), 'ffff:ffff:ffff:ffff::')

    def test_get_PREFIX(self):
        self.assertEqual(self.net.get('PREFIX'), 64)

    def test_get_ns_ip(self):
        self.assertEqual(self.net.get('ns_ip'), 'fdee:172:30:128::254:254')

    def test_change_ns_ip(self):
        json = self.net._json
        self.assertEqual(json['ns_ip'], 39060052)
        self.assertEqual(
            json['freelist'],
            [
                {'start': 1, 'end': 39060051},
                {'start': 39060053, 'end': 18446744073709551614}
            ]
        )

        self.assertTrue(self.net.set('ns_ip', 'fdee:172:30:128::254:253'))
        self.assertEqual(json['ns_ip'], 39060051)
        self.assertEqual(
            json['freelist'],
            [
                {'start': 1, 'end': 39060050},
                {'start': 39060052, 'end': 18446744073709551614}
            ]
        )

    def test_get_other_key(self):
        self.assertEqual(self.net.get('name'), 'test')

    def test_reserve_ip(self):
        self.net.reserve_ip('fdee:172:30:128::253:254')
        net = self.net._json
        expected_freelist = [
            {'start': 1, 'end': 38994515},
            {'start': 38994517, 'end': 39060051},
            {'start': 39060053, 'end': 18446744073709551614}
        ]
        self.assertEqual(net['freelist'], expected_freelist)

    def test_reserve_ip_range(self):
        self.net.reserve_ip('fdee:172:30:128::1:4', 'fdee:172:30:128::1:6')
        net = self.net._json
        self.assertEqual(net['freelist'],
                         [{'end': 65539, 'start': 1},
                          {'start': 65543, 'end': 39060051},
                          {'start': 39060053, 'end': 18446744073709551614}]
                         )

    def test_release_ip(self):
        self.net.release_ip('fdee:172:30:128::254:254')
        net = self.net._json
        self.assertEqual(net['freelist'],
                         [{'start': 1, 'end': 18446744073709551614}])

    def test_release_ip_range(self):
        self.net.reserve_ip('fdee:172:30:128::1:4', 'fdee:172:30:128::1:6')
        self.net.release_ip('fdee:172:30:128::1:4', 'fdee:172:30:128::1:6')
        net = self.net._json
        self.assertEqual(net['freelist'],
                         [{'start': 1, 'end': 39060051},
                          {'start': 39060053, 'end': 18446744073709551614}]
                         )

    def test_change_PREFIX(self):
        self.assertTrue(self.net.set('PREFIX', 32))


class ZoneDataIPv4(unittest.TestCase):

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
        self.cluster.set('path', self.path)
        self.cluster.set('frontend_address', '127.0.0.1')

        self.osimage = luna.OsImage(
            name='testosimage',
            path=self.path,
            mongo_db=self.db,
            create=True
        )

        self.net = luna.Network(
            'testnet',
            mongo_db=self.db,
            create=True,
            NETWORK='10.50.0.0',
            PREFIX=16,
        )

        self.net.set('ns_hostname', 'master')

        self.group = luna.Group(
            name='testgroup',
            osimage=self.osimage.name,
            mongo_db=self.db,
            interfaces=['eth0'],
            create=True,
        )

        self.group.set_net_to_if('eth0', self.net.name)

        self.nodes = []
        for i in range(10):
            self.nodes.append(luna.Node(
                group=self.group,
                create=True,
                mongo_db=self.db,
            ))

        self.net = luna.Network(name=self.net.name, mongo_db=self.db)

    def tearDown(self):
        self.sandbox.cleanup()

    def test_zone_data_simple(self):
        expected_dict = {
            'ns_hostname': 'master',
            'ns_ip': '10.50.255.254',
            'zone_name': 'testnet',
            'version': 4,
            'include': '',
            'rev_include': '',
            'hosts': {
                'node001': '10.50.0.1',
                'node002': '10.50.0.2',
                'node003': '10.50.0.3',
                'node004': '10.50.0.4',
                'node005': '10.50.0.5',
                'node006': '10.50.0.6',
                'node007': '10.50.0.7',
                'node008': '10.50.0.8',
                'node009': '10.50.0.9',
                'node010': '10.50.0.10',
                'master':  '10.50.255.254',
            },
            'rev_zone_name': '50.10',
            'rev_hosts': {
                '1.0': 'node001.testnet.',
                '2.0': 'node002.testnet.',
                '3.0': 'node003.testnet.',
                '4.0': 'node004.testnet.',
                '5.0': 'node005.testnet.',
                '6.0': 'node006.testnet.',
                '7.0': 'node007.testnet.',
                '8.0': 'node008.testnet.',
                '9.0': 'node009.testnet.',
                '10.0': 'node010.testnet.',
                '254.255': 'master.testnet.',
            },
        }
        self.assertEqual(self.net.zone_data, expected_dict)

    def test_zone_data_prefix19(self):
        self.net.set('ns_ip', '10.50.2.254')
        self.net.set('PREFIX', 19)
        self.net.set('NETWORK', '10.50.32.0')
        expected_dict = {
            'ns_hostname': 'master',
            'ns_ip': '10.50.34.254',
            'zone_name': 'testnet',
            'version': 4,
            'include': '',
            'rev_include': '',
            'hosts': {
                'node001': '10.50.32.1',
                'node002': '10.50.32.2',
                'node003': '10.50.32.3',
                'node004': '10.50.32.4',
                'node005': '10.50.32.5',
                'node006': '10.50.32.6',
                'node007': '10.50.32.7',
                'node008': '10.50.32.8',
                'node009': '10.50.32.9',
                'node010': '10.50.32.10',
                'master':  '10.50.34.254',
            },
            'rev_zone_name': '50.10',
            'rev_hosts': {
                '1.32': 'node001.testnet.',
                '2.32': 'node002.testnet.',
                '3.32': 'node003.testnet.',
                '4.32': 'node004.testnet.',
                '5.32': 'node005.testnet.',
                '6.32': 'node006.testnet.',
                '7.32': 'node007.testnet.',
                '8.32': 'node008.testnet.',
                '9.32': 'node009.testnet.',
                '10.32': 'node010.testnet.',
                '254.34': 'master.testnet.',
            },
        }
        self.assertEqual(self.net.zone_data, expected_dict)

    def test_zone_data_prefix19_2(self):
        self.net.set('ns_ip', '10.50.0.254')
        self.net.set('PREFIX', 19)
        self.net.set('NETWORK', '10.50.32.0')
        expected_dict = {
            'ns_hostname': 'master',
            'ns_ip': '10.50.32.254',
            'zone_name': 'testnet',
            'version': 4,
            'include': '',
            'rev_include': '',
            'hosts': {
                'node001': '10.50.32.1',
                'node002': '10.50.32.2',
                'node003': '10.50.32.3',
                'node004': '10.50.32.4',
                'node005': '10.50.32.5',
                'node006': '10.50.32.6',
                'node007': '10.50.32.7',
                'node008': '10.50.32.8',
                'node009': '10.50.32.9',
                'node010': '10.50.32.10',
                'master':  '10.50.32.254',
            },
            'rev_zone_name': '50.10',
            'rev_hosts': {
                '1.32': 'node001.testnet.',
                '2.32': 'node002.testnet.',
                '3.32': 'node003.testnet.',
                '4.32': 'node004.testnet.',
                '5.32': 'node005.testnet.',
                '6.32': 'node006.testnet.',
                '7.32': 'node007.testnet.',
                '8.32': 'node008.testnet.',
                '9.32': 'node009.testnet.',
                '10.32': 'node010.testnet.',
                '254.32': 'master.testnet.',
            },
        }
        self.assertEqual(self.net.zone_data, expected_dict)


class ZoneDataIPv6(unittest.TestCase):

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
        self.cluster.set('path', self.path)
        self.cluster.set('frontend_address', '127.0.0.1')

        self.osimage = luna.OsImage(
            name='testosimage',
            path=self.path,
            mongo_db=self.db,
            create=True
        )

        self.net = luna.Network(
            'testnet',
            mongo_db=self.db,
            create=True,
            NETWORK='fe80::',
            PREFIX=64,
        )

        self.net.set('ns_hostname', 'master')

        self.group = luna.Group(
            name='testgroup',
            osimage=self.osimage.name,
            mongo_db=self.db,
            interfaces=['eth0'],
            create=True,
        )

        self.group.set_net_to_if('eth0', self.net.name)

        self.nodes = []
        for i in range(10):
            self.nodes.append(luna.Node(
                group=self.group,
                create=True,
                mongo_db=self.db,
            ))

        self.net = luna.Network(name=self.net.name, mongo_db=self.db)

    def tearDown(self):
        self.sandbox.cleanup()

    def test_zone_data_simple(self):
        expected_dict = {
            'ns_hostname': 'master',
            'ns_ip': 'fe80::ffff:ffff:ffff:fffe',
            'zone_name': 'testnet',
            'version': 6,
            'include': '',
            'rev_include': '',
            'hosts': {
                'node001': 'fe80::1',
                'node002': 'fe80::2',
                'node003': 'fe80::3',
                'node004': 'fe80::4',
                'node005': 'fe80::5',
                'node006': 'fe80::6',
                'node007': 'fe80::7',
                'node008': 'fe80::8',
                'node009': 'fe80::9',
                'node010': 'fe80::a',
                'master':  'fe80::ffff:ffff:ffff:fffe',
            },
            'rev_zone_name': '0.0.0.0.0.0.0.0.0.0.0.0.0.8.e.f',
            'rev_hosts': {
                '1.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0': 'node001.testnet.',
                '2.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0': 'node002.testnet.',
                '3.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0': 'node003.testnet.',
                '4.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0': 'node004.testnet.',
                '5.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0': 'node005.testnet.',
                '6.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0': 'node006.testnet.',
                '7.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0': 'node007.testnet.',
                '8.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0': 'node008.testnet.',
                '9.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0': 'node009.testnet.',
                'a.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0': 'node010.testnet.',
                'e.f.f.f.f.f.f.f.f.f.f.f.f.f.f.f': 'master.testnet.',
            },
        }
        self.assertEqual(self.net.zone_data, expected_dict)

if __name__ == '__main__':
    unittest.main()
