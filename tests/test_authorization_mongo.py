"""Opt-in API checks against a disposable MongoDB database, never the app database.

Run with EVENTMAN_TEST_MONGO_URL pointing to an isolated test MongoDB instance.
Each test creates and removes a uniquely named database.
"""

import json
import logging
import os
import secrets
import unittest

import tornado.web
from tornado.testing import AsyncHTTPTestCase

import eventman_server as server
from monco import Monco
from test_authorization import FakeDatabase, QuietEvents, QuietUsers, SECRET
from tools.rotate_cookie_secret import rotate_cookie_secret
from utils import hash_password, verify_password


@unittest.skipUnless(os.environ.get('EVENTMAN_TEST_MONGO_URL'), 'Requires disposable EVENTMAN_TEST_MONGO_URL')
class MongoAuthorizationTests(AsyncHTTPTestCase):
    def get_app(self):
        self.database_name = 'eventman_security_test_' + secrets.token_hex(8)
        self.db = Monco(self.database_name, url=os.environ['EVENTMAN_TEST_MONGO_URL'])
        fixtures = FakeDatabase()
        for user in fixtures.users.values():
            user['password'] = hash_password('public-integration-fixture-password')
            self.db.add('users', user)
        self.db.add('events', fixtures.event)
        for setting in fixtures.settings:
            self.db.add('settings', setting)
        params = {'db': self.db, 'authentication': True, 'logger': logging.getLogger()}
        return tornado.web.Application([
            ('/v1.0/events/?(?P<id_>[\\w_-]+)?/?(?P<resource>[\\w_-]+)?/?(?P<resource_id>[\\w_-]+)?', QuietEvents, params),
            ('/v1.0/users/?(?P<id_>[\\w_-]+)?', QuietUsers, params),
            ('/users/?(?P<id_>[\\w_-]+)?', QuietUsers, params),
            ('/login', server.LoginHandler, dict(params, secure_cookies=False)),
            ('/v1.0/settings', server.SettingsHandler, params),
        ], cookie_secret=SECRET, xsrf_cookies=True)

    def tearDown(self):
        try:
            self.db.connection.drop_database(self.database_name)
            self.db.connection.close()
        finally:
            super().tearDown()

    def request(self, path, user='owner', method='GET', data=None, xsrf=True, secret=SECRET):
        token = '0123456789abcdef0123456789abcdef'
        cookie = '_xsrf=' + token
        if user:
            cookie += '; user=' + tornado.web.create_signed_value(secret, 'user', user).decode()
        headers = {'Cookie': cookie}
        if xsrf:
            headers['X-Xsrftoken'] = token
        return self.fetch(path, method=method, headers=headers,
                          body=json.dumps(data or {}) if method in ('POST', 'PUT') else None)

    def test_ticket_ownership_staff_updates_and_missing_delete(self):
        path = '/v1.0/events/event/tickets/own-ticket'
        self.assertEqual(self.request(path, 'other').code, 403)
        self.assertEqual(self.request(path, method='PUT', data={'name': 'Updated owner'}).code, 200)
        self.assertEqual(self.request(path, 'staff', 'PUT', {'attended': True}).code, 200)
        ticket = self.db.get('events', 'event')['tickets'][0]
        self.assertEqual(ticket['created_by'], 'owner')
        self.assertTrue(ticket['attended'])
        self.assertEqual(self.request('/v1.0/events/event/tickets/missing', 'staff', 'DELETE').code, 404)
        self.assertEqual(len(self.db.get('events', 'event')['tickets']), 2)
        self.assertEqual(self.request(path, 'staff', 'DELETE').code, 200)
        self.assertEqual([ticket['_id'] for ticket in self.db.get('events', 'event')['tickets']], ['other-ticket'])

    def test_account_registration_and_password_updates_redact_hashes(self):
        response = self.request('/v1.0/users', method='POST', data={
            'username': 'new-fixture-user', 'password': 'public-new-account-password', 'permissions': ['admin|all']})
        self.assertEqual(response.code, 200)
        account = json.loads(response.body)
        self.assertNotIn('password', account)
        self.assertNotIn('permissions', account)
        response = self.request('/v1.0/users/owner', method='PUT', data={
            'old_password': 'public-integration-fixture-password', 'new_password': 'public-new-fixture-password'})
        self.assertEqual(response.code, 200)
        self.assertNotIn('password', json.loads(response.body))
        self.assertEqual(verify_password('public-new-fixture-password', self.db.get('users', 'owner')['password']), (True, False))

    def test_anonymous_registration_and_login_preserve_xsrf_and_role_boundaries(self):
        for path in ('/users', '/v1.0/users'):
            credentials = {'username': 'guest-' + path.replace('/', '-').replace('.', '-'),
                           'password': 'public-guest-fixture-password', 'permissions': ['admin|all'], 'isAdmin': True}
            rejected = self.request(path, user=None, method='POST', data=credentials, xsrf=False)
            self.assertEqual(rejected.code, 403)
            self.assertEqual(json.loads(rejected.body)['message'], 'Forbidden')
            self.assertFalse(self.db.getOne('users', {'username': credentials['username']}))
            response = self.request(path, user=None, method='POST', data=credentials)
            self.assertEqual(response.code, 200)
            self.assertNotIn('password', json.loads(response.body))
            account = self.db.getOne('users', {'username': credentials['username']})
            self.assertNotIn('permissions', account)
            self.assertNotIn('isAdmin', account)
            response = self.request('/login', user=None, method='POST', data=credentials)
            self.assertEqual(response.code, 200)
            self.assertIn('user=', response.headers.get('Set-Cookie', ''))
        self.assertEqual(self.request('/v1.0/users/owner', user=None, method='POST', data={'email': 'unauthorized'}).code, 401)
        self.assertEqual(self.request('/v1.0/users/owner', user=None, method='PUT', data={'email': 'unauthorized'}).code, 401)
        self.assertNotIn('email', self.db.get('users', 'owner'))

    def test_xsrf_protection_remains_required(self):
        path = '/v1.0/events/event/tickets/own-ticket'
        self.assertEqual(self.request(path, method='PUT', data={'name': 'Rejected'}, xsrf=False).code, 403)
        self.assertEqual(self.db.get('events', 'event')['tickets'][0]['name'], 'Fixture owner')

    def test_settings_redaction_and_real_key_rotation(self):
        self.assertNotIn(SECRET, self.request('/v1.0/settings', 'admin').body.decode())
        rotate_cookie_secret(self.db.db['settings'])
        new_secret = self.db.getOne('settings', {'setting': 'server_cookie_secret'})['cookie_secret']
        self._app.settings['cookie_secret'] = new_secret
        self.assertEqual(self.request('/v1.0/settings', 'admin').code, 401)
        self.assertEqual(self.request('/v1.0/settings', 'admin', secret=new_secret).code, 200)
