"""EventMan(ager) database backend

Classes and functions used to manage events and attendees database.

Copyright 2015-2016 Davide Alberani <da@erlug.linux.it>
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

_force_conversion = {
    'seq_hex': str,
    'tickets.seq_hex': str
}


def convert_obj(obj):
    """Convert an object in a format suitable to be stored in MongoDB.

    :param obj: object to convert

    :returns: object that can be stored in MongoDB.
    """
    if obj is None:
        return None
    if isinstance(obj, bool):
        return obj
    try:
        return ObjectId(obj)
    except:
        pass
    return obj


def convert(seq):
    """Convert an object to a format suitable to be stored in MongoDB,
    descending lists, tuples and dictionaries (a copy is returned).

    :param seq: sequence or object to convert

    :returns: object that can be stored in MongoDB.
    """
    if isinstance(seq, dict):
        d = {}
        for key, item in seq.iteritems():
            if key in _force_conversion:
                d[key] = _force_conversion[key](item)
            else:
                d[key] = convert(item)
        return d
    if isinstance(seq, (list, tuple)):
        return [convert(x) for x in seq]
    return convert_obj(seq)


class EventManDB(object):
    """MongoDB connector."""
    db = None
    connection = None

    # map operations on lists of items.
    _operations = {
            'update': '$set',
            'append': '$push',
            'appendUnique': '$addToSet',
            'delete': '$pull',
            'increment': '$inc'
    }

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

        :returns: the database we're connected to
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

    def get(self, collection, _id):
        """Get a single document with the specified `_id`.

        :param collection: search the document in this collection
        :type collection: str
        :param _id: unique ID of the document
        :type _id: str or :class:`~bson.objectid.ObjectId`

        :returns: the document with the given `_id`
        :rtype: dict
        """
        results = self.query(collection, convert({'_id': _id}))
        return results and results[0] or {}

    def query(self, collection, query=None, condition='or'):
        """Get multiple documents matching a query.

        :param collection: search for documents in this collection
        :type collection: str
        :param query: search for documents with those attributes
        :type query: dict or None

        :returns: list of matching documents
        :rtype: list
        """
        db = self.connect()
        query = convert(query or {})
        if isinstance(query, (list, tuple)):
            query = {'$%s' % condition: query}
        return list(db[collection].find(query))

    def add(self, collection, data, _id=None):
        """Insert a new document.

        :param collection: insert the document in this collection
        :type collection: str
        :param data: the document to store
        :type data: dict
        :param _id: the _id of the document to store; if None, it's generated
        :type _id: object

        :returns: the document, as created in the database
        :rtype: dict
        """
        db = self.connect()
        data = convert(data)
        if _id is not None:
            data['_id'] = _id
        _id = db[collection].insert(data)
        return self.get(collection, _id)

    def insertOne(self, collection, data):
        """Insert a document, avoiding duplicates.

        :param collection: update a document in this collection
        :type collection: str
        :param data: the document information to store
        :type data: dict

        :returns: True if the document was already present
        :rtype: bool
        """
        db = self.connect()
        data = convert(data)
        ret = db[collection].update(data, {'$set': data}, upsert=True)
        return ret['updatedExisting']

    def _buildSearchPattern(self, data, searchBy):
        """Return an OR condition."""
        _or = []
        for searchPattern in searchBy:
            try:
                _or.append(dict([(k, data[k]) for k in searchPattern if k in data]))
            except KeyError:
                continue
        return _or

    def update(self, collection, _id_or_query, data, operation='update',
            updateList=None, create=True):
        """Update an existing document or create it, if requested.
        _id_or_query can be an ID, a dict representing a query or a list of tuples.
        In the latter case, the tuples are put in OR; a tuple match if all of its
        items from 'data' are contained in the document.

        :param collection: update a document in this collection
        :type collection: str
        :param _id_or_query: ID of the document to be updated, or a query or a list of attributes in the data that must match
        :type _id_or_query: str or :class:`~bson.objectid.ObjectId` or iterable
        :param data: the updated information to store
        :type data: dict
        :param operation: operation used to update the document or a portion of it, like a list (update, append, appendUnique, delete, increment)
        :type operation: str
        :param updateList: if set, it's considered the name of a list (the first matching element will be updated)
        :type updateList: str
        :param create: if True, the document is created if no document matches
        :type create: bool

        :returns: a boolean (True if an existing document was updated) and the document after the update
        :rtype: tuple of (bool, dict)
        """
        db = self.connect()
        data = convert(data or {})
        _id_or_query = convert(_id_or_query)
        if isinstance(_id_or_query, (list, tuple)):
            _id_or_query = {'$or': self._buildSearchPattern(data, _id_or_query)}
        elif not isinstance(_id_or_query, dict):
            _id_or_query = {'_id': _id_or_query}
        if '_id' in data:
            del data['_id']
        operator = self._operations.get(operation)
        if updateList:
            newData = {}
            for key, value in data.iteritems():
                newData['%s.$.%s' % (updateList, key)] = value
            data = newData
        res = db[collection].find_and_modify(query=_id_or_query,
                update={operator: data}, full_response=True, new=True, upsert=create)
        lastErrorObject = res.get('lastErrorObject') or {}
        return lastErrorObject.get('updatedExisting', False), res.get('value') or {}

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
        _id_or_query = convert(_id_or_query)
        db[collection].remove(_id_or_query)

