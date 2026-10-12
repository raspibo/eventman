"""Security regression checks for Eventbrite API import responses.

Run from the repository root:
    python3 -m unittest discover -s tests -p 'test_*.py'
"""

import json
import logging
from unittest.mock import Mock, patch

import tornado.web
from tornado.testing import AsyncHTTPTestCase

from eventman_server import EbAPIImportHandler


class AdminImportProbe(EbAPIImportHandler):
    def has_permission(self, permission):
        return permission == 'admin|all'


class EventbriteErrorTests(AsyncHTTPTestCase):
    def get_app(self):
        self.db = Mock()
        return tornado.web.Application([
            ('/ebapi', AdminImportProbe, {
                'authentication': False,
                'db': self.db,
                'logger': logging.getLogger(),
            }),
        ], cookie_secret='disposable-test-cookie-secret')

    def import_event(self):
        return self.fetch('/ebapi', method='POST', body=json.dumps({
            'oauthToken': 'fake-oauth-token',
            'eventID': '123',
            'targetEvent': 'existing-event',
            'create': False,
        }))

    def test_exception_details_are_absent_from_response_and_logs(self):
        details = 'fake-oauth-token /private/sdk/config <img src=x onerror=alert(1)>'
        with patch('utils.ebAPIFetch', side_effect=RuntimeError(details)) as fetch:
            with self.assertLogs(level='WARNING') as logs:
                response = self.import_event()

        self.assertEqual(response.code, 400)
        self.assertTrue(response.headers['Content-Type'].startswith('application/json'))
        self.assertEqual(json.loads(response.body), {
            'error': True, 'message': 'Eventbrite import failed',
        })
        self.assertIn('Eventbrite import failed (RuntimeError)', '\n'.join(logs.output))
        for sensitive_value in details.split():
            self.assertNotIn(sensitive_value, response.body.decode())
            self.assertNotIn(sensitive_value, '\n'.join(logs.output))
        for record in logs.records:
            self.assertIsNone(record.exc_info)
        fetch.assert_called_once_with(oauthToken='fake-oauth-token', eventID='123')
        self.assertEqual(self.db.mock_calls, [])

    def test_successful_empty_import_preserves_response(self):
        with patch('utils.ebAPIFetch', return_value={'event': {}, 'attendees': []}):
            response = self.import_event()

        self.assertEqual(response.code, 200)
        self.assertEqual(json.loads(response.body), {
            'total': 0, 'valid': 0, 'merged': 0, 'new_in_event': 0,
        })
        self.assertEqual(self.db.mock_calls, [])

    def test_missing_information_preserves_error(self):
        with patch('utils.ebAPIFetch', return_value={}):
            response = self.import_event()

        self.assertEqual(response.code, 400)
        self.assertEqual(json.loads(response.body), {
            'error': True, 'message': 'Missing information from Eventbrite API',
        })
        self.assertEqual(self.db.mock_calls, [])
