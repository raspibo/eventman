"""Issue #147 authorization tests with fake users, secrets, and database records."""

import copy
import json
import logging
from urllib.parse import urlencode
from unittest.mock import patch

import tornado.web
import tornado.httpserver
import tornado.websocket
from tornado import gen
from tornado.testing import AsyncHTTPTestCase, gen_test, bind_unused_port

import eventman_server as server


SECRET = 'public-authorization-fixture-secret'


class FakeDatabase:
    def __init__(self):
        self.users = {
            'owner': {'_id': 'owner', 'username': 'owner', 'password': 'fixture-hash', 'permissions': []},
            'other': {'_id': 'other', 'username': 'other', 'password': 'fixture-hash', 'permissions': []},
            'admin': {'_id': 'admin', 'username': 'admin', 'password': 'fixture-hash', 'permissions': ['admin|all']},
            'staff': {'_id': 'staff', 'username': 'staff', 'password': 'fixture-hash',
                      'permissions': ['event:tickets-all|read', 'event:tickets|update', 'event:tickets|delete']},
        }
        self.event = {'_id': 'event', 'title': 'Fixture event', 'begin_date': '2000-01-01',
                      'ticket_sales_end_date': '2099-01-01T00:00:00Z', 'tickets': [
                          {'_id': 'own-ticket', 'created_by': 'owner', 'name': 'Fixture owner'},
                          {'_id': 'other-ticket', 'created_by': 'other', 'name': 'Fixture other'},
                      ]}
        self.settings = [{'setting': 'server_cookie_secret', 'cookie_secret': SECRET},
                         {'setting': 'logo', 'value': 'fixture.png', 'cookie_secret': 'unexpected-secret'},
                         {'setting': 'ticket_custom_field', 'label': 'Company', 'key': 'company', 'type': 'string'}]
        self.writes = []
        self.queries = []

    def getOne(self, collection, query):
        return copy.deepcopy(self.users.get(query.get('_id'), {})) if collection == 'users' else {}

    def get(self, collection, identifier):
        if collection == 'events' and identifier == 'event':
            return copy.deepcopy(self.event)
        if collection == 'users':
            return copy.deepcopy(self.users.get(identifier, {}))
        return {}

    def query(self, collection, query=None):
        self.queries.append((collection, query))
        if collection == 'settings':
            return [copy.deepcopy(record) for record in self.settings
                    if all(record.get(key) == value for key, value in (query or {}).items())]
        if collection == 'events':
            return [copy.deepcopy(self.event)]
        return []

    def update(self, collection, query, data, **kwargs):
        self.writes.append((collection, query, copy.deepcopy(data), kwargs))
        if collection == 'users':
            self.users[query].update(data)
            return True, copy.deepcopy(self.users[query])
        if kwargs.get('operation') == 'delete':
            identifier = data['tickets'].get('_id')
            self.event['tickets'] = [ticket for ticket in self.event['tickets'] if ticket['_id'] != identifier]
        else:
            for ticket in self.event['tickets']:
                if ticket['_id'] == query.get('tickets._id'):
                    ticket.update(data)
        return True, copy.deepcopy(self.event)


class QuietEvents(server.EventsHandler):
    def run_triggers(self, *args, **kwargs):
        pass

    def send_ws_message(self, *args, **kwargs):
        pass


class QuietUsers(server.UsersHandler):
    def run_triggers(self, *args, **kwargs):
        pass


class AuthorizationTests(AsyncHTTPTestCase):
    def setUp(self):
        super().setUp()
        self.connections = []
        app = tornado.web.Application([
            ('/ws/event/(?P<event_id>[\\w_-]+)/tickets/updates', server.InternalWebSocketPublisher),
        ])
        socket, port = bind_unused_port()
        self.publisher_url = 'ws://127.0.0.1:%d/ws/event/event/tickets/updates?uuid=publisher' % port
        self.publisher_server = tornado.httpserver.HTTPServer(app)
        self.publisher_server.add_socket(socket)

    def tearDown(self):
        for connection in self.connections:
            connection.close()
        self.io_loop.run_sync(lambda: gen.sleep(0.01))
        self.publisher_server.stop()
        super().tearDown()

    def get_app(self):
        self.db = FakeDatabase()
        self.params = {'db': self.db, 'authentication': True, 'logger': logging.getLogger()}
        return tornado.web.Application([
            ('/v1.0/settings', server.SettingsHandler, self.params),
            ('/info', server.InfoHandler, self.params),
            ('/v1.0/events/?(?P<id_>[\\w_-]+)?/?(?P<resource>[\\w_-]+)?/?(?P<resource_id>[\\w_-]+)?',
             QuietEvents, self.params),
            ('/v1.0/tickets', server.TicketsHandler, self.params),
            ('/v1.0/ebapi', server.EbAPIImportHandler, self.params),
            ('/v1.0/ebcsvpersons', server.EbCSVImportPersonsHandler, self.params),
            ('/v1.0/login', server.LoginHandler, dict(self.params, secure_cookies=False)),
            ('/v1.0/users/(?P<id_>[\\w_-]+)', QuietUsers, self.params),
            ('/ws/event/(?P<event_id>[\\w_-]+)/tickets/updates', server.WebSocketEventUpdatesHandler, self.params),
        ], cookie_secret=SECRET, login_url='/login', xsrf_cookies=False)

    def request(self, path, user=None, method='GET', data=None, secret=SECRET):
        headers = {}
        if user:
            headers['Cookie'] = 'user=' + tornado.web.create_signed_value(secret, 'user', user).decode()
        return self.fetch(path, method=method, headers=headers,
                          body=json.dumps(data or {}) if method in ('POST', 'PUT') else None)

    def test_settings_never_publish_signing_secret_or_unknown_fields(self):
        for user in ['owner', 'staff', 'admin']:
            with self.subTest(user=user):
                response = self.request('/v1.0/settings', user)
                self.assertEqual(response.code, 200)
                self.assertNotIn(SECRET, response.body.decode())
                self.assertNotIn('cookie_secret', response.body.decode())
                settings = json.loads(response.body)['settings']
                self.assertEqual({record['setting'] for record in settings}, {'logo', 'ticket_custom_field'})
        response = self.request('/v1.0/settings?setting=server_cookie_secret', 'owner')
        self.assertEqual(json.loads(response.body), {'settings': []})

    def test_info_redacts_user_record_without_mutating_database(self):
        response = self.request('/info', 'owner')
        user = json.loads(response.body)['info']['user']
        self.assertEqual(user['_id'], 'owner')
        self.assertNotIn('password', user)
        self.assertEqual(self.db.users['owner']['password'], 'fixture-hash')

    def test_public_mode_does_not_grant_admin_import_access(self):
        self.params['authentication'] = False
        response = self.request('/v1.0/ebapi', method='POST')
        self.assertEqual(response.code, 403)
        self.assertEqual(self.db.writes, [])
        settings = self.request('/v1.0/settings')
        self.assertEqual(settings.code, 200)
        self.assertNotIn(SECRET, settings.body.decode())

    def test_staff_summary_redaction_uses_consistent_permission_scope(self):
        owner = json.loads(self.request('/v1.0/events/event', 'owner').body)
        staff = json.loads(self.request('/v1.0/events/event', 'staff').body)
        self.assertEqual(owner['tickets'], [])
        self.assertEqual(len(staff['tickets']), 2)

    def test_raw_hash_and_role_fields_cannot_bypass_account_change_checks(self):
        from types import SimpleNamespace
        ordinary = SimpleNamespace(has_permission=lambda permission: False)
        cleaned = server.UsersHandler.filter_input_put(ordinary, {
            'password': 'fixture-raw-hash', 'permissions': ['admin|all'], 'isAdmin': True,
            'email': 'fixture@example.invalid',
        })
        self.assertEqual(cleaned, {'email': 'fixture@example.invalid'})

    def test_deleted_or_wrongly_signed_users_cannot_authenticate(self):
        for user, secret in [('deleted', SECRET), ('admin', 'different-fixture-secret')]:
            with self.subTest(user=user):
                self.assertEqual(self.request('/v1.0/tickets', user, secret=secret).code, 401)

    def test_key_rotation_invalidates_old_cookie(self):
        self._app.settings['cookie_secret'] = 'public-new-fixture-key'
        self.assertEqual(self.request('/v1.0/tickets', 'admin').code, 401)
        self.assertEqual(self.request('/v1.0/tickets', 'admin', secret='public-new-fixture-key').code, 200)

    def test_imports_require_admin_before_sdk_or_database_work(self):
        for path in ['/v1.0/ebapi', '/v1.0/ebcsvpersons']:
            for user, status in [(None, 401), ('owner', 403), ('staff', 403)]:
                with self.subTest(path=path, user=user), patch('utils.ebAPIFetch') as fetch:
                    self.assertEqual(self.request(path, user, 'POST').code, status)
                    fetch.assert_not_called()
                    self.assertEqual(self.db.writes, [])

    def test_operator_query_keys_are_rejected_before_database_access(self):
        for path in ['/v1.0/settings', '/v1.0/events']:
            before = len(self.db.queries)
            response = self.request(path + '?' + urlencode({'$where': 'fixture-expression'}), 'admin')
            self.assertEqual(response.code, 400)
            self.assertEqual(len(self.db.queries), before)

    def test_nonstring_login_credentials_never_reach_query(self):
        for data in [{'username': {'$ne': None}, 'password': 'fixture'},
                     {'username': 'owner', 'password': {'$ne': None}}]:
            response = self.request('/v1.0/login', method='POST', data=data)
            self.assertEqual(response.code, 401)
        self.assertEqual(self.db.queries, [])

    def test_nested_operator_input_is_rejected_before_event_write(self):
        response = self.request('/v1.0/events/event', 'admin', 'PUT', {'formSchema': {'nested': {'$where': 'fixture'}}})
        self.assertEqual(response.code, 400)
        self.assertEqual(self.db.writes, [])

    def test_owner_reads_own_ticket_but_not_other_ticket_or_bulk_list(self):
        self.assertEqual(self.request('/v1.0/events/event/tickets/own-ticket', 'owner').code, 200)
        self.assertEqual(self.request('/v1.0/events/event/tickets/other-ticket', 'owner').code, 403)
        self.assertEqual(self.request('/v1.0/events/event/tickets', 'owner').code, 403)
        self.assertEqual(self.request('/v1.0/events/event/tickets/own-ticket').code, 401)
        self.assertEqual(self.request('/v1.0/events/event/tickets/other-ticket', 'staff').code, 200)
        self.assertEqual(self.request('/v1.0/events/event/tickets', 'staff').code, 200)

    def test_owner_edits_own_ticket_only_and_cannot_mark_attendance(self):
        path = '/v1.0/events/event/tickets/own-ticket'
        response = self.request(path, 'owner', 'PUT', {'name': 'Updated owner', 'cancelled': True})
        self.assertEqual(response.code, 200)
        self.assertEqual(self.db.event['tickets'][0]['created_by'], 'owner')
        before = len(self.db.writes)
        self.assertEqual(self.request('/v1.0/events/event/tickets/other-ticket', 'owner', 'PUT',
                                      {'name': 'Unauthorized'}).code, 403)
        for field in ['attended', 'afternoon_attended', 'checked_in_by', 'seq_hex']:
            with self.subTest(field=field):
                self.assertEqual(self.request(path, 'owner', 'PUT', {field: True}).code, 403)
        self.assertEqual(len(self.db.writes), before)

    def test_staff_updates_attendance_without_taking_ticket_ownership(self):
        response = self.request('/v1.0/events/event/tickets/own-ticket', 'staff', 'PUT', {'attended': True})
        self.assertEqual(response.code, 200)
        self.assertTrue(self.db.event['tickets'][0]['attended'])
        self.assertEqual(self.db.event['tickets'][0]['created_by'], 'owner')

    def test_missing_ticket_delete_does_not_delete_other_tickets(self):
        response = self.request('/v1.0/events/event/tickets/missing', 'staff', 'DELETE')
        self.assertEqual(response.code, 404)
        self.assertEqual(self.db.writes, [])
        self.assertEqual(len(self.db.event['tickets']), 2)
        self.assertEqual(self.request('/v1.0/events/event/tickets/own-ticket', 'owner', 'DELETE').code, 403)
        self.assertEqual(self.request('/v1.0/events/event/tickets/own-ticket', 'staff', 'DELETE').code, 200)
        self.assertEqual([ticket['_id'] for ticket in self.db.event['tickets']], ['other-ticket'])

    def test_public_mode_does_not_turn_ticket_ids_into_bearer_capabilities(self):
        self.params['authentication'] = False
        self.assertEqual(self.request('/v1.0/events/event/tickets/own-ticket').code, 403)
        self.assertEqual(self.request('/v1.0/events/event/tickets/own-ticket', method='PUT',
                                      data={'name': 'Unauthorized'}).code, 403)
        self.assertEqual(self.db.writes, [])

    def test_ordinary_users_cannot_update_or_delete_events(self):
        self.assertEqual(self.request('/v1.0/events/event', 'owner', 'PUT', {'title': 'Unauthorized'}).code, 401)
        self.assertEqual(self.request('/v1.0/events/event', 'owner', 'DELETE').code, 401)
        self.assertEqual(self.db.writes, [])

    def test_account_password_change_uses_current_identity_without_username_input(self):
        from utils import hash_password, verify_password
        self.db.users['owner']['password'] = hash_password('fixture-old-password')
        path = '/v1.0/users/owner'
        self.assertEqual(self.request(path, 'owner', 'PUT', {
            'old_password': 'wrong', 'new_password': 'fixture-new-password',
        }).code, 403)
        self.assertEqual(self.db.writes, [])
        self.assertEqual(self.request(path, 'owner', 'PUT', {
            'old_password': 'fixture-old-password', 'new_password': 'fixture-new-password',
        }).code, 200)
        self.assertEqual(verify_password('fixture-new-password', self.db.users['owner']['password']), (True, False))
        self.assertNotIn('password', json.loads(self.request(path, 'owner', 'PUT', {'email': 'fixture@example.invalid'}).body))
        self.assertEqual(self.request('/v1.0/users/other', 'owner', 'PUT', {'email': 'unauthorized'}).code, 401)

    def test_staff_cannot_claim_ownerless_ticket_by_editing_it(self):
        self.db.event['tickets'][0].pop('created_by')
        response = self.request('/v1.0/events/event/tickets/own-ticket', 'staff', 'PUT', {'name': 'Updated guest'})
        self.assertEqual(response.code, 200)
        self.assertIsNone(self.db.event['tickets'][0]['created_by'])
        self.assertEqual(self.request('/v1.0/events/event/tickets/own-ticket', 'owner').code, 403)

    def test_json_array_body_is_rejected_before_event_write(self):
        response = self.fetch('/v1.0/events/event', method='PUT', body='[1,2]', headers={
            'Cookie': 'user=' + tornado.web.create_signed_value(SECRET, 'user', 'admin').decode(),
        })
        self.assertEqual(response.code, 400)
        self.assertEqual(self.db.writes, [])

    async def websocket(self, user=None):
        headers = {}
        if user:
            headers['Cookie'] = 'user=' + tornado.web.create_signed_value(SECRET, 'user', user).decode()
        request = tornado.httpclient.HTTPRequest(
            self.get_url('/ws/event/event/tickets/updates?uuid=' + (user or 'anonymous')).replace('http:', 'ws:'),
            headers=headers)
        connection = await tornado.websocket.websocket_connect(request)
        self.connections.append(connection)
        return connection

    @gen_test
    async def test_websocket_rejects_anonymous_and_ordinary_users(self):
        for user in [None, 'owner', 'other', 'deleted']:
            connection = await self.websocket(user)
            self.assertIsNone(await connection.read_message())
            self.assertEqual(connection.close_code, 1008)

    @gen_test
    async def test_staff_and_admin_receive_internal_updates(self):
        staff = await self.websocket('staff')
        admin = await self.websocket('admin')
        publisher = await tornado.websocket.websocket_connect(self.publisher_url)
        self.connections.append(publisher)
        message = json.dumps({'action': 'add', 'ticket': {'_id': 'fixture'}})
        publisher.write_message(message)
        self.assertEqual(await staff.read_message(), message)
        self.assertEqual(await admin.read_message(), message)

    @gen_test
    async def test_public_socket_cannot_publish_even_from_loopback(self):
        admin = await self.websocket('admin')
        admin.write_message('fixture forged update')
        self.assertIsNone(await admin.read_message())
        self.assertEqual(admin.close_code, 1008)

    @gen_test
    async def test_revoked_staff_socket_is_closed_before_delivery(self):
        staff = await self.websocket('staff')
        self.db.users['staff']['permissions'] = []
        publisher = await tornado.websocket.websocket_connect(self.publisher_url)
        self.connections.append(publisher)
        publisher.write_message('{}')
        self.assertIsNone(await staff.read_message())
        self.assertEqual(staff.close_code, 1008)
