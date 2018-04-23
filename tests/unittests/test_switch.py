from ming import create_datastore
import mock
import unittest

import os
import luna
import getpass
from helper_utils import Sandbox


class SwitchTestsCreate(unittest.TestCase):

    def setUp(self):

        print

        self.sandbox = Sandbox()
        self.db = self.sandbox.db
        self.path = self.sandbox.path

        cluster = luna.Cluster(mongo_db=self.db, create=True,
                               path=self.path, user=getpass.getuser())

        self.network = luna.Network(mongo_db=self.db, create=True,
                               name='cluster', NETWORK='10.141.0.0',
                               PREFIX=16)

    def tearDown(self):
        self.sandbox.cleanup()

    def test_create_switch_with_defaults(self):
        switch = luna.Switch(mongo_db=self.db, create=True,
                             name='switch01',
                             network=self.network.name,
                             ip='10.141.100.1')

        self.assertTrue(switch)


class SwitchTestsChange(unittest.TestCase):

    def setUp(self):

        print

        self.sandbox = Sandbox()
        self.db = self.sandbox.db
        self.path = self.sandbox.path

        cluster = luna.Cluster(mongo_db=self.db, create=True,
                               path=self.path, user=getpass.getuser())

        self.network = luna.Network(mongo_db=self.db, create=True,
                               name='cluster', NETWORK='10.141.0.0',
                               PREFIX=16)
        self.switch = luna.Switch(mongo_db=self.db, create=True,
                                  name='switch01',
                                  network=self.network.name,
                                  ip='10.141.100.1')

    def tearDown(self):
        self.sandbox.cleanup()

    def test_delete_switch(self):
        if self.sandbox.dbtype != 'mongo':
            raise unittest.SkipTest(
                'This test can be run only with MongoDB as a backend.'
            )

        self.assertTrue(self.switch.delete())
        doc = self.db['switch'].find_one({'name': self.switch.name})
        self.assertIsNone(doc)


if __name__ == '__main__':
    unittest.main()
