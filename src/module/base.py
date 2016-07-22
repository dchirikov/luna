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

from config import *
import pymongo
import logging
import inspect
import json
from bson.objectid import ObjectId
from bson.dbref import DBRef
from utils import *

class Base(object):
    """
    Base for LunaCluster
    Also it is the parent class for the rest classes
    """

    logging.basicConfig(level=logging.INFO)
#    logging.basicConfig(level=logging.DEBUG)
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
        nodeprefix='compute' and nodedigits='4' will give names like compute0001
        name is used to give default name for mongo document.
        Don't change it is are not sure what you are doing.
        """
        self._logger.error("Please do not call this class directly")
        raise RuntimeError

    def _check_name(self, name, mongo_db, create, id):
        if mongo_db:
            self._mongo_db = mongo_db
        else:
            try:
                self._mongo_client = pymongo.MongoClient(get_con_options())
            except:
                self._logger.error("Unable to connect to MongoDB.")
                raise RuntimeError
            self._logger.debug("Connection to MongoDB was successful.")
            self._mongo_db = self._mongo_client[db_name]
        self._mongo_collection = self._mongo_db[self._collection_name]
        if id:
            mongo_doc = self._mongo_collection.find_one({'_id': id})
            if mongo_doc:
                return mongo_doc
        if not name:
            self._logger.error("'name' needs to be specified")
            raise RuntimeError
        mongo_doc = self._mongo_collection.find_one({'name': name})
        if not create and not mongo_doc:
            self._logger.error("It is needed to create object '{}' type '{}' first".format(name, self._collection_name))
            raise RuntimeError
        if create and mongo_doc and mongo_doc['name'] == name:
            self._logger.error("'{}' is already created".format(name))
            raise RuntimeError
        return mongo_doc

    def _debug_function(self):
        """
        Outputs name of the calling function and parameters passed into
        """
        if logging.getLogger().getEffectiveLevel() != 10:
            return None
        caller = inspect.currentframe().f_back
        f_name = inspect.getframeinfo(caller)[2]
        _, _, _, values = inspect.getargvalues(caller)
        return (f_name, values)

    def _debug_instance(self):
        """
        Outputs tuple of internal data from class
        """
        if logging.getLogger().getEffectiveLevel() != 10:
            return None
        return (self._name, self._id, self._DBRef, self.nice_json)

    def _wipe_vars(self):
        """
        Erase class variables
        """
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        keys = self.__dict__.keys()
        for key in keys:
            self.__dict__.pop(key, None)
        return None

    def _get_json(self):
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        if self._id:
            return self._mongo_collection.find_one({'_id': self._id})

    def __repr__(self):
        """
        Returns nice JSON
        """
        from bson.json_util import dumps
        return dumps(self._get_json(), sort_keys=True, indent=4, separators=(',', ': '))

    def __str__(self):
        """
        Returns name
        """
        return self._name

    def show(self):
        def get_value(value):
            if type(value) is not DBRef:
                return value
            dbref = value
            #mongo_db = self._mongo_client[db_name]
            mongo_db = self._mongo_db
            mongo_collection = self._mongo_db[dbref.collection]
            try:
                name = '[' + mongo_collection.find_one({'_id': dbref.id})['name'] + ']'
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

    @property
    def name(self):
        """
        Name of the object
        """
        return str(self._name)

    @property
    def id(self):
        """
        MongoDB's '_id' value of the document
        """
        return self._id

    @property
    def DBRef(self):
        """
        MongoDB DBRef of the document
        """
        return self._DBRef

    @property
    def json(self):
        """
        Raw json from MongoDB. One should not use it for change
        """
        return self._get_json()

    @property
    def nice_json(self):
        """
        Raw json from MongoDB. One should not use it for change
        """
        from bson.json_util import dumps
        return dumps(self._get_json(), sort_keys=True, indent=4, separators=(',', ': '))

    @property
    def keylist(self):
        """
        List of the 'simple' fields one can change (no data structures here)
        """
        return self._keylist

    def get(self, key):
        """
        Allow to get variables
        """
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        obj_json = self._get_json()
        try:
            val = obj_json[key]
            if type(val) == unicode:
                val = str(val)
            if not bool(val):
                try:
                    if self._keylist[key] == type(''):
                        val = ''
                    if self._keylist[key] == type(0):
                        val = 0
                except:
                    pass
            return val
        except:
            return None

    def set(self, key, value):
        """
        Allow to set variables from keylist
        """
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        try:
            val_type = self._keylist[key]
        except:
            self._logger.error("No such key '{}' for the given object".format(key))
            return None
        if not bool(key) or type(key) is not str:
            self._logger.error("Field should be specified")
            return None
        obj_json = self._get_json()
        if not obj_json:
            self._logger.error("No json for the given object")
            return None
        if type(value) is not val_type:
            self._logger.error("Value '{}' should be '{}' type".format(key, val_type))
            return None
        if type(value) is str:
            value = unicode(value, "utf-8")
        mongo_doc = {key: value}
        self._mongo_collection.update({'_id': self._id}, {'$set': mongo_doc}, multi=False, upsert=False)
        return True

    def rename(self, name):
        """
        Rename object
        """
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        mongo_doc = self._mongo_collection.find_one({'name': name})
        if mongo_doc:
            self._logger.error("Object '{}' exists already".format(name))
            return None
        self._mongo_collection.update({'_id': self._id}, {'$set': {'name': name}}, multi=False, upsert=False)
        self._name = name
        return True

    def link(self, remote_dbref):
        """
        Unlink objects in MongoDB
        """
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        try:
            remote_dbref = remote_dbref.DBRef
        except:
            pass
        if type(remote_dbref) is not type(self._DBRef):
            self._logger.error("Passed argument is not DBRef type")
            return None
        if remote_dbref == self._DBRef:
            self._logger.error("Cant operate with the link to the same object")
            return None
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        remote_mongo_collection = self._mongo_db[remote_dbref.collection]
        use_doc = self._mongo_collection.find_one({'_id': self._id},{use_key: 1, '_id':0})
        usedby_doc = remote_mongo_collection.find_one({'_id': remote_dbref.id},{usedby_key: 1, '_id':0})
        try:
            use_doc = use_doc[use_key]
        except:
            use_doc = {}
        try:
            usedby_doc = usedby_doc[usedby_key]
        except:
            usedby_doc = {}
        try:
            link_count = use_doc[remote_dbref.collection][str(remote_dbref.id)]
        except:
            link_count = 0
        try:
            back_link_count = usedby_doc[self._DBRef.collection][str(self._DBRef.id)]
        except:
            back_link_count = 0
        link_count += 1
        back_link_count += 1
        try:
            use_doc[remote_dbref.collection][str(remote_dbref.id)] = link_count
        except:
            use_doc[remote_dbref.collection] = {}
            use_doc[remote_dbref.collection][str(remote_dbref.id)] = link_count
        try:
            usedby_doc[self._DBRef.collection][str(self._DBRef.id)] = back_link_count
        except:
            usedby_doc[self._DBRef.collection] = {}
            usedby_doc[self._DBRef.collection][str(self._DBRef.id)] = back_link_count
        self._mongo_collection.update({'_id': self._id}, {'$set': {use_key: use_doc} })
        remote_mongo_collection.update({'_id': remote_dbref.id},  {'$set': {usedby_key: usedby_doc} })

    def unlink(self, remote_dbref):
        """
        Link objects in MongoDB
        """
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        try:
            remote_dbref = remote_dbref.DBRef
        except:
            pass
        if type(remote_dbref) is not type(self._DBRef):
            self._logger.error("Passed argument is not DBRef type")
            raise RuntimeError
            return None
        if remote_dbref == self._DBRef:
            self._logger.error("Cant operate with the link to the same object")
            return None
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        remote_mongo_collection = self._mongo_db[remote_dbref.collection]
        use_doc = self._mongo_collection.find_one({'_id': self._id},{use_key: 1, '_id':0})
        usedby_doc = remote_mongo_collection.find_one({'_id': remote_dbref.id},{usedby_key: 1, '_id':0})
        try:
            use_doc = use_doc[use_key]
        except:
            use_doc = {}
        try:
            usedby_doc = usedby_doc[usedby_key]
        except:
            usedby_doc = {}
        try:
            link_count = use_doc[remote_dbref.collection][str(remote_dbref.id)]
        except:
            link_count = 0
        try:
            back_link_count = usedby_doc[self._DBRef.collection][str(self._DBRef.id)]
        except:
            back_link_count = 0
        if link_count < 1:
            self._logger.error("No links to this object. Cannot unlink.")
            return None
        if back_link_count < 1:
            self._logger.error("Link to this objct exists, but no backlinks to this object. Cannot unlink.")
            return None
        link_count -= 1
        back_link_count -= 1
        if link_count < 1:
            use_doc[remote_dbref.collection].pop(str(remote_dbref.id))
            if len(use_doc[remote_dbref.collection]) < 1:
                use_doc.pop(remote_dbref.collection)
        else:
            use_doc[remote_dbref.collection][str(remote_dbref.id)] = link_count
        if back_link_count < 1:
            usedby_doc[self._DBRef.collection].pop(str(self._DBRef.id))
            if len(usedby_doc[self._DBRef.collection]) < 1:
                usedby_doc.pop(self._DBRef.collection)
        else:
            usedby_doc[self._DBRef.collection][str(self._DBRef.id)] = back_link_count
        self._mongo_collection.update({'_id': self._id}, {'$set': {use_key: use_doc } })
        remote_mongo_collection.update({'_id': remote_dbref.id},  {'$set': {usedby_key: usedby_doc} })

    def get_links(self, resolve=False, collection = None):
        """
        Enumerates all references
        """
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        use_doc = self._mongo_collection.find_one({'_id': self._id},{use_key: 1, '_id':0})
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
                remote_mongo_collection = self._mongo_db[dbref.collection]
                if not resolve:
                    name = str(dbref.id)
                else:
                    try:
                        name = remote_mongo_collection.find_one({'_id': dbref.id})['name']
                    except:
                        name = str(dbref.id)
                output.extend([{'collection': dbref.collection, 'name': name, 'DBRef': dbref}])
        return output

    def get_back_links(self, resolve=False, collection = None):
        """
        Enumerates all reverse references
        """
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        usedby_doc = self._mongo_collection.find_one({'_id': self._id},{usedby_key: 1, '_id':0})
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
                remote_mongo_collection = self._mongo_db[dbref.collection]
                if not resolve:
                    name = str(dbref.id)
                else:
                    try:
                        name = remote_mongo_collection.find_one({'_id': dbref.id})['name']
                    except:
                        name = str(dbref.id)
                output.extend([{'collection': dbref.collection, 'name': name, 'DBRef': dbref}])
        return output

    def delete(self):
        """
        Is used to delete the document from MongoDB.
        """
        self._logger.debug("Arguments to function '{}".format(self._debug_function()))
        if not self._id:
            self._logger.error("Was object deleted?")
            return None
        links = self.get_links(resolve=True)
        back_links = self.get_back_links(resolve=True)
        if len(back_links) > 0:
            self._logger.error("Current object is being written as a dependency for the following objects:")
            for elem in back_links:
                try:
                    name = elem['DBRef'].id
                    collection = elem['DBRef'].collection
                    name = elem['name']
                    collection = elem['collection']
                except:
                    pass
                self._logger.error("[{}/{}]".format(collection, name))
            return None
        for link in links:
            self.unlink(link['DBRef'])
        ret = self._mongo_collection.remove({'_id': self._id}, multi=False)
        self._wipe_vars()
        return not 'err' in ret
