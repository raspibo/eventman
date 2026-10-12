"""Admin bootstrap regression tests using a fake database and fake passwords."""

from pathlib import Path
import logging
import tempfile
import unittest
from unittest.mock import Mock, patch

from tornado.options import OptionParser

import eventman_server
from eventman_server import ensure_admin
from utils import verify_password


class AdminBootstrapTests(unittest.TestCase):
    def setUp(self):
        logger = logging.getLogger()
        self.addCleanup(logger.setLevel, logger.level)
        self.db = Mock()
        self.db.query.return_value = []
        directory = tempfile.TemporaryDirectory(prefix='eventman-admin-test-')
        self.addCleanup(directory.cleanup)
        self.password_file = Path(directory.name) / 'password'

    def assert_created(self, password):
        self.db.add.assert_called_once()
        collection, user = self.db.add.call_args.args
        self.assertEqual(collection, 'users')
        self.assertEqual(user['username'], 'admin')
        self.assertEqual(user['permissions'], ['admin|all'])
        self.assertTrue(user['password'].startswith('pbkdf2_sha256$'))
        self.assertEqual(verify_password(password, user['password']), (True, False))

    def test_password_file_creates_admin_without_secret_in_logs(self):
        password = ' fake-bootstrap-password-é '
        self.password_file.write_text(password + '\r\n', encoding='utf-8')
        self.password_file.chmod(0o600)
        with self.assertLogs(level='WARNING') as logs:
            ensure_admin(self.db, admin_password_file=str(self.password_file))
        self.assert_created(password)
        self.assertNotIn(password, '\n'.join(logs.output))
        self.assertEqual(logs.records[0].getMessage(), 'Created admin user')
        self.assertEqual(self.password_file.read_text(), password + '\n')

    def test_explicit_password_remains_supported_without_secret_in_logs(self):
        password = 'fake-explicit-bootstrap-password'
        with self.assertLogs(level='WARNING') as logs:
            ensure_admin(self.db, admin_password=password)
        self.assert_created(password)
        self.assertNotIn(password, '\n'.join(logs.output))

    def test_missing_or_empty_password_does_not_create_admin(self):
        for password in [None, '']:
            with self.subTest(password=password):
                with self.assertRaisesRegex(SystemExit, 'Initial admin password required'):
                    ensure_admin(self.db, admin_password=password)
        self.db.add.assert_not_called()

    def test_conflicting_inputs_do_not_create_admin_or_read_file(self):
        with patch('builtins.open') as read:
            with self.assertRaises(SystemExit) as error:
                ensure_admin(self.db, 'fake-conflict-password', 'fake-conflict-path')
        self.assertNotIn('fake-conflict-password', str(error.exception))
        read.assert_not_called()
        self.db.add.assert_not_called()

    def test_invalid_file_contents_do_not_create_admin(self):
        for contents in [b'', b'\n', b'\xff', b'fake-secret\nsecond-line']:
            with self.subTest(contents=contents):
                self.password_file.write_bytes(contents)
                with self.assertRaises(SystemExit) as error:
                    ensure_admin(self.db, admin_password_file=str(self.password_file))
                self.assertNotIn('fake-secret', str(error.exception))
        self.db.add.assert_not_called()

    def test_unreadable_file_does_not_leak_os_error_details(self):
        for error in [FileNotFoundError('fake-private-path'),
                      PermissionError('fake-private-path')]:
            with self.subTest(error=type(error).__name__):
                with patch('builtins.open', side_effect=error):
                    with self.assertRaisesRegex(SystemExit, 'Unable to read') as result:
                        ensure_admin(self.db, admin_password_file=str(self.password_file))
                self.assertNotIn('fake-private-path', str(result.exception))
                self.assertTrue(result.exception.__suppress_context__)
        self.db.add.assert_not_called()

    def test_existing_admin_ignores_all_bootstrap_inputs(self):
        self.db.query.return_value = [{'username': 'admin'}]
        with patch('builtins.open') as read, patch('logging.warning') as warning:
            ensure_admin(self.db)
            ensure_admin(self.db, 'unused-password', 'missing-file')
        read.assert_not_called()
        warning.assert_not_called()
        self.db.add.assert_not_called()

    def test_startup_passes_password_file_option_before_starting_servers(self):
        self.password_file.write_text('fake-startup-password\n', encoding='utf-8')
        parser = OptionParser()
        self.db.query.side_effect = lambda collection, query: (
            [] if collection == 'users' else [{'cookie_secret': 'test-cookie-secret'}]
        )
        with patch.object(eventman_server, 'define', parser.define), \
                patch.object(eventman_server, 'options', parser), \
                patch('tornado.options.parse_command_line', side_effect=lambda: parser.parse_command_line([
                    'eventman_server.py', '--admin_password_file=' + str(self.password_file),
                ])), \
                patch('monco.Monco', return_value=self.db), \
                patch('tornado.httpserver.HTTPServer') as http_server, \
                patch('tornado.ioloop.IOLoop.instance') as loop, \
                self.assertLogs(level='INFO') as logs:
            eventman_server.run()
        self.assert_created('fake-startup-password')
        self.assertNotIn('fake-startup-password', '\n'.join(logs.output))
        self.assertEqual(http_server.call_count, 2)
        loop.return_value.start.assert_called_once()

    def test_startup_without_password_stops_before_starting_servers(self):
        parser = OptionParser()
        with patch.object(eventman_server, 'define', parser.define), \
                patch.object(eventman_server, 'options', parser), \
                patch('tornado.options.parse_command_line', side_effect=lambda: parser.parse_command_line([
                    'eventman_server.py',
                ])), \
                patch('monco.Monco', return_value=self.db), \
                patch('tornado.httpserver.HTTPServer') as http_server:
            with self.assertRaisesRegex(SystemExit, 'Initial admin password required'):
                eventman_server.run()
        self.db.add.assert_not_called()
        http_server.assert_not_called()
