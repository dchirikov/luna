from ming import create_datastore
import mock
import unittest

import os
import luna
import getpass
from helper_utils import Sandbox


class BMCSetupCreateTests(unittest.TestCase):

    def setUp(self):

        print

        self.sandbox = Sandbox()
        self.db = self.sandbox.db
        self.path = self.sandbox.path

        cluster = luna.Cluster(mongo_db=self.db, create=True,
                               path=self.path, user=getpass.getuser())

    def tearDown(self):
        self.sandbox.cleanup()

    def test_create_bmcsetup_with_defaults(self):
        bmc = luna.BMCSetup(name='testbmc', mongo_db=self.db, create=True)

        doc = self.db['bmcsetup'].find_one({'_id': bmc._id})
        expected = {'userid': 3, 'user': 'ladmin', 'password': 'ladmin',
                    'netchannel': 1, 'mgmtchannel': 1, 'comment': ''}

        for attr in expected:
            self.assertEqual(doc[attr], expected[attr])

    def test_create_bmcsetup_with_wrong_attr_type(self):
        self.assertRaises(RuntimeError,
                          luna.BMCSetup, name='testbmc', mongo_db=self.db,
                          create=True, userid='3')


class BMCSetupReadTests(unittest.TestCase):

    def setUp(self):

        print

        self.sandbox = Sandbox()
        self.db = self.sandbox.db
        self.path = self.sandbox.path

        cluster = luna.Cluster(mongo_db=self.db, create=True,
                               path=self.path, user=getpass.getuser())
        self.bmc = luna.BMCSetup(name='testbmc', mongo_db=self.db, create=True)

    def tearDown(self):
        self.sandbox.cleanup()

    def test_read_non_existing_bmcsetup(self):
        self.assertRaises(RuntimeError, luna.BMCSetup, mongo_db=self.db,
                          name='non_existing')

    def test_read_bmcsetup(self):
        bmc = luna.BMCSetup(name='testbmc', mongo_db=self.db)

        doc = self.db['bmcsetup'].find_one({'_id': bmc._id})
        expected = {'userid': 3, 'user': 'ladmin', 'password': 'ladmin',
                    'netchannel': 1, 'mgmtchannel': 1}

        for attr in expected:
            self.assertEqual(doc[attr], expected[attr])

if __name__ == '__main__':
    unittest.main()
