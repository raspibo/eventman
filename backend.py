"""Event Man(ager) database backend

Classes and functions used to manage events and attendees database.

Copyright 2015 Davide Alberani <da@erlug.linux.it>
               RaspiBO <info@raspibo.org>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import re
import pymongo
from bson.objectid import ObjectId

re_objectid = re.compile(r'[0-9a-f]{24}')

class EventManDB(object):
    """MongoDB connector."""
    db = None
    connection = None

    def __init__(self, url=None, dbName='eventman'):
        """Initialize the instance, connecting to the database.

        :param url: URL of the database
        :type url: str (or None to connect to localhost)
        """
        self._url = url
        self._dbName = dbName
        self.connect(url)

    def connect(self, url=None, dbName=None):
        """Connect to the database.

        :param url: URL of the database
        :type url: str (or None to connect to localhost)

        :return: the database we're connected to
        :rtype: :class:`~pymongo.database.Database`
        """
        if self.db is not None:
            return self.db
        if url:
            self._url = url
        if dbName:
            self._dbName = dbName
        self.connection = pymongo.MongoClient(self._url)
        self.db = self.connection[self._dbName]
        return self.db

    def convert_obj(self, obj):
        """Convert a string to an object for MongoDB.

        :param obj: object to convert
        """
        try:
            return ObjectId(obj)
        except:
            pass
        try:
            return int(obj)
        except:
            pass
        return obj

    def convert(self, seq):
        if isinstance(seq, dict):
            d = {}
            for key, item in seq.iteritems():
                d[key] = self.convert(item)
            return d
        if isinstance(seq, (list, tuple)):
            return [self.convert(x) for x in seq]
        return self.convert_obj(seq)

    def get(self, collection, _id):
        """Get a single document with the specified `_id`.

        :param collection: search the document in this collection
        :type collection: str
        :param _id: unique ID of the document
        :type _id: str or :class:`~bson.objectid.ObjectId`

        :return: the document with the given `_id`
        :rtype: dict
        """
        results = self.query(collection, self.convert({'_id': _id}))
        return results and results[0] or {}

    def query(self, collection, query=None):
        """Get multiple documents matching a query.

        :param collection: search for documents in this collection
        :type collection: str
        :param query: search for documents with those attributes
        :type query: dict or None

        :return: list of matching documents
        :rtype: list
        """
        db = self.connect()
        query = self.convert(query or {})
        return list(db[collection].find(query))

    def add(self, collection, data):
        """Insert a new document.

        :param collection: insert the document in this collection
        :type collection: str
        :param data: the document to store
        :type data: dict

        :return: the document, as created in the database
        :rtype: dict
        """
        db = self.connect()
        _id = db[collection].insert(data)
        return self.get(collection, _id)

    def insertOne(self, collection, data):
        """Insert a document, avoiding duplicates.

        :param collection: update a document in this collection
        :type collection: str
        :param data: the document information to store
        :type data: dict

        :return: True if the document was already present
        :rtype: bool
        """
        db = self.connect()
        ret = db[collection].update(data, {'$set': data}, upsert=True)
        return ret['updatedExisting']

    def update(self, collection, _id_or_query, data, operator='$set', create=True):
        """Update an existing document.

        :param collection: update a document in this collection
        :type collection: str
        :param _id: unique ID of the document to be updated
        :type _id: str or :class:`~bson.objectid.ObjectId`
        :param data: the updated information to store
        :type data: dict

        :return: the document, after the update
        :rtype: dict
        """
        db = self.connect()
        data = data or {}
        if _id_or_query is None:
            _id_or_query = {'_id': None}
        elif isinstance(_id_or_query, (list, tuple)):
            _id_or_query = {'$or': self.buildSearchPattern(data, _id_or_query)}
        elif not isinstance(_id_or_query, dict):
            _id_or_query = {'_id': _id_or_query}
        _id_or_query = self.convert(_id_or_query)
        if '_id' in data:
            del data['_id']
        data = self.convert(data)
        res = db[collection].find_and_modify(query=_id_or_query,
                update={operator: data}, full_response=True, new=True, upsert=create)
        lastErrorObject = res.get('lastErrorObject') or {}
        return lastErrorObject.get('updatedExisting', False), res.get('value') or {}

    def buildSearchPattern(self, data, searchBy):
        _or = []
        for searchPattern in searchBy:
            try:
                _or.append(dict([(k, data[k]) for k in searchPattern]))
            except KeyError:
                continue
        return _or

    def merge(self, collection, data, searchBy, operator='$set'):
        """Update an existing document.

        :param collection: update a document in this collection
        :type collection: str
        :param data: the document to store or merge with an existing one
        :type data: dict

        :return: a tuple with a boolean (True if an existing document was updated, and the _id of the document)
        :rtype: tuple
        """
        db = self.connect()
        _or = []
        for searchPattern in searchBy:
            try:
                _or.append(dict([(k, data[k]) for k in searchPattern]))
            except KeyError:
                continue
        if not _or:
            return False, None
        # Two-steps merge/find to count the number of merged documents
        ret = db[collection].update({'$or': _or}, {operator: data}, upsert=True)
        _id = ret.get('upserted')
        if _id is None:
            newDoc = db[collection].find_one(data)
            if newDoc:
                _id = newDoc['_id']
        return ret['updatedExisting'], _id

    def delete(self, collection, _id_or_query=None, force=False):
        """Remove one or more documents from a collection.

        :param collection: search the documents in this collection
        :type collection: str
        :param _id_or_query: unique ID of the document or query to match multiple documents
        :type _id_or_query: str or :class:`~bson.objectid.ObjectId` or dict
        :param force: force the deletion of all documents, when `_id_or_query` is empty
        :type force: bool
        """
        if not _id_or_query and not force:
            return
        db = self.connect()
        if not isinstance(_id_or_query, dict):
            _id_or_query = {'_id': _id_or_query}
        _id_or_query = self.convert(_id_or_query)
        db[collection].remove(_id_or_query)

