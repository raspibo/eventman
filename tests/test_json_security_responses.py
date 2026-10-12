"""Regression evidence for CodeQL's JSON-response XSS false positives."""

import json
from unittest.mock import Mock
from urllib.parse import urlencode

import tornado.web
from tornado.testing import AsyncHTTPTestCase

from eventman_server import BaseHandler, EventsHandler, UsersHandler


PAYLOAD = '<img src=x onerror="alert(1)"></script><script>alert(2)</script>'


class ErrorProbe(BaseHandler):
    def get(self):
        self.build_error(self.get_argument('message'))


class AuthorizedUserProbe(UsersHandler):
    def has_permission(self, permission):
        return True


class JsonSecurityResponseTests(AsyncHTTPTestCase):
    def get_app(self):
        self.db = Mock()
        self.db.query.return_value = []
        params = {'authentication': False, 'db': self.db}
        return tornado.web.Application([
            ('/error', ErrorProbe),
            ('/events/(?P<id_>[\\w_-]+)', EventsHandler, params),
            ('/users/(?P<id_>[\\w_-]+)', AuthorizedUserProbe, params),
        ], cookie_secret='disposable-response-test-secret', xsrf_cookies=True)

    def json_response(self, path, expected_status):
        response = self.fetch(path)
        self.assertEqual(response.code, expected_status)
        self.assertEqual(response.headers['Content-Type'], 'application/json; charset=UTF-8')
        self.assertNotIn('text/html', response.headers['Content-Type'])
        return json.loads(response.body)

    def test_reflected_error_is_json_data(self):
        data = self.json_response('/error?' + urlencode({'message': PAYLOAD}), 400)
        self.assertEqual(data, {'error': True, 'message': PAYLOAD})

    def test_event_document_preserves_markup_as_json_data(self):
        self.db.get.return_value = {'_id': 'fixture-event', 'title': PAYLOAD, 'description': PAYLOAD}
        data = self.json_response('/events/fixture-event', 200)
        self.assertEqual(data['title'], PAYLOAD)
        self.assertEqual(data['description'], PAYLOAD)
        self.db.get.assert_called_once_with('events', 'fixture-event')

    def test_user_document_is_json_and_excludes_password(self):
        self.db.get.return_value = {'_id': 'fixture-user', 'username': PAYLOAD,
                                   'password': 'fixture-sensitive-value'}
        data = self.json_response('/users/fixture-user', 200)
        self.assertEqual(data['username'], PAYLOAD)
        self.assertNotIn('password', data)

    def test_missing_document_is_still_a_json_object(self):
        self.db.get.return_value = {}
        self.assertEqual(self.json_response('/events/missing', 200), {})
