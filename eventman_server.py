#!/usr/bin/env python
"""Event Man(ager)

Your friendly manager of attendees at an event.

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

import os
import re
import glob
import json
import time
import string
import random
import logging
import datetime

import tornado.httpserver
import tornado.ioloop
import tornado.options
from tornado.options import define, options
import tornado.web
import tornado.websocket
from tornado import gen, escape, process

import utils
import backend

ENCODING = 'utf-8'
PROCESS_TIMEOUT = 60

API_VERSION = '1.0'

re_env_key = re.compile('[^A-Z_]+')
re_slashes = re.compile(r'//+')


def authenticated(method):
    """Decorator to handle authentication."""
    original_wrapper = tornado.web.authenticated(method)
    @tornado.web.functools.wraps(method)
    def my_wrapper(self, *args, **kwargs):
        # If no authentication was required from the command line or config file.
        if not self.authentication:
            return method(self, *args, **kwargs)
        # unauthenticated API calls gets redirected to /v1.0/[...]
        if self.is_api() and not self.current_user:
            self.redirect('/v%s%s' % (API_VERSION, self.get_login_url()))
            return
        return original_wrapper(self, *args, **kwargs)
    return my_wrapper


class BaseException(Exception):
    """Base class for EventMan custom exceptions.

    :param message: text message
    :type message: str
    :param status: numeric http status code
    :type status: int"""
    def __init__(self, message, status=400):
        super(BaseException, self).__init__(message)
        self.message = message
        self.status = status


class InputException(BaseException):
    """Exception raised by errors in input handling."""
    pass


class BaseHandler(tornado.web.RequestHandler):
    """Base class for request handlers."""
    permissions = {
        'event|read': True,
        'event:tickets|all': True,
        'event:tickets-all|create': True,
        'events|read': True,
        'persons|create': True,
        'person|create': True,
        'users|create': True
    }

    _users_cache = {}

    # A property to access the first value of each argument.
    arguments = property(lambda self: dict([(k, v[0])
        for k, v in self.request.arguments.iteritems()]))

    # A property to access both the UUID and the clean arguments.
    @property
    def uuid_arguments(self):
        uuid = None
        arguments = self.arguments
        if 'uuid' in arguments:
            uuid = arguments['uuid']
            del arguments['uuid']
        return uuid, arguments

    _bool_convert = {
        '0': False,
        'n': False,
        'f': False,
        'no': False,
        'off': False,
        'false': False,
        '1': True,
        'y': True,
        't': True,
        'on': True,
        'yes': True,
        'true': True
    }

    def write_error(self, status_code, **kwargs):
        """Default error handler."""
        if isinstance(kwargs.get('exc_info', (None, None))[1], BaseException):
            exc = kwargs['exc_info'][1]
            status_code = exc.status
            message = exc.message
        else:
            message = 'internal error'
        self.build_error(message, status=status_code)

    def is_api(self):
        """Return True if the path is from an API call."""
        return self.request.path.startswith('/v%s' % API_VERSION)

    def tobool(self, obj):
        """Convert some textual values to boolean."""
        if isinstance(obj, (list, tuple)):
            obj = obj[0]
        if isinstance(obj, (str, unicode)):
            obj = obj.lower()
        return self._bool_convert.get(obj, obj)

    def arguments_tobool(self):
        """Return a dictionary of arguments, converted to booleans where possible."""
        return dict([(k, self.tobool(v)) for k, v in self.arguments.iteritems()])

    def initialize(self, **kwargs):
        """Add every passed (key, value) as attributes of the instance."""
        for key, value in kwargs.iteritems():
            setattr(self, key, value)

    @property
    def current_user(self):
        """Retrieve current user name from the secure cookie."""
        return self.get_secure_cookie("user")

    @property
    def current_user_info(self):
        """Information about the current user, including their permissions."""
        current_user = self.current_user
        if current_user in self._users_cache:
            return self._users_cache[current_user]
        permissions = set([k for (k, v) in self.permissions.iteritems() if v is True])
        user_info = {'permissions': permissions}
        if current_user:
            user_info['username'] = current_user
            res = self.db.query('users', {'username': current_user})
            if res:
                user = res[0]
                user_info = user
                permissions.update(set(user.get('permissions') or []))
                user_info['permissions'] = permissions
        self._users_cache[current_user] = user_info
        return user_info

    def has_permission(self, permission):
        """Check permissions of the current user.

        :param permission: the permission to check
        :type permission: str

        :returns: True if the user is allowed to perform the action or False
        :rtype: bool
        """
        user_info = self.current_user_info or {}
        user_permissions = user_info.get('permissions') or []
        global_permission = '%s|all' % permission.split('|')[0]
        if 'admin|all' in user_permissions or global_permission in user_permissions or permission in user_permissions:
            return True
        collection_permission = self.permissions.get(permission)
        if isinstance(collection_permission, bool):
            return collection_permission
        if callable(collection_permission):
            return collection_permission(permission)
        return False

    def build_error(self, message='', status=400):
        """Build and write an error message."""
        self.set_status(status)
        self.write({'error': True, 'message': message})

    def logout(self):
        """Remove the secure cookie used fro authentication."""
        if self.current_user in self._users_cache:
            del self._users_cache[self.current_user]
        self.clear_cookie("user")


class RootHandler(BaseHandler):
    """Handler for the / path."""
    angular_app_path = os.path.join(os.path.dirname(__file__), "angular_app")

    @gen.coroutine
    @authenticated
    def get(self, *args, **kwargs):
        # serve the ./angular_app/index.html file
        with open(self.angular_app_path + "/index.html", 'r') as fd:
            self.write(fd.read())


# Keep track of WebSocket connections.
_ws_clients = {}

class CollectionHandler(BaseHandler):
    """Base class for handlers that need to interact with the database backend.

    Introduce basic CRUD operations."""
    # set of documents we're managing (a collection in MongoDB or a table in a SQL database)
    document = None
    collection = None

    # set of documents used to store incremental sequences
    counters_collection = 'counters'

    _id_chars = string.ascii_lowercase + string.digits

    def get_next_seq(self, seq):
        """Increment and return the new value of a ever-incrementing counter.

        :param seq: unique name of the sequence
        :type seq: str

        :returns: the next value of the sequence
        :rtype: int
        """
        if not self.db.query(self.counters_collection, {'seq_name': seq}):
            self.db.add(self.counters_collection, {'seq_name': seq, 'seq': 0})
        merged, doc = self.db.update(self.counters_collection,
                {'seq_name': seq},
                {'seq': 1},
                operation='increment')
        return doc.get('seq', 0)

    def gen_id(self, seq='ids', random_alpha=32):
        """Generate a unique, non-guessable ID.

        :param seq: the scope of the ever-incrementing sequence
        :type seq: str
        :param random_alpha: number of random lowercase alphanumeric chars
        :type random_alpha: int

        :returns: unique ID
        :rtype: str"""
        t = str(time.time()).replace('.', '_')
        seq = str(self.get_next_seq(seq))
        rand = ''.join([random.choice(self._id_chars) for x in xrange(random_alpha)])
        return '-'.join((t, seq, rand))

    def _filter_results(self, results, params):
        """Filter a list using keys and values from a dictionary.

        :param results: the list to be filtered
        :type results: list
        :param params: a dictionary of items that must all be present in an original list item to be included in the return
        :type params: dict

        :returns: list of items that have all the keys with the same values as params
        :rtype: list"""
        if not params:
            return results
        params = backend.convert(params)
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

    def _clean_dict(self, data):
        """Filter a dictionary (in place) to remove unwanted keywords.

        :param data: dictionary to clean
        :type data: dict"""
        if isinstance(data, dict):
            for key in data.keys():
                if isinstance(key, (str, unicode)) and key.startswith('$'):
                    del data[key]
        return data

    def _dict2env(self, data):
        """Convert a dictionary into a form suitable to be passed as environment variables.

        :param data: dictionary to convert
        :type data: dict"""
        ret = {}
        for key, value in data.iteritems():
            if isinstance(value, (list, tuple, dict)):
                continue
            try:
                key = key.upper().encode('ascii', 'ignore')
                key = re_env_key.sub('', key)
                if not key:
                    continue
                ret[key] = unicode(value).encode(ENCODING)
            except:
                continue
        return ret

    def apply_filter(self, data, filter_name):
        """Apply a filter to the data.

        :param data: the data to filter
        :returns: the modified (possibly also in place) data
        """
        filter_method = getattr(self, 'filter_%s' % filter_name, None)
        if filter_method is not None:
            data = filter_method(data)
        return data

    @gen.coroutine
    @authenticated
    def get(self, id_=None, resource=None, resource_id=None, acl=True, **kwargs):
        if resource:
            # Handle access to sub-resources.
            permission = '%s:%s%s|read' % (self.document, resource, '-all' if resource_id is None else '')
            if acl and not self.has_permission(permission):
                return self.build_error(status=401, message='insufficient permissions: %s' % permission)
            handler = getattr(self, 'handle_get_%s' % resource, None)
            if handler and callable(handler):
                output = handler(id_, resource_id, **kwargs) or {}
                output = self.apply_filter(output, 'get_%s' % resource)
                self.write(output)
                return
            return self.build_error(status=404, message='unable to access resource: %s' % resource)
        if id_ is not None:
            # read a single document
            permission = '%s|read' % self.document
            if acl and not self.has_permission(permission):
                return self.build_error(status=401, message='insufficient permissions: %s' % permission)
            output = self.db.get(self.collection, id_)
            output = self.apply_filter(output, 'get')
            self.write(output)
        else:
            # return an object containing the list of all objects in the collection;
            # e.g.: {'events': [{'_id': 'obj1-id, ...}, {'_id': 'obj2-id, ...}, ...]}
            # Please, never return JSON lists that are not encapsulated into an object,
            # to avoid XSS vulnerabilities.
            permission = '%s|read' % self.collection
            if acl and not self.has_permission(permission):
                return self.build_error(status=401, message='insufficient permissions: %s' % permission)
            output = {self.collection: self.db.query(self.collection, self.arguments)}
            output = self.apply_filter(output, 'get_all')
            self.write(output)

    @gen.coroutine
    @authenticated
    def post(self, id_=None, resource=None, resource_id=None, **kwargs):
        data = escape.json_decode(self.request.body or '{}')
        self._clean_dict(data)
        method = self.request.method.lower()
        crud_method = 'create' if method == 'post' else 'update'
        now = datetime.datetime.now()
        user_info = self.current_user_info
        user_id = user_info.get('_id')
        if crud_method == 'create':
            data['created_by'] = user_id
            data['created_at'] = now
        data['updated_by'] = user_id
        data['updated_at'] = now
        if resource:
            permission = '%s:%s%s|%s' % (self.document, resource, '-all' if resource_id is None else '', crud_method)
            if not self.has_permission(permission):
                return self.build_error(status=401, message='insufficient permissions: %s' % permission)
            # Handle access to sub-resources.
            handler = getattr(self, 'handle_%s_%s' % (method, resource), None)
            if handler and callable(handler):
                data = self.apply_filter(data, 'input_%s_%s' % (method, resource))
                output = handler(id_, resource_id, data, **kwargs)
                output = self.apply_filter(output, 'get_%s' % resource)
                self.write(output)
                return
        if id_ is not None:
            permission = '%s|%s' % (self.document, crud_method)
            if not self.has_permission(permission):
                return self.build_error(status=401, message='insufficient permissions: %s' % permission)
            data = self.apply_filter(data, 'input_%s' % method)
            merged, newData = self.db.update(self.collection, id_, data)
            newData = self.apply_filter(newData, method)
        else:
            permission = '%s|%s' % (self.collection, crud_method)
            if not self.has_permission(permission):
                return self.build_error(status=401, message='insufficient permissions: %s' % permission)
            data = self.apply_filter(data, 'input_%s_all' % method)
            newData = self.db.add(self.collection, data, _id=self.gen_id())
            newData = self.apply_filter(newData, '%s_all' % method)
        self.write(newData)

    # PUT (update an existing document) is handled by the POST (create a new document) method
    put = post

    @gen.coroutine
    @authenticated
    def delete(self, id_=None, resource=None, resource_id=None, **kwargs):
        if resource:
            # Handle access to sub-resources.
            permission = '%s:%s%s|delete' % (self.document, resource, '-all' if resource_id is None else '')
            if not self.has_permission(permission):
                return self.build_error(status=401, message='insufficient permissions: %s' % permission)
            method = getattr(self, 'handle_delete_%s' % resource, None)
            if method and callable(method):
                self.write(method(id_, resource_id, **kwargs))
                return
        if id_:
            permission = '%s|delete' % self.document
            if not self.has_permission(permission):
                return self.build_error(status=401, message='insufficient permissions: %s' % permission)
            self.db.delete(self.collection, id_)
        else:
            self.write({'success': False})
        self.write({'success': True})

    def on_timeout(self, cmd, pipe):
        """Kill a process that is taking too long to complete."""
        logging.debug('cmd %s is taking too long: killing it' % ' '.join(cmd))
        try:
            pipe.proc.kill()
        except:
            pass

    def on_exit(self, returncode, cmd, pipe):
        """Callback executed when a subprocess execution is over."""
        self.ioloop.remove_timeout(self.timeout)
        logging.debug('cmd: %s returncode: %d' % (' '.join(cmd), returncode))

    @gen.coroutine
    def run_subprocess(self, cmd, stdin_data=None, env=None):
        """Execute the given action.

        :param cmd: the command to be run with its command line arguments
        :type cmd: list

        :param stdin_data: data to be sent over stdin
        :type stdin_data: str
        :param env: environment of the process
        :type env: dict
        """
        self.ioloop = tornado.ioloop.IOLoop.instance()
        p = process.Subprocess(cmd, close_fds=True, stdin=process.Subprocess.STREAM,
                stdout=process.Subprocess.STREAM, stderr=process.Subprocess.STREAM, env=env)
        p.set_exit_callback(lambda returncode: self.on_exit(returncode, cmd, p))
        self.timeout = self.ioloop.add_timeout(datetime.timedelta(seconds=PROCESS_TIMEOUT),
                lambda: self.on_timeout(cmd, p))
        yield gen.Task(p.stdin.write, stdin_data or '')
        p.stdin.close()
        out, err = yield [gen.Task(p.stdout.read_until_close),
                gen.Task(p.stderr.read_until_close)]
        logging.debug('cmd: %s' % ' '.join(cmd))
        logging.debug('cmd stdout: %s' % out)
        logging.debug('cmd strerr: %s' % err)
        raise gen.Return((out, err))

    @gen.coroutine
    def run_triggers(self, action, stdin_data=None, env=None):
        """Asynchronously execute triggers for the given action.

        :param action: action name; scripts in directory ./data/triggers/{action}.d will be run
        :type action: str
        :param stdin_data: a python dictionary that will be serialized in JSON and sent to the process over stdin
        :type stdin_data: dict
        :param env: environment of the process
        :type stdin_data: dict
        """
        logging.debug('running triggers for action "%s"' % action)
        stdin_data = stdin_data or {}
        try:
            stdin_data = json.dumps(stdin_data)
        except:
            stdin_data = '{}'
        for script in glob.glob(os.path.join(self.data_dir, 'triggers', '%s.d' % action, '*')):
            if not (os.path.isfile(script) and os.access(script, os.X_OK)):
                continue
            out, err = yield gen.Task(self.run_subprocess, [script], stdin_data, env)

    def build_ws_url(self, path, proto='ws', host=None):
        """Return a WebSocket url from a path."""
        return 'ws://127.0.0.1:%s/ws/%s' % (self.listen_port + 1, path)

    @gen.coroutine
    def send_ws_message(self, path, message):
        """Send a WebSocket message to all the connected clients.

        :param path: partial path used to build the WebSocket url
        :type path: str
        :param message: message to send
        :type message: str
        """
        try:
            ws = yield tornado.websocket.websocket_connect(self.build_ws_url(path))
            ws.write_message(message)
            ws.close()
        except Exception, e:
            self.logger.error('Error yielding WebSocket message: %s', e)


class PersonsHandler(CollectionHandler):
    """Handle requests for Persons."""
    document = 'person'
    collection = 'persons'

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
            if 'persons' in event:
                del event['persons']
            event['person_data'] = person_data
        if resource_id and events:
            return events[0]
        return {'events': events}


class EventsHandler(CollectionHandler):
    """Handle requests for Events."""
    document = 'event'
    collection = 'events'

    def filter_get(self, output):
        if not self.has_permission('persons-all|read'):
            if 'persons' in output:
                output['persons'] = []
        return output

    def filter_get_all(self, output):
        if not self.has_permission('persons-all|read'):
            for event in output.get('events') or []:
                if 'persons' in event:
                    event['persons'] = []
        return output

    def filter_input_post_tickets(self, data):
        if not self.has_permission('event|update'):
            if 'attended' in data:
                del data['attended']
        return data

    filter_input_put_tickets = filter_input_post_tickets

    def _get_person_data(self, person_id_or_query, persons):
        """Filter a list of persons returning the first item with a given person_id
        or which set of keys specified in a dictionary match their respective values."""
        for person in persons:
            if isinstance(person_id_or_query, dict):
                if all(person.get(k) == v for k, v in person_id_or_query.iteritems()):
                    return person
            else:
                if str(person.get('person_id')) == person_id_or_query:
                    return person
        return {}

    def handle_get_persons(self, id_, resource_id=None, match_query=None):
        # Return every person registered at this event, or the information
        # about a specific person.
        query = {'_id': id_}
        event = self.db.query('events', query)[0]
        if match_query is None:
            match_query = resource_id
        if resource_id:
            return {'person': self._get_person_data(match_query, event.get('persons') or [])}
        persons = self._filter_results(event.get('persons') or [], self.arguments)
        return {'persons': persons}

    def handle_get_tickets(self, id_, resource_id=None):
        if resource_id is None and not self.has_permission('event:tickets|all'):
            return self.build_error(status=401, message='insufficient permissions: event:tickets|all')
        return self.handle_get_persons(id_, resource_id, {'_id': resource_id})

    def handle_post_persons(self, id_, person_id, data):
        # Add a person to the list of persons registered at this event.
        uuid, arguments = self.uuid_arguments
        self._clean_dict(data)
        data['seq'] = self.get_next_seq('event_%s_persons' % id_)
        data['seq_hex'] = '%06X' % data['seq']
        if person_id is None:
            doc = {}
        else:
            doc = self.db.query('events', {'_id': id_, 'persons.person_id': person_id})
        ret = {'action': 'add', 'person_id': person_id, 'person': data, 'uuid': uuid}
        if '_id' in data:
            del data['_id']
            self.send_ws_message('event/%s/updates' % id_, json.dumps(ret))
        if not doc:
            data['_id'] = self.gen_id()
            merged, doc = self.db.update('events',
                    {'_id': id_},
                    {'persons': data},
                    operation='appendUnique',
                    create=False)
        return ret

    handle_post_tickets = handle_post_persons

    def handle_put_persons(self, id_, person_id, data, ticket=False):
        # Update an existing entry for a person registered at this event.
        self._clean_dict(data)
        uuid, arguments = self.uuid_arguments
        query = dict([('persons.%s' % k, v) for k, v in arguments.iteritems()])
        query['_id'] = id_
        if ticket:
            query['persons._id'] = person_id
            person_query = {'_id': person_id}
        elif person_id is not None:
            query['persons.person_id'] = person_id
            person_query = person_id
        else:
            person_query = self.arguments
        old_person_data = {}
        current_event = self.db.query(self.collection, query)
        if current_event:
            current_event = current_event[0]
        else:
            current_event = {}
        old_person_data = self._get_person_data(person_query,
                current_event.get('persons') or [])
        merged, doc = self.db.update('events', query,
                data, updateList='persons', create=False)
        new_person_data = self._get_person_data(person_query,
                doc.get('persons') or [])
        env = self._dict2env(new_person_data)
        # always takes the person_id from the new person (it may have
        # be a ticket_id).
        person_id = str(new_person_data.get('person_id'))
        env.update({'PERSON_ID': person_id, 'EVENT_ID': id_,
            'EVENT_TITLE': doc.get('title', ''), 'WEB_USER': self.current_user,
            'WEB_REMOTE_IP': self.request.remote_ip})
        stdin_data = {'old': old_person_data,
            'new': new_person_data,
            'event': doc,
            'merged': merged
        }
        self.run_triggers('update_person_in_event', stdin_data=stdin_data, env=env)
        if old_person_data and old_person_data.get('attended') != new_person_data.get('attended'):
            if new_person_data.get('attended'):
                self.run_triggers('attends', stdin_data=stdin_data, env=env)

        ret = {'action': 'update', 'person_id': person_id, 'person': new_person_data, 'uuid': uuid}
        if old_person_data != new_person_data:
            self.send_ws_message('event/%s/tickets/updates' % id_, json.dumps(ret))
        return ret

    def handle_put_tickets(self, id_, person_id, data):
        return self.handle_put_persons(id_, person_id, data, True)

    def handle_delete_persons(self, id_, person_id):
        # Remove a specific person from the list of persons registered at this event.
        uuid, arguments = self.uuid_arguments
        doc = self.db.query('events',
                {'_id': id_, 'persons.person_id': person_id})
        ret = {'action': 'delete', 'person_id': person_id, 'uuid': uuid}
        if doc:
            merged, doc = self.db.update('events',
                    {'_id': id_},
                    {'persons': {'person_id': person_id}},
                    operation='delete',
                    create=False)
            self.send_ws_message('event/%s/updates' % id_, json.dumps(ret))
        return ret

    handle_delete_tickets = handle_delete_persons


class UsersHandler(CollectionHandler):
    """Handle requests for Users."""
    document = 'user'
    collection = 'users'

    def filter_input_post_all(self, data):
        username = (data.get('username') or '').strip()
        password = (data.get('password') or '').strip()
        email = (data.get('email') or '').strip()
        if not (username and password):
            raise InputException('missing username or password')
        res = self.db.query('users', {'username': username})
        if res:
            raise InputException('username already exists')
        return {'username': username, 'password': utils.hash_password(password),
                'email': email, '_id': self.gen_id()}


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
        'Titolo professionale': 'job_title',
        'Azienda': 'company',
        'Prefisso': 'name_title',
        'Prefisso (Sig., Sig.ra, ecc.)': 'name_title',

        'Order #': 'order_nr',
        'Prefix': 'name_title',
        'First Name': 'name',
        'Last Name': 'surname',
        'Suffix': 'name_suffix',
        'Email': 'email',
        'Attendee #': 'attendee_nr',
        'Barcode #': 'ebqrcode',
        'Company': 'company',
    }
    # Only these information are stored in the person collection.
    keepPersonData = ('name', 'surname', 'email', 'name_title', 'name_suffix',
            'company', 'job_title')

    @gen.coroutine
    @authenticated
    def post(self, **kwargs):
        # import a CSV list of persons
        event_handler = EventsHandler(self.application, self.request)
        event_handler.db = self.db
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
                    merged, stored_person = self.db.update('persons',
                            [('email', 'name', 'surname')],
                            person_data)
                    if merged:
                        reply['merged'] += 1
                    if targetEvent and stored_person:
                        event_id = targetEvent
                        person_id = stored_person['_id']
                        registered_data = {
                                'person_id': person_id,
                                'attended': False,
                                'from_file': filename}
                        person.update(registered_data)
                        if not self.db.query('events',
                                {'_id': event_id, 'persons.person_id': person_id}):
                            event_handler.handle_post_persons(event_id, person_id, person)
                            reply['new_in_event'] += 1
        self.write(reply)


class SettingsHandler(BaseHandler):
    """Handle requests for Settings."""
    @gen.coroutine
    @authenticated
    def get(self, **kwds):
        query = self.arguments_tobool()
        settings = self.db.query('settings', query)
        self.write({'settings': settings})


class InfoHandler(BaseHandler):
    """Handle requests for Info."""
    @gen.coroutine
    @authenticated
    def get(self, **kwds):
        info = {}
        user_info = self.current_user_info
        if user_info:
            info['user'] = user_info
        self.write({'info': info})


class WebSocketEventUpdatesHandler(tornado.websocket.WebSocketHandler):
    """Manage websockets."""
    def _clean_url(self, url):
        return re_slashes.sub('/', url)

    def open(self, event_id, *args, **kwds):
        logging.debug('WebSocketEventUpdatesHandler.on_open event_id:%s' % event_id)

        _ws_clients.setdefault(self._clean_url(self.request.uri), set()).add(self)
        logging.debug('WebSocketEventUpdatesHandler.on_open %s clients connected' % len(_ws_clients))

    def on_message(self, message):
        logging.debug('WebSocketEventUpdatesHandler.on_message')
        count = 0
        for client in _ws_clients.get(self._clean_url(self.request.uri), []):
            if client == self:
                continue
            client.write_message(message)
            count += 1
        logging.debug('WebSocketEventUpdatesHandler.on_message sent message to %d clients' % count)

    def on_close(self):
        logging.debug('WebSocketEventUpdatesHandler.on_close')
        try:
            if self in _ws_clients.get(self._clean_url(self.request.uri), []):
                _ws_clients[self._clean_url(self.request.uri)].remove(self)
        except Exception as e:
            logging.warn('WebSocketEventUpdatesHandler.on_close error closing websocket: %s', str(e))


class LoginHandler(BaseHandler):
    """Handle user authentication requests."""
    re_split_salt = re.compile(r'\$(?P<salt>.+)\$(?P<hash>.+)')

    @gen.coroutine
    def get(self, **kwds):
        # show the login page
        if self.is_api():
            self.set_status(401)
            self.write({'error': True,
                'message': 'authentication required'})
        else:
            with open(self.angular_app_path + "/login.html", 'r') as fd:
                self.write(fd.read())

    def _authorize(self, username, password, email=None):
        """Return True is this username/password is valid."""
        query = [{'username': username}]
        if email is not None:
            query.append({'email': email})
        res = self.db.query('users', query)
        if not res:
            return False
        user = res[0]
        db_password = user.get('password') or ''
        if not db_password:
            return False
        match = self.re_split_salt.match(db_password)
        if not match:
            return False
        salt = match.group('salt')
        if utils.hash_password(password, salt=salt) == db_password:
            return True
        return False

    @gen.coroutine
    def post(self, *args, **kwargs):
        # authenticate a user
        try:
            password = self.get_body_argument('password')
            username = self.get_body_argument('username')
        except tornado.web.MissingArgumentError:
            data = escape.json_decode(self.request.body or '{}')
            username = data.get('username')
            password = data.get('password')
        if not (username and password):
            self.set_status(401)
            self.write({'error': True, 'message': 'missing username or password'})
            return
        if self._authorize(username, password):
            logging.info('successful login for user %s' % username)
            self.set_secure_cookie("user", username)
            self.write({'error': False, 'message': 'successful login'})
            return
        logging.info('login failed for user %s' % username)
        self.set_status(401)
        self.write({'error': True, 'message': 'wrong username and password'})


class LogoutHandler(BaseHandler):
    """Handle user logout requests."""
    @gen.coroutine
    def get(self, **kwds):
        # log the user out
        logging.info('logout')
        self.logout()
        self.write({'error': False, 'message': 'logged out'})


def run():
    """Run the Tornado web application."""
    # command line arguments; can also be written in a configuration file,
    # specified with the --config argument.
    define("port", default=5242, help="run on the given port", type=int)
    define("address", default='', help="bind the server at the given address", type=str)
    define("data_dir", default=os.path.join(os.path.dirname(__file__), "data"),
            help="specify the directory used to store the data")
    define("ssl_cert", default=os.path.join(os.path.dirname(__file__), 'ssl', 'eventman_cert.pem'),
            help="specify the SSL certificate to use for secure connections")
    define("ssl_key", default=os.path.join(os.path.dirname(__file__), 'ssl', 'eventman_key.pem'),
            help="specify the SSL private key to use for secure connections")
    define("mongo_url", default=None,
            help="URL to MongoDB server", type=str)
    define("db_name", default='eventman',
            help="Name of the MongoDB database to use", type=str)
    define("authentication", default=False, help="if set to true, authentication is required")
    define("debug", default=False, help="run in debug mode")
    define("config", help="read configuration file",
            callback=lambda path: tornado.options.parse_config_file(path, final=False))
    tornado.options.parse_command_line()

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    if options.debug:
        logger.setLevel(logging.DEBUG)

    # database backend connector
    db_connector = backend.EventManDB(url=options.mongo_url, dbName=options.db_name)
    init_params = dict(db=db_connector, data_dir=options.data_dir, listen_port=options.port,
            authentication=options.authentication, logger=logger)

    # If not present, we store a user 'admin' with password 'eventman' into the database.
    if not db_connector.query('users', {'username': 'admin'}):
        db_connector.add('users',
                {'username': 'admin', 'password': utils.hash_password('eventman'),
                 'permissions': ['admin|all']})

    # If present, use the cookie_secret stored into the database.
    cookie_secret = db_connector.query('settings', {'setting': 'server_cookie_secret'})
    if cookie_secret:
        cookie_secret = cookie_secret[0]['cookie_secret']
    else:
        # the salt guarantees its uniqueness
        cookie_secret = utils.hash_password('__COOKIE_SECRET__')
        db_connector.add('settings',
                {'setting': 'server_cookie_secret', 'cookie_secret': cookie_secret})

    _ws_handler = (r"/ws/+event/+(?P<event_id>[\w\d_-]+)/+tickets/+updates/?", WebSocketEventUpdatesHandler)
    _persons_path = r"/persons/?(?P<id_>[\w\d_-]+)?/?(?P<resource>[\w\d_-]+)?/?(?P<resource_id>[\w\d_-]+)?"
    _events_path = r"/events/?(?P<id_>[\w\d_-]+)?/?(?P<resource>[\w\d_-]+)?/?(?P<resource_id>[\w\d_-]+)?"
    _users_path = r"/users/?(?P<id_>[\w\d_-]+)?/?(?P<resource>[\w\d_-]+)?/?(?P<resource_id>[\w\d_-]+)?"
    application = tornado.web.Application([
            (_persons_path, PersonsHandler, init_params),
            (r'/v%s%s' % (API_VERSION, _persons_path), PersonsHandler, init_params),
            (_events_path, EventsHandler, init_params),
            (r'/v%s%s' % (API_VERSION, _events_path), EventsHandler, init_params),
            (_users_path, UsersHandler, init_params),
            (r'/v%s%s' % (API_VERSION, _users_path), UsersHandler, init_params),
            (r"/(?:index.html)?", RootHandler, init_params),
            (r"/ebcsvpersons", EbCSVImportPersonsHandler, init_params),
            (r"/settings", SettingsHandler, init_params),
            (r"/info", InfoHandler, init_params),
            _ws_handler,
            (r'/login', LoginHandler, init_params),
            (r'/v%s/login' % API_VERSION, LoginHandler, init_params),
            (r'/logout', LogoutHandler),
            (r'/v%s/logout' % API_VERSION, LogoutHandler),
            (r'/(.*)', tornado.web.StaticFileHandler, {"path": "angular_app"})
        ],
        template_path=os.path.join(os.path.dirname(__file__), "templates"),
        static_path=os.path.join(os.path.dirname(__file__), "static"),
        cookie_secret='__COOKIE_SECRET__',
        login_url='/login',
        debug=options.debug)
    ssl_options = {}
    if os.path.isfile(options.ssl_key) and os.path.isfile(options.ssl_cert):
        ssl_options = dict(certfile=options.ssl_cert, keyfile=options.ssl_key)
    http_server = tornado.httpserver.HTTPServer(application, ssl_options=ssl_options or None)
    logger.info('Start serving on %s://%s:%d', 'https' if ssl_options else 'http',
                                                 options.address if options.address else '127.0.0.1',
                                                 options.port)
    http_server.listen(options.port, options.address)

    # Also listen on options.port+1 for our local ws connection.
    ws_application = tornado.web.Application([_ws_handler], debug=options.debug)
    ws_http_server = tornado.httpserver.HTTPServer(ws_application)
    ws_http_server.listen(options.port+1, address='127.0.0.1')
    logger.debug('Starting WebSocket on ws://127.0.0.1:%d', options.port+1)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == '__main__':
    run()
