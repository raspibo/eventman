"""Event Man(ager) backend

Classes and functions used to manage events and attendants.
"""

import pymongo


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

    def get(self, collection, id_):
        results = self.query(collection, {'id': id_})
        print results, id_, type(id_)
        return results and results[0] or {}

    def query(self, collection, query=None):
        db = self.connect()
        results = list(db[collection].find(query or {}))
        for result in results:
            result['_id'] = str(result['_id'])
        return results

    def add(self, collection, data):
        db = self.connect()
        _id = db[collection].insert(data)
        newData = db[collection].find_one({'_id': _id})
        newData['_id'] = str(newData['_id'])
        return newData

    #def update(self, collection)

    def addUser(self, user):
        db = self.connect()
        db.users.insert(user)

    def addEvent(self, event):
        db = self.connect()
        db.events.insert(event)

    def getUser(self, query=None):
        db = self.connect()
        return db.users.find_one(query or {})

    def getEvent(self, query):
        db = self.connect()
        return db.events.find_one(query or {})

    def getUsers(self, eventID=None):
        self.connect()
        pass

    def getEvents(self):
        self.connect()
        pass




