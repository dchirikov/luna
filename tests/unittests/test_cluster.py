from ming import create_datastore
import unittest

import os
import luna
import getpass
from helper_utils import Sandbox


expected = {'name': 'general',
            'nodeprefix': 'node',
            'nodedigits': 3,
            'user': getpass.getuser(),
            'path': '',
            'debug': 0,
            'cluster_ips': None,
            'frontend_address': '',
            'frontend_port': '7050',
            'server_port': 7051,
            'tracker_interval': 10,
            'tracker_min_interval': 5,
            'tracker_maxpeers': 200,
            'torrent_listen_port_min': 7052,
            'torrent_listen_port_max': 7200,
            'torrent_pidfile': '/run/luna/ltorrent.pid',
            'lweb_pidfile': '/run/luna/lweb.pid',
            'lweb_num_proc': 0,
            'named_include_file': '/etc/named.luna.zones',
            'named_zone_dir': '/var/named',
            'dhcp_net': None,
            'dhcp_range_start': None,
            'dhcp_range_end': None,
            'comment': None}


class ClusterUtilsTests(unittest.TestCase):

    @classmethod
    def setUpClass(self):

        print

        self.sandbox = Sandbox()
        self.db = self.sandbox.db
        self.path = self.sandbox.path

        self.cluster = luna.Cluster(mongo_db=self.db, create=True,
                                    path=self.path, user=getpass.getuser())

    @classmethod
    def tearDownClass(self):
        self.sandbox.cleanup()


class ClusterReadTests(unittest.TestCase):

    def setUp(self):

        print

        self.sandbox = Sandbox()
        self.db = self.sandbox.db
        self.path = self.sandbox.path

    def tearDown(self):
        self.sandbox.cleanup()

    def test_read_non_existing_cluster(self):
        self.assertRaises(RuntimeError, luna.Cluster, mongo_db=self.db)

    def test_cluster_read(self):
        luna.Cluster(mongo_db=self.db, create=True,
                     path=self.path, user=getpass.getuser())

        cluster = luna.Cluster(mongo_db=self.db)
        doc = self.db['cluster'].find_one({'_id': cluster._id})
        expected['path'] = self.path

        for attr in expected:
            self.assertEqual(doc[attr], expected[attr])


class ClusterCreateTests(unittest.TestCase):

    def setUp(self):

        print

        self.sandbox = Sandbox()
        self.db = self.sandbox.db
        self.path = self.sandbox.path

    def tearDown(self):
        self.sandbox.cleanup()

    def test_init_cluster_with_defaults(self):
        cluster = luna.Cluster(mongo_db=self.db, create=True,
                               path=self.path, user=getpass.getuser())

        doc = self.db['cluster'].find_one({'_id': cluster._id})
        expected['path'] = self.path

        for attr in expected:
            self.assertEqual(doc[attr], expected[attr])

if __name__ == '__main__':
    unittest.main()
