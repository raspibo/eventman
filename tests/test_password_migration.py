"""Legacy retirement and operator-tool checks using fixture passwords and fake MongoDB."""

from contextlib import redirect_stdout
import io
import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from pymongo.errors import OperationFailure

from eventman_server import BaseHandler, UsersHandler
from tools import password_hash_inventory, reset_user_password
from utils import hash_password, password_hash_kind, verify_password


PASSWORD = 'fixture-password'
LEGACY = ('$fixture-salt$59fed5fb503e43920c4c4688315f0b15c79af39f18ab28a6235904962fea4e621'
          '134b8991a644793cce9e49526f43c568d2ea6cbafbbeb2dfee4aceca30d4eed')


class PasswordMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.modern = hash_password(PASSWORD)

    def test_modern_passwords_verify_and_use_random_salts(self):
        self.assertEqual(verify_password(PASSWORD, self.modern), (True, False))
        self.assertEqual(verify_password('incorrect', self.modern), (False, False))
        self.assertNotEqual(self.modern, hash_password(PASSWORD))
        self.assertEqual(password_hash_kind(self.modern), 'pbkdf2_sha256')

    def test_legacy_password_is_rejected_even_when_correct(self):
        self.assertEqual(password_hash_kind(LEGACY), 'legacy_sha512')
        self.assertEqual(verify_password(PASSWORD, LEGACY), (False, False))
        self.assertEqual(verify_password('incorrect', LEGACY), (False, False))
        with self.assertRaises(TypeError):
            hash_password(PASSWORD, salt='fixture-salt')

    def test_legacy_login_is_rejected_without_rewriting_account(self):
        handler = BaseHandler.__new__(BaseHandler)
        handler.db = Mock()
        user = {'_id': 'fixture-id', 'username': 'fixture-user', 'password': LEGACY}
        handler.db.query.return_value = [user]
        self.assertEqual(handler.user_authorized('fixture-user', PASSWORD), (False, {}))
        handler.db.update.assert_not_called()
        self.assertEqual(user['password'], LEGACY)

    def test_modern_login_does_not_rewrite_account(self):
        handler = BaseHandler.__new__(BaseHandler)
        handler.db = Mock()
        user = {'_id': 'fixture-id', 'password': self.modern}
        handler.db.query.return_value = [user]
        self.assertEqual(handler.user_authorized('fixture-user', PASSWORD), (True, user))
        handler.db.update.assert_not_called()

    def test_registration_and_password_change_create_modern_hashes(self):
        handler = UsersHandler.__new__(UsersHandler)
        handler.db = Mock()
        handler.db.query.return_value = []
        handler.gen_id = lambda: 'fixture-id'
        user = handler.filter_input_post_all({'username': 'fixture-user', 'password': PASSWORD})
        self.assertEqual(password_hash_kind(user['password']), 'pbkdf2_sha256')
        self.assertEqual(verify_password(PASSWORD, user['password']), (True, False))
        operator = SimpleNamespace(user_authorized=Mock(return_value=(False, {})),
                                   has_permission=lambda permission: True)
        changed = UsersHandler.filter_input_put(operator, {
            'username': 'fixture-user', 'old_password': 'old', 'new_password': PASSWORD,
        })
        self.assertEqual(verify_password(PASSWORD, changed['password']), (True, False))
        self.assertNotIn('new_password', changed)

    def test_inventory_reads_only_hash_projection_and_returns_counts(self):
        users = Mock()
        users.find.return_value = [{'password': self.modern}, {'password': LEGACY}, {},
                                   {'password': ''}, {'password': 'pbkdf2_sha256$broken'},
                                   {'password': 123}]
        self.assertEqual(password_hash_inventory.inventory(users), {
            'total': 6, 'pbkdf2_sha256': 1, 'legacy_sha512': 1, 'missing': 2, 'unrecognized': 2,
        })
        self.assertEqual(users.mock_calls, [unittest.mock.call.find({}, {'_id': 0, 'password': 1})])

    def test_inventory_cli_prints_only_counts(self):
        output = io.StringIO()
        with patch('sys.argv', ['inventory']), patch('pymongo.MongoClient') as client, redirect_stdout(output):
            users = client.return_value.__enter__.return_value.__getitem__.return_value.__getitem__.return_value
            users.find.return_value = [{'password': LEGACY}]
            password_hash_inventory.main()
        self.assertEqual(json.loads(output.getvalue())['legacy_sha512'], 1)
        self.assertNotIn(LEGACY, output.getvalue())
        self.assertNotIn('fixture-user', output.getvalue())

    def test_inventory_failure_does_not_expose_driver_details(self):
        with patch('sys.argv', ['inventory']), \
                patch('pymongo.MongoClient', side_effect=OperationFailure('fake-uri-secret')):
            with self.assertRaises(SystemExit) as error:
                password_hash_inventory.main()
        self.assertNotIn('fake-uri-secret', str(error.exception))
        self.assertTrue(error.exception.__suppress_context__)

    def test_reset_updates_only_selected_account_password(self):
        users = Mock()
        users.find.return_value.limit.return_value = [{'_id': 'fixture-id'}]
        users.update_one.return_value.matched_count = 1
        reset_user_password.reset_password(users, 'fixture-user', PASSWORD)
        users.find.assert_called_once_with({'username': 'fixture-user'}, {'_id': 1})
        users.find.return_value.limit.assert_called_once_with(2)
        query, update = users.update_one.call_args.args
        self.assertEqual(query, {'_id': 'fixture-id'})
        self.assertEqual(list(update), ['$set'])
        self.assertEqual(list(update['$set']), ['password'])
        self.assertEqual(verify_password(PASSWORD, update['$set']['password']), (True, False))

    def test_operator_reset_restores_legacy_account_login(self):
        user = {'_id': 'fixture-id', 'username': 'fixture-user', 'password': LEGACY,
                'permissions': ['admin|all'], 'email': 'test@example.invalid'}
        handler = BaseHandler.__new__(BaseHandler)
        handler.db = Mock()
        handler.db.query.return_value = [user]
        self.assertEqual(handler.user_authorized('fixture-user', PASSWORD), (False, {}))
        users = Mock()
        users.find.return_value.limit.return_value = [{'_id': user['_id']}]

        def update(query, change):
            user.update(change['$set'])
            return SimpleNamespace(matched_count=1)

        users.update_one.side_effect = update
        reset_user_password.reset_password(users, 'fixture-user', PASSWORD)
        self.assertEqual(handler.user_authorized('fixture-user', PASSWORD), (True, user))
        self.assertEqual(user['permissions'], ['admin|all'])
        self.assertEqual(user['email'], 'test@example.invalid')
        self.assertEqual(user['_id'], 'fixture-id')
        handler.db.update.assert_not_called()

    def test_reset_rejects_missing_duplicate_or_deleted_accounts(self):
        for matches in [[], [{'_id': 'one'}, {'_id': 'two'}]]:
            with self.subTest(matches=matches):
                users = Mock()
                users.find.return_value.limit.return_value = matches
                with self.assertRaises(ValueError):
                    reset_user_password.reset_password(users, 'fixture-user', PASSWORD)
                users.update_one.assert_not_called()
        users = Mock()
        users.find.return_value.limit.return_value = [{'_id': 'deleted'}]
        users.update_one.return_value.matched_count = 0
        with self.assertRaises(ValueError):
            reset_user_password.reset_password(users, 'fixture-user', PASSWORD)

    def test_reset_cli_refuses_nonterminal_empty_or_mismatched_input(self):
        for terminal, values in [(False, []), (True, ['', '']), (True, [PASSWORD, 'different'])]:
            with self.subTest(terminal=terminal, values=values):
                with patch('sys.argv', ['reset', '--username', 'fixture-user']), \
                        patch('sys.stdin.isatty', return_value=terminal), \
                        patch('getpass.getpass', side_effect=values), \
                        patch('pymongo.MongoClient') as client:
                    with self.assertRaises(SystemExit) as error:
                        reset_user_password.main()
                    self.assertNotIn(PASSWORD, str(error.exception))
                    client.assert_not_called()

    def test_reset_cli_refuses_insecure_getpass_fallback(self):
        import getpass
        import warnings

        def insecure_prompt(prompt):
            warnings.warn('Unable to hide input', getpass.GetPassWarning)

        with patch('sys.argv', ['reset', '--username', 'fixture-user']), \
                patch('sys.stdin.isatty', return_value=True), \
                patch('getpass.getpass', side_effect=insecure_prompt), \
                patch('pymongo.MongoClient') as client:
            with self.assertRaisesRegex(SystemExit, 'Unable to read a password securely'):
                reset_user_password.main()
            client.assert_not_called()

    def test_reset_cli_hides_driver_errors(self):
        with patch('sys.argv', ['reset', '--username', 'fixture-user']), \
                patch('sys.stdin.isatty', return_value=True), \
                patch('getpass.getpass', side_effect=[PASSWORD, PASSWORD]), \
                patch('pymongo.MongoClient', side_effect=OperationFailure('fake-uri-secret')):
            with self.assertRaises(SystemExit) as error:
                reset_user_password.main()
        self.assertNotIn('fake-uri-secret', str(error.exception))
        self.assertTrue(error.exception.__suppress_context__)

    def test_reset_cli_success_prints_no_password_or_hash(self):
        output = io.StringIO()
        with patch('sys.argv', ['reset', '--username', 'fixture-user']), \
                patch('sys.stdin.isatty', return_value=True), \
                patch('getpass.getpass', side_effect=[PASSWORD, PASSWORD]), \
                patch('pymongo.MongoClient') as client, redirect_stdout(output):
            users = client.return_value.__enter__.return_value.__getitem__.return_value.__getitem__.return_value
            users.find.return_value.limit.return_value = [{'_id': 'fixture-id'}]
            users.update_one.return_value.matched_count = 1
            reset_user_password.main()
        self.assertEqual(output.getvalue(), 'Password reset complete\n')
        users.update_one.assert_called_once()
