"""Event Man(ager) backend

Classes and functions used to manage events and attendants.
"""

import pymongo


class EventManDB(object):
    connection = None

    def __init__(self, url=None, dbName='eventman'):
        self._url = url
        self._dbName = dbName
        self.connect(url)

    def connect(self, url=None, dbName=None):
        if self.connection is not None:
            return self.connection
        if url:
            self._url = url
        if dbName:
            self._dbName = dbName
        self.connection = pymongo.MongoClient(self._url)
        self.db = self.connection[self._dbName]
        return self.db

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




