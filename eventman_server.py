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

import tornado.httpserver
import tornado.ioloop
import tornado.options
from tornado.options import define, options
import tornado.web
from tornado import gen, escape

import utils
import backend


class BaseHandler(tornado.web.RequestHandler):
    """Base class for request handlers."""
    _bool_convert = {
        '0': False,
        'n': False,
        'f': False,
        'no': False,
        'off': False,
        'false': False
    }

    def tobool(self, obj):
        if isinstance(obj, (list, tuple)):
            obj = obj[0]
        if isinstance(obj, (str, unicode)):
            obj = obj.lower()
        return bool(self._bool_convert.get(obj, obj))

    def initialize(self, **kwargs):
        """Add every passed (key, value) as attributes of the instance."""
        for key, value in kwargs.iteritems():
            setattr(self, key, value)


class RootHandler(BaseHandler):
    """Handler for the / path."""
    angular_app_path = os.path.join(os.path.dirname(__file__), "angular_app")

    @gen.coroutine
    def get(self, *args, **kwargs):
        # serve the ./angular_app/index.html file
        with open(self.angular_app_path + "/index.html", 'r') as fd:
            self.write(fd.read())


class CollectionHandler(BaseHandler):
    """Base class for handlers that need to interact with the database backend.
    
    Introduce basic CRUD operations."""
    # set of documents we're managing (a collection in MongoDB or a table in a SQL database)
    collection = None

    def _filter_results(self, results, params):
        """Filter a list using keys and values from a dictionary.
        
        :param results: the list to be filtered
        :type results: list
        :param params: a dictionary of items that must all be present in an original list item to be included in the return
        
        :return: list of items that have all the keys with the same values as params
        :rtype: list"""
        if not params:
            return results
        filtered = []
        for result in results:
            add = True
            for key, value in params.iteritems():
                if key not in result or result[key] != value:
                    add = False
                    break
            if add:
                filtered.append(result)
        return filtered

    # A property to access the first value of each argument.
    arguments = property(lambda self: dict([(k, v[0])
        for k, v in self.request.arguments.iteritems()]))

    @gen.coroutine
    def get(self, id_=None, resource=None, resource_id=None, **kwargs):
        if resource:
            # Handle access to sub-resources.
            method = getattr(self, 'handle_get_%s' % resource, None)
            if method and callable(method):
                self.write(method(id_, resource_id, **kwargs))
                return
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
    def post(self, id_=None, resource=None, resource_id=None, **kwargs):
        data = escape.json_decode(self.request.body or '{}')
        if resource:
            # Handle access to sub-resources.
            method = getattr(self, 'handle_%s_%s' % (self.request.method.lower(), resource), None)
            if method and callable(method):
                self.write(method(id_, resource_id, data, **kwargs))
                return
        if id_ is None:
            newData = self.db.add(self.collection, data)
        else:
            merged, newData = self.db.update(self.collection, id_, data)
        self.write(newData)

    # PUT (update an existing document) is handled by the POST (create a new document) method
    put = post

    @gen.coroutine
    def delete(self, id_=None, resource=None, resource_id=None, **kwargs):
        if resource:
            # Handle access to sub-resources.
            method = getattr(self, 'handle_delete_%s' % resource, None)
            if method and callable(method):
                self.write(method(id_, resource_id, **kwargs))
                return
        if id_:
            self.db.delete(self.collection, id_)
        self.write({'success': True})


class PersonsHandler(CollectionHandler):
    """Handle requests for Persons."""
    collection = 'persons'
    object_id = 'person_id'

    def handle_get_events(self, id_, resource_id=None, **kwargs):
        # Get a list of events attended by this person.
        # Inside the data of each event, a 'person_data' dictionary is
        # created, duplicating the entry for the current person (so that
        # there's no need to parse the 'persons' list on the client).
        #
        # If resource_id is given, only the specified event is considered.
        #
        # If the 'all' parameter is given, every event (also unattended ones) is returned.
        args = self.request.arguments
        query = {}
        if id_ and not self.tobool(args.get('all')):
            query = {'persons.person_id': id_}
        if resource_id:
            query['_id'] = resource_id

        events = self.db.query('events', query)
        for event in events:
            person_data = {}
            for persons in event.get('persons') or []:
                if str(persons.get('person_id')) == id_:
                    person_data = persons
                    break
            event['person_data'] = person_data
        if resource_id and events:
            return events[0]
        return {'events': events}


class EventsHandler(CollectionHandler):
    """Handle requests for Events."""
    collection = 'events'
    object_id = 'event_id'

    def handle_get_persons(self, id_, resource_id=None):
        # Return every person registered at this event, or the information
        # about a specific person.
        query = {'_id': id_}
        event = self.db.query('events', query)[0]
        if resource_id:
            for person in event.get('persons', []):
                if str(person.get('person_id')) == resource_id:
                    return {'person': person}
        if resource_id:
            return {'person': {}}
        persons = self._filter_results(event.get('persons') or [], self.arguments)
        return {'persons': persons}

    def handle_post_persons(self, id_, person_id, data):
        # Add a person to the list of persons registered at this event.
        doc = self.db.query('events',
                {'_id': id_, 'persons.person_id': person_id})
        if '_id' in data:
            del data['_id']
        if not doc:
            merged, doc = self.db.update('events',
                    {'_id': id_},
                    {'persons': data},
                    operation='append',
                    create=False)
        return {'event': doc}

    def handle_put_persons(self, id_, person_id, data):
        # Update an existing entry for a person registered at this event.
        query = dict([('persons.%s' % k, v) for k, v in self.arguments.iteritems()])
        query['_id'] = id_
        if person_id is not None:
            query['persons.person_id'] = person_id
        merged, doc = self.db.update('events', query,
                data, updateList='persons', create=False)
        return {'event': doc}

    def handle_delete_persons(self, id_, person_id):
        # Remove a specific person from the list of persons registered at this event.
        merged, doc = self.db.update('events',
                {'_id': id_},
                {'persons': {'person_id': person_id}},
                operation='delete',
                create=False)
        return {'event': doc}


class EbCSVImportPersonsHandler(BaseHandler):
    """Importer for CSV files exported from eventbrite."""
    csvRemap = {
        'Nome evento': 'event_title',
        'ID evento': 'event_id',
        'N. codice a barre': 'ebqrcode',
        'Cognome acquirente': 'surname',
        'Nome acquirente': 'name',
        'E-mail acquirente': 'email',
        'Cognome': 'surname',
        'Nome': 'name',
        'E-mail': 'email',
        'Indirizzo e-mail': 'email',
        'Tipologia biglietto': 'ticket_kind',
        'Data partecipazione': 'attending_datetime',
        'Data check-in': 'checkin_datetime',
        'Ordine n.': 'order_nr',
        'ID ordine': 'order_nr',
        'Prefisso (Sig., Sig.ra, ecc.)': 'name_title',
    }
    keepPersonData = ('name', 'surname', 'email', 'name_title')

    @gen.coroutine
    def post(self, **kwargs):
        targetEvent = None
        try:
            targetEvent = self.get_body_argument('targetEvent')
        except:
            pass
        reply = dict(total=0, valid=0, merged=0, new_in_event=0)
        for fieldname, contents in self.request.files.iteritems():
            for content in contents:
                filename = content['filename']
                parseStats, persons = utils.csvParse(content['body'], remap=self.csvRemap)
                reply['total'] += parseStats['total']
                reply['valid'] += parseStats['valid']
                for person in persons:
                    person_data = dict([(k, person[k]) for k in self.keepPersonData
                        if k in person])
                    merged, person = self.db.update('persons',
                            [('email',), ('name', 'surname')],
                            person_data)
                    if merged:
                        reply['merged'] += 1
                    if targetEvent and person:
                        event_id = targetEvent
                        person_id = person['_id']
                        registered_data = {
                                'person_id': person_id,
                                'attended': False,
                                'from_file': filename}
                        person.update(registered_data)
                        if not self.db.query('events',
                                {'_id': event_id, 'persons.person_id': person_id}):
                            self.db.update('events', {'_id': event_id},
                                    {'persons': person},
                                    operation='appendUnique')
                            reply['new_in_event'] += 1
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
            (r"/persons/?(?P<id_>\w+)?/?(?P<resource>\w+)?/?(?P<resource_id>\w+)?", PersonsHandler, init_params),
            (r"/events/?(?P<id_>\w+)?/?(?P<resource>\w+)?/?(?P<resource_id>\w+)?", EventsHandler, init_params),
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

