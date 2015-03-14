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

class MainHandler(tornado.web.RequestHandler):
    @gen.coroutine
    def get(self):
        self.redirect('/index.html')

MOCKUP_PERSONS = [
    {'name': 'Silvia', 'surname': 'Castellari',
     'email': 'hackinbo.it@gmail.com',
     'id': 1},
    {'name': 'Daniele', 'surname': 'Castellari',
     'email': 'hackinbo.it@gmail.com',
     'id': 2},
    {'name': 'Mario', 'surname': 'Anglani',
     'email': 'hackinbo.it@gmail.com',
     'id': 3}]


class PersonsHandler(tornado.web.RequestHandler):
    @gen.coroutine
    def get(self, id_=None):
        self.write({'persons': MOCKUP_PERSONS})

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
            (r"/", MainHandler),
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

