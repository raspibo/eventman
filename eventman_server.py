#!/usr/bin/env python
"""Event Man(ager)

Your friendly manager of attendants at a conference.
"""

import os

import tornado.httpserver
import tornado.ioloop
import tornado.options
from tornado.options import define, options
import tornado.web
from tornado import gen

class RootHandler(tornado.web.RequestHandler):
    angular_app_path = os.path.join(os.path.dirname(__file__), "angular_app")
    @gen.coroutine
    def get(self):
        with open(self.angular_app_path + "/index.html", 'r') as fd:
            self.write(fd.read())

MOCKUP_PERSONS = {
    1: {'name': 'Silvia', 'surname': 'Castellari',
     'email': 'hackinbo.it@gmail.com',
     'id': 1},
    2: {'name': 'Daniele', 'surname': 'Castellari',
     'email': 'hackinbo.it@gmail.com',
     'id': 2},
    3: {'name': 'Mario', 'surname': 'Anglani',
     'email': 'hackinbo.it@gmail.com',
     'id': 3}
}

import datetime
MOCKUP_EVENTS = {
    1: {'title': 'HackInBo 2015', 'begin-datetime': datetime.datetime(2015, 5, 23, 9, 0),
        'end-datetime': datetime.datetime(2015, 5, 24, 17, 0),
        'location': 'Bologna', 'id': 1},
    2: {'title': 'La fiera del carciofo', 'begin-datetime': datetime.datetime(2015, 6, 23, 9, 0),
        'end-datetime': datetime.datetime(2015, 6, 24, 17, 0),
        'location': 'Gatteo a mare', 'id': 2},
}

import json

class ImprovedEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime.datetime):
            return str(o)
        return json.JSONEncoder.default(self, o)

json._default_encoder = ImprovedEncoder()


class PersonsHandler(tornado.web.RequestHandler):
    @gen.coroutine
    def get(self, id_=None):
        if id_ is not None:
            self.write({'person': MOCKUP_PERSONS[int(id_)]})
            return
        self.write({'persons': MOCKUP_PERSONS.values()})


class EventsHandler(tornado.web.RequestHandler):
    @gen.coroutine
    def get(self, id_=None):
        if id_ is not None:
            self.write({'event': MOCKUP_EVENTS[int(id_)]})
            return
        self.write({'events': MOCKUP_EVENTS.values()})



def main():
    define("port", default=5242, help="run on the given port", type=int)
    define("data", default=os.path.join(os.path.dirname(__file__), "data"),
            help="specify the directory used to store the data")
    define("debug", default=False, help="run in debug mode")
    define("config", help="read configuration file",
            callback=lambda path: tornado.options.parse_config_file(path, final=False))
    tornado.options.parse_command_line()

    application = tornado.web.Application([
            (r"/persons/?(?P<id_>\d+)?", PersonsHandler),
            (r"/events/?(?P<id_>\d+)?", EventsHandler),
            (r"/(?:index.html)?", RootHandler),
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

