'''
Written by Dmitry Chirikov <dmitry@chirikov.ru>
This file is part of Luna, cluster provisioning tool
https://github.com/dchirikov/luna

This file is part of Luna.

Luna is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Luna is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Luna.  If not, see <http://www.gnu.org/licenses/>.

'''

from config import db_name, use_key, usedby_key

import pymongo
import inspect
import logging

from bson.objectid import ObjectId
from bson.dbref import DBRef
from bson.json_util import dumps

from luna import utils


class Base(object):
    """
    Base for LunaCluster
    Also it is the parent class for the rest classes
    """

    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger(__name__)
    _logger = logging.getLogger(__name__)
    _collection_name = None
    _mongo_collection = None
    _keylist = None
    _id = None
    _name = None
    _DBRef = None
    _json = None

    def __init__(self):
        """
        Constructor can be used for creating object by setting create=True
        nodeprefix='node' and nodedigits='3' will give names like node001,
        nodeprefix='compute' and nodedigits='2' will give names like compute01
        name is used to give default name for mongo document.
        Don't change it is are not sure what you are doing.
        """
        err_msg = "Please do not call this class directly"
        self.log.error(err_msg)
        raise RuntimeError, err_msg

    def __str__(self):
        """Returns name"""

        return self._name

    @property
    def name(self):
        """Name of the object"""

        return str(self._name)

    @property
    def id(self):
        """MongoDB's '_id' value of the document"""

        return self._id

    @property
    def DBRef(self):
        """MongoDB DBRef of the document"""

        return self._DBRef

    @property
    def nice_json(self):
        """Raw json from MongoDB. One should not use it for change"""

        return dumps(self._json, sort_keys=True, indent=4,
                     separators=(',', ': '))

    @property
    def keylist(self):
        """
        List of the 'simple' fields one can change (no data structures here)
        """
        return self._keylist

    def _check_name(self, name, mongo_db, create, id):
        return self._get_object(name, mongo_db, create, id)

    def _get_object(self, name, mongo_db, create, id):
        if name and type(name) != str:
            err_msg = "Name of the object should be string."
            self.log.error(err_msg)
            raise RuntimeError, err_msg
        if mongo_db:
            self._mongo_db = mongo_db
        else:
            try:
                client = pymongo.MongoClient(**utils.helpers.get_con_options())
            except:
                err_msg = "Unable to connect to MongoDB."
                self.log.error(err_msg)
                raise RuntimeError, err_msg

            self.log.debug("Connection to MongoDB was successful.")
            self._mongo_db = client[db_name]

        self._mongo_collection = self._mongo_db[self._collection_name]

        self._json = self._mongo_collection.find_one({'$or': [{'name': name},
                                                              {'_id': id}]})

        if not create and not self._json:
            err_msg = ("Object '{}' of type '{}' does not exist"
                       .format(name, self._collection_name))
            self.log.error(err_msg)
            raise RuntimeError, err_msg

        elif not create and self._json:
            self._id = self._json['_id']
            self._name = self._json['name']
            self._DBRef = DBRef(u'' + self._collection_name, self._id)

        elif create and self._json:
            err_msg = "'{}' is already created".format(self._json['name'])
            self.log.error(err_msg)
            raise RuntimeError, err_msg

        return self._json

    def _debug_function(self):
        """Outputs the calling function's name and it's arguments"""

        if logging.getLogger().getEffectiveLevel() != 10:
            return None

        caller = inspect.currentframe().f_back
        f_name = inspect.getframeinfo(caller)[2]
        _, _, _, values = inspect.getargvalues(caller)

        return (f_name, values)

    def _debug_instance(self):
        """Outputs tuple of internal data from class"""

        if logging.getLogger().getEffectiveLevel() != 10:
            return None

        return (self._name, self._id, self._DBRef, self.nice_json)

    def _wipe_vars(self):
        """Erase class variables"""

        self.log.debug("function args {}".format(self._debug_function()))
        keys = self.__dict__.keys()

        for key in keys:
            self.__dict__.pop(key, None)

        return None

    def _get_json(self):
        """Return document as stored in DB in json format"""

        return self._json

    def show(self):
        def get_value(value):
            if type(value) is not DBRef:
                return value
            dbref = value
            mongo_collection = self._mongo_db[dbref.collection]
            try:
                name = mongo_collection.find_one({'_id': dbref.id})['name']
                name = '[' + name + ']'
            except:
                name = '[id_' + str(dbref.id) + ']'
            return name

        def resolve_links(json):
            internal_json = {}
            if type(json) is not dict:
                return get_value(json)
            for key in json:
                val = json[key]
                if type(val) is dict:
                    internal_json[key] = resolve_links(val)
                    continue
                if type(val) is list:
                    internal_list = val[:]
                    for idx in range(len(internal_list)):
                        internal_list[idx] = resolve_links(internal_list[idx])
                    internal_json[key] = internal_list[:]
                    continue
                internal_json[key] = get_value(val)
            return internal_json

        json = self._get_json()
        try:
            json.pop('_id')
        except:
            pass
        try:
            json.pop(use_key)
        except:
            pass
        try:
            json.pop(usedby_key)
        except:
            pass
        return resolve_links(json)

    def get(self, key):
        """Get object attributes"""

        self.log.debug("function args {}".format(self._debug_function()))

        if key in self._json:
            value = self._json[key]

            if not value and key in self._keylist:
                if self._keylist[key] is str:
                    value = ''
                elif self._keylist[key] is int:
                    value = 0

            elif value and type(value) == unicode:
                value = str(value)

            return value

        else:
            value = None

        return value

    def store(self, obj):
        obj[usedby_key] = {}
        self._id = self._mongo_collection.insert(obj)

        self._DBRef = DBRef(self._collection_name, self._id)
        self._name = obj['name']
        self._json = obj

        return True

    def set(self, key, value):
        """Allow to set variables from keylist"""

        self.log.debug("function args {}".format(self._debug_function()))

        if not bool(key) or type(key) is not str:
            self.log.error("Field should be specified")
            return False

        if not self._json:
            self.log.error("No json for the given object")
            return False

        if key in self._keylist and type(value) is not self._keylist[key]:
            self.log.error(("Value '{}' should be of type '{}'"
                            .format(key, self._keylist[key])))
            return False

        if value == '':
            value = None

        if type(value) is str:
            value = unicode(value, "utf-8")

        self._mongo_collection.update({'_id': self._id},
                                      {'$set': {key: value}},
                                      multi=False, upsert=False)

        self._json[key] = value

        return True

    def rename(self, name):
        """Rename object"""
        self.log.debug("function args {}".format(self._debug_function()))

        obj = self._mongo_collection.find_one({'name': name})
        if obj:
            self.log.error("Object '{}' exists already".format(name))
            return None

        self.set('name', name)
        self._name = name

        return True

    def link(self, remote_dbref):
        """Unlink objects in MongoDB"""
        self.log.debug("function args {}".format(self._debug_function()))

        try:
            remote_dbref = remote_dbref.DBRef
        except:
            pass

        if not isinstance(remote_dbref, DBRef):
            self.log.error("Object to link to is not a DBRef object")
            return None

        elif remote_dbref == self._DBRef:
            self.log.error("Can't link an object to itself")
            return None

        use_doc = self._mongo_collection.find_one({'_id': self._id},
                                                  {use_key: 1, '_id': 0})

        remote_collection = self._mongo_db[remote_dbref.collection]
        usedby_doc = remote_collection.find_one({'_id': remote_dbref.id},
                                                {usedby_key: 1, '_id': 0})
        try:
            use_doc = use_doc[use_key]
        except:
            use_doc = {}
        try:
            usedby_doc = usedby_doc[usedby_key]
        except:
            usedby_doc = {}
        try:
            links = use_doc[remote_dbref.collection][str(remote_dbref.id)]
        except:
            links = 0
        try:
            backlinks = usedby_doc[self._DBRef.collection][str(self._DBRef.id)]
        except:
            backlinks = 0
        links += 1
        backlinks += 1
        try:
            use_doc[remote_dbref.collection][str(remote_dbref.id)] = links
        except:
            use_doc[remote_dbref.collection] = {}
            use_doc[remote_dbref.collection][str(remote_dbref.id)] = links
        try:
            usedby_doc[self._DBRef.collection][str(self._DBRef.id)] = backlinks
        except:
            usedby_doc[self._DBRef.collection] = {}
            usedby_doc[self._DBRef.collection][str(self._DBRef.id)] = backlinks
        self._mongo_collection.update({'_id': self._id},
                                      {'$set': {use_key: use_doc}})
        remote_collection.update({'_id': remote_dbref.id},
                                 {'$set': {usedby_key: usedby_doc}})

    def unlink(self, remote_dbref):
        """Link objects in MongoDB"""
        self.log.debug("function args {}".format(self._debug_function()))

        try:
            remote_dbref = remote_dbref.DBRef
        except:
            pass

        if not isinstance(remote_dbref, DBRef):
            err_msg = "Object to unlink from is not a DBRef object"
            self.log.error(err_msg)
            raise RuntimeError, err_msg
            return None

        elif remote_dbref == self._DBRef:
            self.log.error("Can't unlink an object from itself")
            return None

        remote_collection = self._mongo_db[remote_dbref.collection]
        use_doc = self._mongo_collection.find_one({'_id': self._id},
                                                  {use_key: 1, '_id': 0})
        usedby_doc = remote_collection.find_one({'_id': remote_dbref.id},
                                                {usedby_key: 1, '_id': 0})
        try:
            use_doc = use_doc[use_key]
        except:
            use_doc = {}
        try:
            usedby_doc = usedby_doc[usedby_key]
        except:
            usedby_doc = {}
        try:
            links = use_doc[remote_dbref.collection][str(remote_dbref.id)]
        except:
            links = 0
        try:
            backlinks = usedby_doc[self._DBRef.collection][str(self._DBRef.id)]
        except:
            backlinks = 0

        if links < 1:
            self.log.error("No links to this object. Cannot unlink.")
            return None

        if backlinks < 1:
            self.log.error(("Link to this objct exists, "
                            "but no backlinks to this object. Cannot unlink."))
            return None

        links -= 1
        backlinks -= 1
        if links < 1:
            use_doc[remote_dbref.collection].pop(str(remote_dbref.id))
            if len(use_doc[remote_dbref.collection]) < 1:
                use_doc.pop(remote_dbref.collection)
        else:
            use_doc[remote_dbref.collection][str(remote_dbref.id)] = links
        if backlinks < 1:
            usedby_doc[self._DBRef.collection].pop(str(self._DBRef.id))
            if len(usedby_doc[self._DBRef.collection]) < 1:
                usedby_doc.pop(self._DBRef.collection)
        else:
            usedby_doc[self._DBRef.collection][str(self._DBRef.id)] = backlinks
        self._mongo_collection.update({'_id': self._id},
                                      {'$set': {use_key: use_doc}})
        remote_collection.update({'_id': remote_dbref.id},
                                 {'$set': {usedby_key: usedby_doc}})

    def get_links(self, resolve=False, collection=None):
        """Enumerates all references"""

        self.log.debug("function args {}".format(self._debug_function()))
        use_doc = self._mongo_collection.find_one({'_id': self._id},
                                                  {use_key: 1, '_id': 0})
        try:
            use_doc = use_doc[use_key]
        except:
            return []

        if bool(collection):
            try:
                collection_objs = use_doc.pop('collection')
            except:
                collection_objs = {}
            use_doc = {}
            use_doc['collection'] = collection_objs

        output = []
        for col_iter in use_doc:
            for uid in use_doc[col_iter]:
                dbref = DBRef(col_iter, ObjectId(uid))
                remote_col = self._mongo_db[dbref.collection]
                if not resolve:
                    name = str(dbref.id)
                else:
                    try:
                        name = remote_col.find_one({'_id': dbref.id})['name']
                    except:
                        name = str(dbref.id)
                output.extend([{'collection': dbref.collection,
                                'name': name, 'DBRef': dbref}])
        return output

    def get_back_links(self, resolve=False, collection=None):
        """Enumerates all reverse references"""
        self.log.debug("function args {}".format(self._debug_function()))

        usedby_doc = self._mongo_collection.find_one({'_id': self._id},
                                                     {usedby_key: 1, '_id': 0})
        try:
            usedby_doc = usedby_doc[usedby_key]
        except:
            return []

        if bool(collection):
            try:
                collection_objs = usedby_doc.pop('collection')
            except:
                collection_objs = {}
            usedby_doc = {}
            usedby_doc['collection'] = collection_objs

        output = []
        for col_iter in usedby_doc:
            for uid in usedby_doc[col_iter]:
                dbref = DBRef(col_iter, ObjectId(uid))
                remote_col = self._mongo_db[dbref.collection]
                if not resolve:
                    name = str(dbref.id)
                else:
                    try:
                        name = remote_col.find_one({'_id': dbref.id})['name']
                    except:
                        name = str(dbref.id)
                output.extend([{'collection': dbref.collection,
                                'name': name, 'DBRef': dbref}])
        return output

    def cleanup_links(self):
        links = self.get_links(resolve=True)
        back_links = self.get_back_links(resolve=True)

        if len(back_links) > 0:
            self.log.error(("{} is a dependency for the objects:"
                            .format(self._name)))

            for elem in back_links:
                self.log.error("[{}/{}]".format(elem['collection'],
                                                elem['name']))

            return False

        for link in links:
            self.unlink(link['DBRef'])

        return True

    def release_resources(self):
        return True

    def delete(self):
        """Used to delete this object from the datastore"""

        self.log.debug("function {} args".format(self._debug_function()))

        if not self.cleanup_links():
            return False

        self.release_resources()

        ret = self._mongo_collection.remove({'_id': self._id}, multi=False)
        self._wipe_vars()

        return not ret['err']
