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
        self.redirect('/static/html/index.html')


def main():
    define("port", default=5242, help="run on the given port", type=int)
    define("config", help="read configuration file",
            callback=lambda path: tornado.options.parse_config_file(path, final=False))
    define("debug", default=False, help="run in debug mode")
    tornado.options.parse_command_line()

    application = tornado.web.Application([
            (r"/(?:index.html)?", MainHandler),
        ],
        template_path=os.path.join(os.path.dirname(__file__), "templates"),
        static_path=os.path.join(os.path.dirname(__file__), "static"),
        debug=options.debug)
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == '__main__':
    main()

