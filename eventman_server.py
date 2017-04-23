#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""EventMan(ager)

Your friendly manager of attendees at an event.

Copyright 2015-2017 Davide Alberani <da@erlug.linux.it>
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
import dateutil.tz
import dateutil.parser

import tornado.httpserver
import tornado.ioloop
import tornado.options
from tornado.options import define, options
import tornado.web
import tornado.websocket
from tornado import gen, escape, process

import utils
import monco
import collections

ENCODING = 'utf-8'
PROCESS_TIMEOUT = 60

API_VERSION = '1.0'

re_env_key = re.compile('[^a-zA-Z_]+')
re_slashes = re.compile(r'//+')

# Keep track of WebSocket connections.
_ws_clients = {}


def authenticated(method):
    """Decorator to handle forced authentication."""
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
        'event:tickets|read': True,
        'event:tickets|create': True,
        'event:tickets|update': True,
        'event:tickets-all|create': True,
        'events|read': True,
        'users|create': True
    }

    # Cache currently connected users.
    _users_cache = {}

    # A property to access the first value of each argument.
    arguments = property(lambda self: dict([(k, v[0].decode('utf-8'))
        for k, v in self.request.arguments.items()]))

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

    _re_split_salt = re.compile(r'\$(?P<salt>.+)\$(?P<hash>.+)')

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
        if isinstance(obj, str):
            obj = obj.lower()
        return self._bool_convert.get(obj, obj)

    def arguments_tobool(self):
        """Return a dictionary of arguments, converted to booleans where possible."""
        return dict([(k, self.tobool(v)) for k, v in self.arguments.items()])

    def initialize(self, **kwargs):
        """Add every passed (key, value) as attributes of the instance."""
        for key, value in kwargs.items():
            setattr(self, key, value)

    @property
    def current_user(self):
        """Retrieve current user name from the secure cookie."""
        current_user = self.get_secure_cookie("user")
        if isinstance(current_user, bytes):
            current_user = current_user.decode('utf-8')
        return current_user

    @property
    def current_user_info(self):
        """Information about the current user, including their permissions."""
        current_user = self.current_user
        if current_user in self._users_cache:
            return self._users_cache[current_user]
        permissions = set([k for (k, v) in self.permissions.items() if v is True])
        user_info = {'permissions': permissions}
        if current_user:
            user_info['_id'] = current_user
            user = self.db.getOne('users', {'_id': current_user})
            if user:
                user_info = user
                permissions.update(set(user.get('permissions') or []))
                user_info['permissions'] = permissions
                user_info['isRegistered'] = True
        self._users_cache[current_user] = user_info
        return user_info

    def add_access_info(self, doc):
        """Add created/updated by/at to a document (modified in place and returned).

        :param doc: the doc to be updated
        :type doc: dict
        :returns: the updated document
        :rtype: dict"""
        user_id = self.current_user
        now = datetime.datetime.utcnow()
        if 'created_by' not in doc:
            doc['created_by'] = user_id
        if 'created_at' not in doc:
            doc['created_at'] = now
        doc['updated_by'] = user_id
        doc['updated_at'] = now
        return doc

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
        if isinstance(collection_permission, collections.Callable):
            return collection_permission(permission)
        return False

    def user_authorized(self, username, password):
        """Check if a combination of username/password is valid.

        :param username: username or email
        :type username: str
        :param password: password
        :type password: str

        :returns: tuple like (bool_user_is_authorized, dict_user_info)
        :rtype: dict"""
        query = [{'username': username}, {'email': username}]
        res = self.db.query('users', query)
        if not res:
            return (False, {})
        user = res[0]
        db_password = user.get('password') or ''
        if not db_password:
            return (False, {})
        match = self._re_split_salt.match(db_password)
        if not match:
            return (False, {})
        salt = match.group('salt')
        if utils.hash_password(password, salt=salt) == db_password:
            return (True, user)
        return (False, {})

    def build_error(self, message='', status=400):
        """Build and write an error message.

        :param message: textual message
        :type message: str
        :param status: HTTP status code
        :type status: int
        """
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
    def get(self, *args, **kwargs):
        # serve the ./angular_app/index.html file
        with open(self.angular_app_path + "/index.html", 'r') as fd:
            self.write(fd.read())


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
        rand = ''.join([random.choice(self._id_chars) for x in range(random_alpha)])
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
        params = monco.convert(params)
        filtered = []
        for result in results:
            add = True
            for key, value in params.items():
                if key not in result or result[key] != value:
                    add = False
                    break
            if add:
                filtered.append(result)
        return filtered

    def _clean_dict(self, data):
        """Filter a dictionary (in place) to remove unwanted keywords in db queries.

        :param data: dictionary to clean
        :type data: dict"""
        if isinstance(data, dict):
            for key in list(data.keys()):
                if (isinstance(key, str) and key.startswith('$')) or key in ('_id', 'created_by', 'created_at',
                                                                    'updated_by', 'updated_at', 'isRegistered'):
                    del data[key]
        return data

    def _dict2env(self, data):
        """Convert a dictionary into a form suitable to be passed as environment variables.

        :param data: dictionary to convert
        :type data: dict"""
        ret = {}
        for key, value in data.items():
            if isinstance(value, (list, tuple, dict, set)):
                continue
            try:
                key = re_env_key.sub('', key)
                key = key.upper().encode('ascii', 'ignore')
                if not key:
                    continue
                if not isinstance(value, str):
                    value = str(value)
                ret[key] = value
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
            if handler and isinstance(handler, collections.Callable):
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
        env = {}
        if id_ is not None:
            env['%s_ID' % self.document.upper()] = id_
        self.add_access_info(data)
        if resource:
            permission = '%s:%s%s|%s' % (self.document, resource, '-all' if resource_id is None else '', crud_method)
            if not self.has_permission(permission):
                return self.build_error(status=401, message='insufficient permissions: %s' % permission)
            # Handle access to sub-resources.
            handler = getattr(self, 'handle_%s_%s' % (method, resource), None)
            if handler and isinstance(handler, collections.Callable):
                data = self.apply_filter(data, 'input_%s_%s' % (method, resource))
                output = handler(id_, resource_id, data, **kwargs)
                output = self.apply_filter(output, 'get_%s' % resource)
                env['RESOURCE'] = resource
                if resource_id:
                    env['%s_ID' % resource] = resource_id
                self.run_triggers('%s_%s_%s' % ('create' if resource_id is None else 'update', self.document, resource),
                                  stdin_data=output, env=env)
                self.write(output)
                return
            return self.build_error(status=404, message='unable to access resource: %s' % resource)
        if id_ is not None:
            permission = '%s|%s' % (self.document, crud_method)
            if not self.has_permission(permission):
                return self.build_error(status=401, message='insufficient permissions: %s' % permission)
            data = self.apply_filter(data, 'input_%s' % method)
            merged, newData = self.db.update(self.collection, id_, data)
            newData = self.apply_filter(newData, method)
            self.run_triggers('update_%s' % self.document, stdin_data=newData, env=env)
        else:
            permission = '%s|%s' % (self.collection, crud_method)
            if not self.has_permission(permission):
                return self.build_error(status=401, message='insufficient permissions: %s' % permission)
            data = self.apply_filter(data, 'input_%s_all' % method)
            newData = self.db.add(self.collection, data, _id=self.gen_id())
            newData = self.apply_filter(newData, '%s_all' % method)
            self.run_triggers('create_%s' % self.document, stdin_data=newData, env=env)
        self.write(newData)

    # PUT (update an existing document) is handled by the POST (create a new document) method;
    # in subclasses you can always separate sub-resources handlers like handle_post_tickets and handle_put_tickets
    put = post

    @gen.coroutine
    @authenticated
    def delete(self, id_=None, resource=None, resource_id=None, **kwargs):
        env = {}
        if id_ is not None:
            env['%s_ID' % self.document.upper()] = id_
        if resource:
            # Handle access to sub-resources.
            permission = '%s:%s%s|delete' % (self.document, resource, '-all' if resource_id is None else '')
            if not self.has_permission(permission):
                return self.build_error(status=401, message='insufficient permissions: %s' % permission)
            method = getattr(self, 'handle_delete_%s' % resource, None)
            if method and isinstance(method, collections.Callable):
                output = method(id_, resource_id, **kwargs)
                env['RESOURCE'] = resource
                if resource_id:
                    env['%s_ID' % resource] = resource_id
                self.run_triggers('delete_%s_%s' % (self.document, resource), stdin_data=env, env=env)
                self.write(output)
                return
            return self.build_error(status=404, message='unable to access resource: %s' % resource)
        if id_ is not None:
            permission = '%s|delete' % self.document
            if not self.has_permission(permission):
                return self.build_error(status=401, message='insufficient permissions: %s' % permission)
            howMany = self.db.delete(self.collection, id_)
            env['DELETED_ITEMS'] = howMany
            self.run_triggers('delete_%s' % self.document, stdin_data=env, env=env)
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
        processed_env = self._dict2env(env)
        p = process.Subprocess(cmd, close_fds=True, stdin=process.Subprocess.STREAM,
                stdout=process.Subprocess.STREAM, stderr=process.Subprocess.STREAM, env=processed_env)
        p.set_exit_callback(lambda returncode: self.on_exit(returncode, cmd, p))
        self.timeout = self.ioloop.add_timeout(datetime.timedelta(seconds=PROCESS_TIMEOUT),
                lambda: self.on_timeout(cmd, p))
        yield gen.Task(p.stdin.write, stdin_data.encode(ENCODING) or b'')
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
        if not hasattr(self, 'data_dir'):
            return
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
        try:
            args = '?uuid=%s' % self.get_argument('uuid')
        except:
            args = ''
        return 'ws://127.0.0.1:%s/ws/%s%s' % (self.listen_port + 1, path, args)

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
        except Exception as e:
            self.logger.error('Error yielding WebSocket message: %s', e)


class EventsHandler(CollectionHandler):
    """Handle requests for Events."""
    document = 'event'
    collection = 'events'

    def _mangle_event(self, event):
        # Some in-place changes to an event
        if 'tickets' in event:
            event['tickets_sold'] = len([t for t in event['tickets'] if not t.get('cancelled')])
            event['no_tickets_for_sale'] = False
            try:
                self._check_sales_datetime(event)
                self._check_number_of_tickets(event)
            except InputException:
                event['no_tickets_for_sale'] = True
            if not self.has_permission('tickets-all|read'):
                event['tickets'] = []
        return event

    def filter_get(self, output):
        return self._mangle_event(output)

    def filter_get_all(self, output):
        for event in output.get('events') or []:
            self._mangle_event(event)
        return output

    def filter_input_post(self, data):
        # Auto-generate the group_id, if missing.
        if 'group_id' not in data:
            data['group_id'] = self.gen_id()
        return data

    filter_input_post_all = filter_input_post
    filter_input_put = filter_input_post

    def filter_input_post_tickets(self, data):
        # Avoid users to be able to auto-update their 'attendee' status.
        if not self.has_permission('event|update'):
            if 'attended' in data:
                del data['attended']
        self.add_access_info(data)
        return data

    filter_input_put_tickets = filter_input_post_tickets

    def handle_get_group_persons(self, id_, resource_id=None):
        persons = []
        this_query = {'_id': id_}
        this_event = self.db.query('events', this_query)[0]
        group_id = this_event.get('group_id')
        if group_id is None:
            return {'persons': persons}
        this_persons = [p for p in (this_event.get('tickets') or []) if not p.get('cancelled')]
        this_emails = [_f for _f in [p.get('email') for p in this_persons] if _f]
        all_query = {'group_id': group_id}
        events = self.db.query('events', all_query)
        for event in events:
            if id_ is not None and  str(event.get('_id')) == id_:
                continue
            persons += [p for p in (event.get('tickets') or []) if p.get('email') and p.get('email') not in this_emails]
        return {'persons': persons}

    def _get_ticket_data(self, ticket_id_or_query, tickets, only_one=True):
        """Filter a list of tickets returning the first item with a given _id
        or which set of keys specified in a dictionary match their respective values."""
        matches = []
        for ticket in tickets:
            if isinstance(ticket_id_or_query, dict):
                if all(ticket.get(k) == v for k, v in ticket_id_or_query.items()):
                    matches.append(ticket)
                    if only_one:
                        break
            else:
                if str(ticket.get('_id')) == ticket_id_or_query:
                    matches.append(ticket)
                    if only_one:
                        break
        if only_one:
            if matches:
                return matches[0]
            return {}
        return matches

    def handle_get_tickets(self, id_, resource_id=None):
        # Return every ticket registered at this event, or the information
        # about a specific ticket.
        query = {'_id': id_}
        event = self.db.query('events', query)[0]
        if resource_id:
            return {'ticket': self._get_ticket_data(resource_id, event.get('tickets') or [])}
        tickets = self._filter_results(event.get('tickets') or [], self.arguments)
        return {'tickets': tickets}

    def _check_number_of_tickets(self, event):
        if self.has_permission('admin|all'):
            return
        number_of_tickets = event.get('number_of_tickets')
        if number_of_tickets is None:
            return
        try:
            number_of_tickets = int(number_of_tickets)
        except ValueError:
            return
        tickets = event.get('tickets') or []
        tickets = [t for t in tickets if not t.get('cancelled')]
        if len(tickets) >= event['number_of_tickets']:
            raise InputException('no more tickets available')

    def _check_sales_datetime(self, event):
        if self.has_permission('admin|all'):
            return
        begin_date = event.get('ticket_sales_begin_date')
        begin_time = event.get('ticket_sales_begin_time')
        end_date = event.get('ticket_sales_end_date')
        end_time = event.get('ticket_sales_end_time')
        utc = dateutil.tz.tzutc()
        is_dst = time.daylight and time.localtime().tm_isdst > 0
        utc_offset = - (time.altzone if is_dst else time.timezone)
        if begin_date is None:
            begin_date = datetime.datetime.now(tz=utc).replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            begin_date = dateutil.parser.parse(begin_date)
            # Compensate UTC and DST offset, that otherwise would be added 2 times (one for date, one for time)
            begin_date = begin_date + datetime.timedelta(seconds=utc_offset)
        if begin_time is None:
            begin_time_h = 0
            begin_time_m = 0
        else:
            begin_time = dateutil.parser.parse(begin_time)
            begin_time_h = begin_time.hour
            begin_time_m = begin_time.minute
        now = datetime.datetime.now(tz=utc)
        begin_datetime = begin_date + datetime.timedelta(hours=begin_time_h, minutes=begin_time_m)
        if now < begin_datetime:
            raise InputException('ticket sales not yet started')

        if end_date is None:
            end_date = datetime.datetime.today().replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=utc)
        else:
            end_date = dateutil.parser.parse(end_date)
            end_date = end_date + datetime.timedelta(seconds=utc_offset)
        if end_time is None:
            end_time = end_date
            end_time_h = 23
            end_time_m = 59
        else:
            end_time = dateutil.parser.parse(end_time, yearfirst=True)
            end_time_h = end_time.hour
            end_time_m = end_time.minute
        end_datetime = end_date + datetime.timedelta(hours=end_time_h, minutes=end_time_m+1)
        if now > end_datetime:
            raise InputException('ticket sales has ended')

    def handle_post_tickets(self, id_, resource_id, data):
        event = self.db.query('events', {'_id': id_})[0]
        self._check_sales_datetime(event)
        self._check_number_of_tickets(event)
        uuid, arguments = self.uuid_arguments
        self._clean_dict(data)
        data['seq'] = self.get_next_seq('event_%s_tickets' % id_)
        data['seq_hex'] = '%06X' % data['seq']
        data['_id'] = ticket_id = self.gen_id()
        self.add_access_info(data)
        ret = {'action': 'add', 'ticket': data, 'uuid': uuid}
        merged, doc = self.db.update('events',
                {'_id': id_},
                {'tickets': data},
                operation='appendUnique',
                create=False)
        if doc:
            self.send_ws_message('event/%s/tickets/updates' % id_, json.dumps(ret))
            ticket = self._get_ticket_data(ticket_id, doc.get('tickets') or [])
            env = dict(ticket)
            env.update({'PERSON_ID': ticket_id, 'TICKED_ID': ticket_id, 'EVENT_ID': id_,
                'EVENT_TITLE': doc.get('title', ''), 'WEB_USER': self.current_user_info.get('username', ''),
                'WEB_REMOTE_IP': self.request.remote_ip})
            stdin_data = {'new': ticket,
                'event': doc,
                'merged': merged
            }
            self.run_triggers('create_ticket_in_event', stdin_data=stdin_data, env=env)
        return ret

    def handle_put_tickets(self, id_, ticket_id, data):
        # Update an existing entry for a ticket registered at this event.
        self._clean_dict(data)
        uuid, arguments = self.uuid_arguments
        _errorMessage = ''
        if '_errorMessage' in arguments:
            _errorMessage = arguments['_errorMessage']
            del arguments['_errorMessage']
        _searchFor = False
        if '_searchFor' in arguments:
            _searchFor = arguments['_searchFor']
            del arguments['_searchFor']
        query = dict([('tickets.%s' % k, v) for k, v in arguments.items()])
        query['_id'] = id_
        if ticket_id is not None:
            query['tickets._id'] = ticket_id
            ticket_query = {'_id': ticket_id}
        else:
            ticket_query = arguments
        old_ticket_data = {}
        current_event = self.db.query(self.collection, query)
        if current_event:
            current_event = current_event[0]
        else:
            current_event = {}
        self._check_sales_datetime(current_event)
        tickets = current_event.get('tickets') or []
        matching_tickets = self._get_ticket_data(ticket_query, tickets, only_one=False)
        nr_matches = len(matching_tickets)
        if nr_matches > 1:
            ret = {'error': True, 'message': 'more than one ticket matched. %s' % _errorMessage, 'query': query,
                   'searchFor': _searchFor, 'uuid': uuid, 'username': self.current_user_info.get('username', '')}
            self.send_ws_message('event/%s/tickets/updates' % id_, json.dumps(ret))
            self.set_status(400)
            return ret
        elif nr_matches == 0:
            ret = {'error': True, 'message': 'no ticket matched. %s' % _errorMessage, 'query': query,
                   'searchFor': _searchFor, 'uuid': uuid, 'username': self.current_user_info.get('username', '')}
            self.send_ws_message('event/%s/tickets/updates' % id_, json.dumps(ret))
            self.set_status(400)
            return ret
        else:
            old_ticket_data = matching_tickets[0]

        # We have changed the "cancelled" status of a ticket to False; check if we still have a ticket available
        if 'number_of_tickets' in current_event and old_ticket_data.get('cancelled') and not data.get('cancelled'):
            self._check_number_of_tickets(current_event)

        self.add_access_info(data)
        merged, doc = self.db.update('events', query,
                data, updateList='tickets', create=False)
        new_ticket_data = self._get_ticket_data(ticket_query,
                doc.get('tickets') or [])
        env = dict(new_ticket_data)
        # always takes the ticket_id from the new ticket
        ticket_id = str(new_ticket_data.get('_id'))
        env.update({'PERSON_ID': ticket_id, 'TICKED_ID': ticket_id, 'EVENT_ID': id_,
            'EVENT_TITLE': doc.get('title', ''), 'WEB_USER': self.current_user_info.get('username', ''),
            'WEB_REMOTE_IP': self.request.remote_ip})
        stdin_data = {'old': old_ticket_data,
            'new': new_ticket_data,
            'event': doc,
            'merged': merged
        }
        self.run_triggers('update_ticket_in_event', stdin_data=stdin_data, env=env)
        if old_ticket_data and old_ticket_data.get('attended') != new_ticket_data.get('attended'):
            if new_ticket_data.get('attended'):
                self.run_triggers('attends', stdin_data=stdin_data, env=env)

        ret = {'action': 'update', '_id': ticket_id, 'ticket': new_ticket_data,
               'uuid': uuid, 'username': self.current_user_info.get('username', '')}
        if old_ticket_data != new_ticket_data:
            self.send_ws_message('event/%s/tickets/updates' % id_, json.dumps(ret))
        return ret

    def handle_delete_tickets(self, id_, ticket_id):
        # Remove a specific ticket from the list of tickets registered at this event.
        uuid, arguments = self.uuid_arguments
        doc = self.db.query('events',
                {'_id': id_, 'tickets._id': ticket_id})
        ret = {'action': 'delete', '_id': ticket_id, 'uuid': uuid}
        if doc:
            ticket = self._get_ticket_data(ticket_id, doc[0].get('tickets') or [])
            merged, rdoc = self.db.update('events',
                    {'_id': id_},
                    {'tickets': {'_id': ticket_id}},
                    operation='delete',
                    create=False)
            self.send_ws_message('event/%s/tickets/updates' % id_, json.dumps(ret))
            env = dict(ticket)
            env.update({'PERSON_ID': ticket_id, 'TICKED_ID': ticket_id, 'EVENT_ID': id_,
                'EVENT_TITLE': rdoc.get('title', ''), 'WEB_USER': self.current_user_info.get('username', ''),
                'WEB_REMOTE_IP': self.request.remote_ip})
            stdin_data = {'old': ticket,
                'event': rdoc,
                'merged': merged
            }
            self.run_triggers('delete_ticket_in_event', stdin_data=stdin_data, env=env)
        return ret


class UsersHandler(CollectionHandler):
    """Handle requests for Users."""
    document = 'user'
    collection = 'users'

    def filter_get(self, data):
        if 'password' in data:
            del data['password']
        if '_id' in data:
            # Also add a 'tickets' list with all the tickets created by this user
            tickets = []
            events = self.db.query('events', {'tickets.created_by': data['_id']})
            for event in events:
                event_title = event.get('title') or ''
                event_id = str(event.get('_id'))
                evt_tickets = self._filter_results(event.get('tickets') or [], {'created_by': data['_id']})
                for evt_ticket in evt_tickets:
                    evt_ticket['event_title'] = event_title
                    evt_ticket['event_id'] = event_id
                tickets.extend(evt_tickets)
            data['tickets'] = tickets
        return data

    def filter_get_all(self, data):
        if 'users' not in data:
            return data
        for user in data['users']:
            if 'password' in user:
                del user['password']
        return data

    @gen.coroutine
    @authenticated
    def get(self, id_=None, resource=None, resource_id=None, acl=True, **kwargs):
        if id_ is not None:
            if (self.has_permission('user|read') or self.current_user == id_):
                acl = False
        super(UsersHandler, self).get(id_, resource, resource_id, acl=acl, **kwargs)

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

    def filter_input_put(self, data):
        old_pwd = data.get('old_password')
        new_pwd = data.get('new_password')
        if old_pwd is not None:
            del data['old_password']
        if new_pwd is not None:
            del data['new_password']
            authorized, user = self.user_authorized(data['username'], old_pwd)
            if not (self.has_permission('user|update') or (authorized and
                                                           self.current_user_info.get('username') == data['username'])):
                raise InputException('not authorized to change password')
            data['password'] = utils.hash_password(new_pwd)
        if '_id' in data:
            del data['_id']
        if 'username' in data:
            del data['username']
        if not self.has_permission('admin|all'):
            if 'permissions' in data:
                del data['permissions']
        else:
            if 'isAdmin' in data:
                if not 'permissions' in data:
                    data['permissions'] = []
                if 'admin|all' in data['permissions'] and not data['isAdmin']:
                    data['permissions'].remove('admin|all')
                elif 'admin|all' not in data['permissions'] and data['isAdmin']:
                    data['permissions'].append('admin|all')
                del data['isAdmin']
        return data

    @gen.coroutine
    @authenticated
    def put(self, id_=None, resource=None, resource_id=None, **kwargs):
        if id_ is None:
            return self.build_error(status=404, message='unable to access the resource')
        if not (self.has_permission('user|update') or self.current_user == id_):
            return self.build_error(status=401, message='insufficient permissions: user|update or current user')
        super(UsersHandler, self).put(id_, resource, resource_id, **kwargs)


class EbCSVImportPersonsHandler(BaseHandler):
    """Importer for CSV files exported from Eventbrite."""
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
        'Titolo professionale': 'job title',
        'Azienda': 'company',
        'Prefisso': 'name_title',
        'Prefisso (Sig., Sig.ra, ecc.)': 'name title',

        'Order #': 'order_nr',
        'Prefix': 'name title',
        'First Name': 'name',
        'Last Name': 'surname',
        'Suffix': 'name suffix',
        'Email': 'email',
        'Attendee #': 'attendee_nr',
        'Barcode #': 'ebqrcode',
        'Company': 'company'
    }

    @gen.coroutine
    @authenticated
    def post(self, **kwargs):
        # import a CSV list of persons
        event_handler = EventsHandler(self.application, self.request)
        event_handler.db = self.db
        event_handler.logger = self.logger
        event_id = None
        try:
            event_id = self.get_body_argument('targetEvent')
        except:
            pass
        if event_id is None:
            return self.build_error('invalid event')
        reply = dict(total=0, valid=0, merged=0, new_in_event=0)
        event_details = event_handler.db.query('events', {'_id': event_id})
        if not event_details:
            return self.build_error('invalid event')
        all_emails = set()
        #[x.get('email') for x in (event_details[0].get('tickets') or []) if x.get('email')])
        for ticket in (event_details[0].get('tickets') or []):
            all_emails.add('%s_%s_%s' % (ticket.get('name'), ticket.get('surname'), ticket.get('email')))
        for fieldname, contents in self.request.files.items():
            for content in contents:
                filename = content['filename']
                parseStats, persons = utils.csvParse(content['body'], remap=self.csvRemap)
                reply['total'] += parseStats['total']
                for person in persons:
                    if not person:
                        continue
                    reply['valid'] += 1
                    person['attended'] = False
                    person['from_file'] = filename
                    self.add_access_info(person)
                    duplicate_check = '%s_%s_%s' % (person.get('name'), person.get('surname'), person.get('email'))
                    if duplicate_check in all_emails:
                        continue
                    all_emails.add(duplicate_check)
                    event_handler.handle_post_tickets(event_id, None, person)
                    reply['new_in_event'] += 1
        self.write(reply)


class SettingsHandler(BaseHandler):
    """Handle requests for Settings."""
    @gen.coroutine
    @authenticated
    def get(self, **kwargs):
        query = self.arguments_tobool()
        settings = self.db.query('settings', query)
        self.write({'settings': settings})


class InfoHandler(BaseHandler):
    """Handle requests for information about the logged in user."""
    @gen.coroutine
    def get(self, **kwargs):
        info = {}
        user_info = self.current_user_info
        if user_info:
            info['user'] = user_info
        info['authentication_required'] = self.authentication
        self.write({'info': info})


class WebSocketEventUpdatesHandler(tornado.websocket.WebSocketHandler):
    """Manage WebSockets."""
    def _clean_url(self, url):
        url = re_slashes.sub('/', url)
        ridx = url.rfind('?')
        if ridx != -1:
            url = url[:ridx]
        return url

    def open(self, event_id, *args, **kwargs):
        try:
            self.uuid = self.get_argument('uuid')
        except:
            self.uuid = None
        url = self._clean_url(self.request.uri)
        logging.debug('WebSocketEventUpdatesHandler.on_open event_id:%s url:%s' % (event_id, url))
        _ws_clients.setdefault(url, {})
        if self.uuid and self.uuid not in _ws_clients[url]:
            _ws_clients[url][self.uuid] = self
        logging.debug('WebSocketEventUpdatesHandler.on_open %s clients connected' % len(_ws_clients[url]))

    def on_message(self, message):
        url = self._clean_url(self.request.uri)
        logging.debug('WebSocketEventUpdatesHandler.on_message url:%s' % url)
        count = 0
        _to_delete = set()
        for uuid, client in _ws_clients.get(url, {}).items():
            try:
                client.write_message(message)
            except:
                _to_delete.add(uuid)
                continue
            count += 1
        for uuid in _to_delete:
            try:
                del _ws_clients[url][uuid]
            except KeyError:
                pass
        logging.debug('WebSocketEventUpdatesHandler.on_message sent message to %d clients' % count)


class LoginHandler(RootHandler):
    """Handle user authentication requests."""

    @gen.coroutine
    def get(self, **kwargs):
        # show the login page
        if self.is_api():
            self.set_status(401)
            self.write({'error': True,
                'message': 'authentication required'})

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
        authorized, user = self.user_authorized(username, password)
        if authorized and 'username' in user and '_id' in user:
            id_ = str(user['_id'])
            username = user['username']
            logging.info('successful login for user %s (id: %s)' % (username, id_))
            self.set_secure_cookie("user", id_)
            self.write({'error': False, 'message': 'successful login'})
            return
        logging.info('login failed for user %s' % username)
        self.set_status(401)
        self.write({'error': True, 'message': 'wrong username and password'})


class LogoutHandler(BaseHandler):
    """Handle user logout requests."""
    @gen.coroutine
    def get(self, **kwargs):
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

    ssl_options = {}
    if os.path.isfile(options.ssl_key) and os.path.isfile(options.ssl_cert):
        ssl_options = dict(certfile=options.ssl_cert, keyfile=options.ssl_key)

    # database backend connector
    db_connector = monco.Monco(url=options.mongo_url, dbName=options.db_name)
    init_params = dict(db=db_connector, data_dir=options.data_dir, listen_port=options.port,
            authentication=options.authentication, logger=logger, ssl_options=ssl_options)

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
    _events_path = r"/events/?(?P<id_>[\w\d_-]+)?/?(?P<resource>[\w\d_-]+)?/?(?P<resource_id>[\w\d_-]+)?"
    _users_path = r"/users/?(?P<id_>[\w\d_-]+)?/?(?P<resource>[\w\d_-]+)?/?(?P<resource_id>[\w\d_-]+)?"
    application = tornado.web.Application([
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
        cookie_secret=cookie_secret,
        login_url='/login',
        debug=options.debug)
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
    try:
        run()
    except KeyboardInterrupt:
        print('Stop server')
