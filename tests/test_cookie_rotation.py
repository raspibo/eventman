"""Signing-key rotation tests with fake settings and public fixture keys."""

from contextlib import redirect_stdout
import io
import unittest
from unittest.mock import Mock, patch

from tools import rotate_cookie_secret


class CookieRotationTests(unittest.TestCase):
    def test_rotation_changes_only_one_existing_key_without_returning_it(self):
        settings = Mock()
        settings.find.return_value.limit.return_value = [{'_id': 'key-record'}]
        settings.update_one.return_value.matched_count = 1
        with patch('secrets.token_urlsafe', return_value='public-new-fixture-key') as generate:
            self.assertIsNone(rotate_cookie_secret.rotate_cookie_secret(settings))
        generate.assert_called_once_with(48)
        settings.update_one.assert_called_once_with({'_id': 'key-record'},
                                                    {'$set': {'cookie_secret': 'public-new-fixture-key'}})

    def test_missing_or_duplicate_records_are_not_changed(self):
        for records in [[], [{'_id': 'one'}, {'_id': 'two'}]]:
            with self.subTest(records=records):
                settings = Mock()
                settings.find.return_value.limit.return_value = records
                with self.assertRaises(ValueError):
                    rotate_cookie_secret.rotate_cookie_secret(settings)
                settings.update_one.assert_not_called()

    def test_cli_requires_acknowledgment_without_contacting_database(self):
        with patch('sys.argv', ['rotate']), patch('pymongo.MongoClient') as client:
            with self.assertRaisesRegex(SystemExit, 'requires --yes'):
                rotate_cookie_secret.main()
            client.assert_not_called()

    def test_cli_does_not_print_generated_key(self):
        output = io.StringIO()
        with patch('sys.argv', ['rotate', '--yes']), patch('pymongo.MongoClient') as client, \
                patch('secrets.token_urlsafe', return_value='public-new-fixture-key'), redirect_stdout(output):
            settings = client.return_value.__enter__.return_value.__getitem__.return_value.__getitem__.return_value
            settings.find.return_value.limit.return_value = [{'_id': 'key-record'}]
            settings.update_one.return_value.matched_count = 1
            rotate_cookie_secret.main()
        self.assertNotIn('public-new-fixture-key', output.getvalue())
        self.assertIn('restart', output.getvalue())
