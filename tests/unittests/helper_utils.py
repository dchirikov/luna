import rpm
import os
import shutil
import socket
import time
import tempfile
import pymongo
import subprocess
import ming
import uuid


class Sandbox(object):
    """
    Class for creating sanboxed envidonment for Luna
    Class.db     - MongoDB or Ming database.
                   Depends if mongod executable exist.
    Class.dbtype - Current DB.
    Class.path   - Path to temporary folder.
    """

    def __init__(self, path = None, dbtype = 'auto'):
        """
        path   - Path to store sandbox files.
        dbtype - Type of the dabatabse. [auto|mongo|ming]
        """
        if 'LUNA_TEST_DBTYPE' in os.environ:
            dbtype = os.environ['LUNA_TEST_DBTYPE']
        if not path:
            self.path = tempfile.mkdtemp(prefix='luna')
        else:
            # can cause race condition, but ok
            if not os.path.exists(path):
                os.makedirs(path)
            self.path = path
        self._dbconn = None
        self._mingdatastore = None
        self._mongopath = self.path + "/mongo"
        if not os.path.exists(self._mongopath):
            os.makedirs(self._mongopath)
        self._mongoprocess = None
        if dbtype == 'auto':
            try:
                self._start_mongo()
                self.dbtype = 'mongo'
            except OSError:
                self._mingdatastore = ming.create_datastore('mim:///' + str(uuid.uuid4()))
                self._dbconn = self._mingdatastore.db.luna
                self.dbtype = 'ming'
        elif dbtype == 'mongo':
            self._start_mongo()
            self.dbtype = 'mongo'
        else:
            self._mingdatastore = ming.create_datastore('mim:///' + str(uuid.uuid4()))
            self._dbconn = self._mingdatastore.db.luna
            self.dbtype = 'ming'
        self._create_luna_homedir()

    def _create_luna_homedir(self):
        """
        Creates ./boot, ./torrents, ./templates
        subdirs in path
        """

        if 'VIRTUAL_ENV' not in os.environ:
            print "Runinning not in virtual environment"
            virtual_env_path = '/'
        else:
            virtual_env_path = os.environ['VIRTUAL_ENV']
        for d in ['boot', 'torrents']:
            if not os.path.exists(self.path + '/' + d):
                os.makedirs(self.path + '/' + d)
        source_template_path = virtual_env_path + '/usr/share/luna/templates'
        if not os.path.exists(self.path + '/templates'):
            shutil.copytree(source_template_path, self.path + '/templates')

    def _start_mongo(self):
        # will try 5 times
        for t in range(5):
            s = socket.socket()
            res = s.bind(('127.0.0.1', 0))
            dbport = s.getsockname()[1]
            s.close()
            s = None
            self._mongoprocess = subprocess.Popen([
                'mongod',
                '--bind_ip',
                'localhost',
                '--port', str(dbport),
                '--dbpath', self._mongopath,
                '--nojournal', '--nohttpinterface',
                '--noauth', '--smallfiles',
                '--syncdelay', '0',
                '--maxConns', '10',
                '--nssize', '1', ],
                stdout=open(os.devnull, 'wb'),
                stderr=subprocess.STDOUT

            )

            # it might take some time to bring DB up

            for i in range(3):
                time.sleep(1)
                try:
                    self._dbconn = pymongo.MongoClient('localhost:'+ str(dbport))['luna']
                except pymongo.errors.ConnectionFailure:
                    continue
                else:
                    break
            if self._dbconn:
                break
        if not self._dbconn:
            self.cleanup()
            assert False, 'Cannot connect to the mongodb test instance'

    @property
    def db(self):
        return self._dbconn

    def __del__(self):
        self.cleanup()

    def cleanup(self):
        if self._mongoprocess:
            self._mongoprocess.terminate()
            self._mongoprocess.wait()
            self._mongoprocess = None
        elif self._mingdatastore:
            self._mingdatastore.conn.drop_all()
        shutil.rmtree(self.path, ignore_errors=True)
