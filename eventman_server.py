#!/usr/bin/env python
"""Event Man(ager)

Your friendly manager of attendees at an event.

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

import os
import csv
import json
import StringIO
import datetime

import tornado.httpserver
import tornado.ioloop
import tornado.options
from tornado.options import define, options
import tornado.web
from tornado import gen, escape

import backend


class ImprovedEncoder(json.JSONEncoder):
    """Enhance the default JSON encoder to serialize datetime objects."""
    def default(self, o):
        if isinstance(o, (datetime.datetime, datetime.date,
                datetime.time, datetime.timedelta)):
            return str(o)
        return json.JSONEncoder.default(self, o)

json._default_encoder = ImprovedEncoder()


class BaseHandler(tornado.web.RequestHandler):
    """Base class for request handlers."""
    def initialize(self, **kwargs):
        """Add every passed (key, value) as attributes of the instance."""
        for key, value in kwargs.iteritems():
            setattr(self, key, value)


class RootHandler(BaseHandler):
    """Handler for the / path."""
    angular_app_path = os.path.join(os.path.dirname(__file__), "angular_app")

    @gen.coroutine
    def get(self):
        # serve the ./angular_app/index.html file
        with open(self.angular_app_path + "/index.html", 'r') as fd:
            self.write(fd.read())


class CollectionHandler(BaseHandler):
    """Base class for handlers that need to interact with the database backend.
    
    Introduce basic CRUD operations."""
    # set of documents we're managing (a collection in MongoDB or a table in a SQL database)
    collection = None

    @gen.coroutine
    def get(self, id_=None):
        if id_ is not None:
            # read a single document
            self.write(self.db.get(self.collection, id_))
        else:
            # return an object containing the list of all objects in the collection;
            # e.g.: {'events': [{'_id': 'obj1-id, ...}, {'_id': 'obj2-id, ...}, ...]}
            # Please, never return JSON lists that are not encapsulated into an object,
            # to avoid XSS vulnerabilities.
            self.write({self.collection: self.db.query(self.collection)})

    @gen.coroutine
    def post(self, id_=None, **kwargs):
        data = escape.json_decode(self.request.body or {})
        if id_ is None:
            # insert a new document
            newData = self.db.add(self.collection, data)
        else:
            # update an existing document
            newData = self.db.update(self.collection, id_, data)
        self.write(newData)

    # PUT (update an existing document) is handled by the POST (create a new document) method
    put = post

    @gen.coroutine
    def delete(self, id_=None, **kwargs):
        self.db.delete(self.collection, id_)


class PersonsHandler(CollectionHandler):
    """Handle requests for Persons."""
    collection = 'persons'


class EventsHandler(CollectionHandler):
    """Handle requests for Events."""
    collection = 'events'


class ImportPersonsHandler(BaseHandler):
    pass


def csvParse(csvStr, remap=None):
    fd = StringIO.StringIO(csvStr)
    reader = csv.reader(fd)
    fields = 0
    reply = dict(total=0, valid=0)
    results = []
    try:
        headers = reader.next()
        fields = len(headers)
    except (StopIteration, csv.Error):
        return reply, {}
    if remap:
        for idx, header in enumerate(headers):
            if header in remap:
                headers[idx] = remap[header]
    for row in reader:
        try:
            reply['total'] += 1
            if len(row) != fields:
                continue
            results.append(dict(map(None, headers, row)))
            reply['valid'] += 1
        except csv.Error:
            continue
    fd.close()
    return reply, results


class EbCSVImportPersonsHandler(ImportPersonsHandler):
    csvRemap = {
        'Nome evento': 'event_title',
        'ID evento': 'event_id',
        'N. codice a barre': 'ebqrcode',
        'Cognome acquirente': 'surname',
        'Nome acquirente': 'name',
        'E-mail acquirente': 'email',
        'Cognome': 'lowercase_surname',
        'Nome': 'lowercase_name',
        'E-mail': 'lowercase_email',
        'Tipologia biglietto': 'ticket_kind',
        'Data partecipazione': 'attending_datetime',
        'Data check-in': 'checkin_datetime',
        'Ordine n.': 'order_nr',
    }
    @gen.coroutine
    def post(self, **kwargs):
        print kwargs
        targetEvent = None
        try:
            targetEvent = self.get_body_argument('targetEvent')
        except:
            pass
        reply = dict(total=0, valid=0, merged=0)
        for fieldname, contents in self.request.files.iteritems():
            print fieldname
            for content in contents:
                print content.keys()
                filename = content['filename']
                parseStats, result = csvParse(content['body'], remap=self.csvRemap)
                reply['total'] += parseStats['total']
                reply['valid'] += parseStats['valid']
                print filename
        print reply
        self.write(reply)


def run():
    """Run the Tornado web application."""
    # command line arguments; can also be written in a configuration file,
    # specified with the --config argument.
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

    # database backend connector
    db_connector = backend.EventManDB(url=options.mongodbURL, dbName=options.dbName)
    init_params = dict(db=db_connector)

    application = tornado.web.Application([
            (r"/persons/?(?P<id_>\w+)?", PersonsHandler, init_params),
            (r"/events/?(?P<id_>\w+)?", EventsHandler, init_params),
            (r"/(?:index.html)?", RootHandler, init_params),
            (r"/ebcsvpersons", EbCSVImportPersonsHandler, init_params),
            (r'/(.*)', tornado.web.StaticFileHandler, {"path": "angular_app"})
        ],
        template_path=os.path.join(os.path.dirname(__file__), "templates"),
        static_path=os.path.join(os.path.dirname(__file__), "static"),
        debug=options.debug)
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == '__main__':
    run()

