#!/usr/bin/env python
"""Event Man(ager)

Your friendly manager of attendants at a conference.
"""

import os
import json
import datetime

import tornado.httpserver
import tornado.ioloop
import tornado.options
from tornado.options import define, options
import tornado.web
from tornado import gen, escape

import backend


class BaseHandler(tornado.web.RequestHandler):
    def initialize(self, **kwargs):
        for key, value in kwargs.iteritems():
            setattr(self, key, value)


class RootHandler(BaseHandler):
    angular_app_path = os.path.join(os.path.dirname(__file__), "angular_app")
    @gen.coroutine
    def get(self):
        with open(self.angular_app_path + "/index.html", 'r') as fd:
            self.write(fd.read())


class ImprovedEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime.datetime):
            return str(o)
        return json.JSONEncoder.default(self, o)

json._default_encoder = ImprovedEncoder()


class CollectionHandler(BaseHandler):
    collection = None

    @gen.coroutine
    def get(self, id_=None):
        if id_ is not None:
            self.write(self.db.get(self.collection, id_))
        else:
            self.write({self.collection: self.db.query(self.collection)})

    @gen.coroutine
    def post(self, id_=None, **kwargs):
        data = escape.json_decode(self.request.body or {})
        if id_ is None:
            newData = self.db.add(self.collection, data)
        else:
            newData = self.db.update(self.collection, id_, data)
        self.write(newData)

    put = post

class PersonsHandler(CollectionHandler):
    collection = 'persons'

class EventsHandler(CollectionHandler):
    collection = 'events'


def main():
    define("port", default=5242, help="run on the given port", type=int)
    define("data", default=os.path.join(os.path.dirname(__file__), "data"),
            help="specify the directory used to store the data")
    define("mongodbURL", default=None,
            help="URL to MongoDB server", type=str)
    define("dbName", default='eventman',
            help="Name of the MongoDB database to use", type=str)
    define("debug", default=False, help="run in debug mode")
    define("config", help="read configuration file",
            callback=lambda path: tornado.options.parse_config_file(path, final=False))
    tornado.options.parse_command_line()

    db_connector = backend.EventManDB(url=options.mongodbURL, dbName=options.dbName)
    init_params = dict(db=db_connector)

    application = tornado.web.Application([
            (r"/persons/?(?P<id_>\w+)?", PersonsHandler, init_params),
            (r"/events/?(?P<id_>\w+)?", EventsHandler, init_params),
            (r"/(?:index.html)?", RootHandler, init_params),
            (r'/(.*)', tornado.web.StaticFileHandler, {"path": "angular_app"})
        ],
        template_path=os.path.join(os.path.dirname(__file__), "templates"),
        static_path=os.path.join(os.path.dirname(__file__), "static"),
        debug=options.debug)
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == '__main__':
    main()

