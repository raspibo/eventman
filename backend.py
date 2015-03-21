"""Event Man(ager) backend

Classes and functions used to manage events and attendants.
"""

import pymongo
from bson.objectid import ObjectId


class EventManDB(object):
    db = None
    connection = None

    def __init__(self, url=None, dbName='eventman'):
        self._url = url
        self._dbName = dbName
        self.connect(url)

    def connect(self, url=None, dbName=None):
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
        if not isinstance(_id, ObjectId):
            _id = ObjectId(_id)
        results = self.query(collection, {'_id': _id})
        return results and results[0] or {}

    def query(self, collection, query=None):
        db = self.connect()
        query = query or {}
        if'_id' in query and not isinstance(query['_id'], ObjectId):
            query['_id'] = ObjectId(query['_id'])
        results = list(db[collection].find(query))
        for result in results:
            result['_id'] = str(result['_id'])
        return results

    def add(self, collection, data):
        db = self.connect()
        _id = db[collection].insert(data)
        return self.get(collection, _id)

    def update(self, collection, _id, data):
        db = self.connect()
        data = data or {}
        if '_id' in data:
            del data['_id']
        db[collection].update({'_id': ObjectId(_id)}, {'$set': data})
        return self.get(collection, _id)

