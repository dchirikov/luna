import unittest
import mock

import luna
import getpass
from helper_utils import Sandbox


class OsimageCreateTests(unittest.TestCase):

    def setUp(self):

        print

        self.sandbox = Sandbox()
        self.db = self.sandbox.db
        self.path = self.sandbox.path

        self.cluster = luna.Cluster(
            mongo_db=self.db,
            create=True,
            path=self.path,
            user=getpass.getuser(),
        )

    def tearDown(self):
        self.sandbox.cleanup()

    @mock.patch('rpm.TransactionSet')
    @mock.patch('rpm.addMacro')
    def test_create_osimage_with_defaults(self,
                                          mock_rpm_addmacro,
                                          mock_rpm_transactionset,
                                          ):
        packages = [
            {'VERSION': '3.10', 'RELEASE': '999-el0', 'ARCH': 'x86_64'},
        ]
        mock_rpm_transactionset.return_value.dbMatch.return_value = packages

        osimage = luna.OsImage(
            name='testosimage',
            path=self.path,
            mongo_db=self.db,
            create=True,
        )

        doc = self.db['osimage'].find_one({'_id': osimage._id})
        expected = {
            'path': self.path,
            'kernmodules': 'ipmi_devintf,ipmi_si,ipmi_msghandler',
            'dracutmodules': 'luna,-i18n,-plymouth',
            'kernver': '3.10-999-el0.x86_64'
        }

        for attr in expected:
            self.assertEqual(doc[attr], expected[attr])

    @mock.patch('rpm.TransactionSet')
    @mock.patch('rpm.addMacro')
    def test_create_osimage_with_same_path(self,
                                           mock_rpm_addmacro,
                                           mock_rpm_transactionset,
                                           ):
        packages = [
            {'VERSION': '3.10', 'RELEASE': '999-el0', 'ARCH': 'x86_64'},
        ]
        mock_rpm_transactionset.return_value.dbMatch.return_value = packages

        args = {
            'name': 'testosimage',
            'path': self.path,
            'mongo_db': self.db,
            'create': True,
        }
        luna.OsImage(**args)
        args['name'] = 'testosimage2'

        self.assertRaises(RuntimeError, luna.OsImage, **args)

    @mock.patch('rpm.TransactionSet')
    @mock.patch('rpm.addMacro')
    def test_create_osimage_wo_kernel(self,
                                      mock_rpm_addmacro,
                                      mock_rpm_transactionset,
                                      ):
        mock_rpm_transactionset.return_value.dbMatch.return_value = []

        args = {
            'name': 'testosimage',
            'path': self.path,
            'mongo_db': self.db,
            'create': True,
        }

        self.assertRaises(RuntimeError, luna.OsImage, **args)

    def test_create_osimage_wrong_path(self):
        args = {
            'name': 'testosimage',
            'path': '/dev/null',
            'mongo_db': self.db,
            'create': True,
        }

        self.assertRaises(RuntimeError, luna.OsImage, **args)

    @mock.patch('rpm.TransactionSet')
    @mock.patch('rpm.addMacro')
    def test_create_osimage_wrong_kernver(self,
                                          mock_rpm_addmacro,
                                          mock_rpm_transactionset,
                                          ):
        packages = [
            {'VERSION': '3.10', 'RELEASE': '999-el0', 'ARCH': 'x86_64'},
        ]

        mock_rpm_transactionset.return_value.dbMatch.return_value = packages

        args = {
            'name': 'testosimage',
            'path': self.path,
            'mongo_db': self.db,
            'kernver': '3.10-000-el0.x86_64',
            'create': True,
        }

        self.assertRaises(RuntimeError, luna.OsImage, **args)

    @mock.patch('rpm.TransactionSet')
    @mock.patch('rpm.addMacro')
    def test_create_osimage_wrong_grablist(self,
                                           mock_rpm_addmacro,
                                           mock_rpm_transactionset,
                                           ):
        packages = [
            {'VERSION': '3.10', 'RELEASE': '999-el0', 'ARCH': 'x86_64'},
        ]

        mock_rpm_transactionset.return_value.dbMatch.return_value = packages

        args = {
            'name': 'testosimage',
            'path': self.path,
            'mongo_db': self.db,
            'grab_list': 'no_grab_list',
            'create': True,
        }

        self.assertRaises(RuntimeError, luna.OsImage, **args)


class OsimageMethodsTests(unittest.TestCase):

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
            user=getpass.getuser(),
        )

        self.osimage = luna.OsImage(
            name='testosimage',
            path=self.path,
            mongo_db=self.db,
            create=True,
        )

    def tearDown(self):
        self.sandbox.cleanup()

    @mock.patch('shutil.copy')
    @mock.patch('os.remove')
    @mock.patch('os.chmod')
    @mock.patch('os.chown')
    @mock.patch('shutil.move')
    @mock.patch('os.close')
    @mock.patch('os.fchdir')
    @mock.patch('subprocess.Popen')
    @mock.patch('os.chroot')
    @mock.patch('os.open')
    def test_pack_create_tarball(self,
                                 mock_os_open,
                                 mock_os_chroot,
                                 mock_subprocess_popen,
                                 mock_os_fchdir,
                                 mock_os_close,
                                 mock_shutil_move,
                                 mock_os_chown,
                                 mock_os_chmod,
                                 mock_os_remove,
                                 mock_shutil_copy,
                                 ):

        mock_subprocess_popen.return_value.stderr.readline.return_value = ''

        self.assertTrue(self.osimage.create_tarball())

    def test_create_torrent_wo_tarball(self):

        self.assertFalse(self.osimage.create_torrent())

    @mock.patch('os.path.exists')
    def test_create_torrent_w_wrong_tarball(self,
                                            mock_os_path_exists):

        self.osimage.set('tarball', 'UUID')

        mock_os_path_exists.return_value = False

        self.assertFalse(self.osimage.create_torrent())

    @mock.patch('os.path.exists')
    def test_create_torrent_w_wrong_frontend(self,
                                             mock_os_path_exists):

        self.osimage.set('tarball', 'UUID')

        self.assertFalse(self.osimage.create_torrent())

    @mock.patch('os.path.exists')
    def test_create_torrent_w_wrong_frontend_port(
            self, mock_os_path_exists):

        self.osimage.set('tarball', 'UUID')
        self.cluster.set('frontend_address', '127.0.0.1')
        self.cluster.set('frontend_port', 0)

        self.assertFalse(self.osimage.create_torrent())

    @mock.patch('libtorrent.set_piece_hashes')
    @mock.patch('libtorrent.add_files')
    @mock.patch('shutil.move')
    @mock.patch('os.chdir')
    @mock.patch('os.close')
    @mock.patch('os.fchdir')
    @mock.patch('os.chroot')
    @mock.patch('os.open')
    @mock.patch('subprocess.Popen')
    @mock.patch('os.chmod')
    @mock.patch('os.chown')
    @mock.patch('shutil.copy')
    @mock.patch('os.path.exists')
    def test_create_torrent_default(*args):
        self = args[0]
        args[5].return_value.stderr.readline.return_value = ''
        self.osimage.set('tarball', 'UUID')
        self.cluster.set('frontend_address', '127.0.0.1')
        self.cluster.set('frontend_port', 7050)
        self.assertTrue(self.osimage.create_torrent())

    @mock.patch('os.close')
    @mock.patch('os.fchdir')
    @mock.patch('os.remove')
    @mock.patch('subprocess.Popen')
    @mock.patch('os.chroot')
    @mock.patch('os.open')
    def test_pack_image_broken(self,
                               mock_os_open,
                               mock_os_chroot,
                               mock_subprocess_popen,
                               mock_os_remove,
                               mock_os_fchdir,
                               mock_os_close,
                               ):

        mock_subprocess_popen.side_effect = Exception('dummy excepion')

        self.assertFalse(self.osimage.create_tarball())

    @mock.patch('rpm.TransactionSet')
    @mock.patch('rpm.addMacro')
    def test_get_package_ver(self,
                             mock_rpm_addmacro,
                             mock_rpm_transactionset,
                             ):
        packages = [
            {'VERSION': '3.10', 'RELEASE': '999-el0', 'ARCH': 'x86_64'},
            {'VERSION': '3.11', 'RELEASE': '999-el0', 'ARCH': 'x86_64'},
        ]
        mock_rpm_transactionset.return_value.dbMatch.return_value = packages
        #mock_rpm_transactionset.dbMatch = [p1]
        self.assertEqual(
            self.osimage.get_package_ver('', 'test'),
            ['3.10-999-el0.x86_64', '3.11-999-el0.x86_64']
        )

        self.assertEqual(
            self.osimage.list_kernels(),
            ['3.10-999-el0.x86_64', '3.11-999-el0.x86_64']
        )

    @mock.patch('os.chmod')
    @mock.patch('os.chown')
    @mock.patch('shutil.copy')
    @mock.patch('shutil.move')
    @mock.patch('os.path.isfile')
    @mock.patch('os.remove')
    @mock.patch('pwd.getpwnam')
    @mock.patch('subprocess.Popen')
    def Ztest_pack_boot(*args):

        self = args[0]
        args[2].return_value.pw_uid.return_value = 1000
        args[2].return_value.pw_gid.return_value = 1000

        self.assertFalse(self.osimage.pack_boot())

        args[1].return_value.poll.side_effect = [None, None, True]
        self.assertFalse(self.osimage.pack_boot())
        args[1].return_value.poll.side_effect = [None, None, True]
        args[1].return_value.stdout.readline.return_value = 'luna'
        self.assertFalse(self.osimage.pack_boot())
        args[1].return_value.returncode = 0
        args[1].return_value.poll.side_effect = [None, None, True]
        self.assertTrue(self.osimage.pack_boot())

    def test_copy_boot_wo_kern(self):
        self.assertFalse(self.osimage.copy_boot())

    @mock.patch('os.chmod')
    @mock.patch('os.chown')
    @mock.patch('shutil.copy')
    @mock.patch('os.path.isfile')
    def test_copy_boot_default(*args):
        self = args[0]
        self.assertTrue(self.osimage.copy_boot())

    @mock.patch('os.remove')
    @mock.patch('subprocess.Popen')
    @mock.patch('os.path.exists')
    def grab_host_default(*args):
        self = args[0]
        args[2].return_value.stdout.readline.return_value = ''
        args[2].return_value.communicate.return_value = ('', '')
        args[2].return_value.returncode = 0
        self.assertTrue(self.osimage.grab_host('127.0.0.1'))
        args[2].return_value.returncode = 255
        self.assertFalse(self.osimage.grab_host('127.0.0.1'))

if __name__ == '__main__':
    unittest.main()
