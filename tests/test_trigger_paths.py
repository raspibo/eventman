"""Trigger selection/confinement checks; subprocess execution is stubbed."""

import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from tornado import gen
from tornado.testing import AsyncTestCase, gen_test

from eventman_server import CollectionHandler


class TriggerPathTests(AsyncTestCase):
    def setUp(self):
        super().setUp()
        directory = tempfile.TemporaryDirectory(prefix='eventman-triggers-test-')
        self.addCleanup(directory.cleanup)
        self.base = Path(directory.name)
        self.data = self.base / 'data'
        self.action_dir = self.data / 'triggers/attends.d'
        self.action_dir.mkdir(parents=True)
        self.calls = []
        self.handler = CollectionHandler.__new__(CollectionHandler)
        self.handler.data_dir = str(self.data)

        @gen.coroutine
        def capture(cmd, stdin_data, env):
            self.calls.append((cmd, stdin_data, env))
            return b'', b''

        self.handler.run_subprocess = capture

    def script(self, path, executable=True):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('#!/bin/sh\nexit 0\n')
        path.chmod(0o700 if executable else 0o600)
        return path

    @gen_test
    def test_only_executable_regular_files_receive_original_payload(self):
        executable = self.script(self.action_dir / 'safe.sh')
        self.script(self.action_dir / 'README.md', executable=False)
        (self.action_dir / 'directory').mkdir()
        (self.action_dir / 'dangling').symlink_to(self.data / 'missing')
        payload = {'new': {'name': 'Test attendee'}}
        env = {'NAME': 'Test attendee'}
        yield self.handler.run_triggers('attends', payload, env)
        self.assertEqual(self.calls, [([str(executable)], json.dumps(payload), env)])

    @gen_test
    def test_invalid_actions_never_reach_glob_or_file_checks(self):
        for action in ['../outside', '/absolute', 'attends/other', 'attends\\other',
                       '*', 'attends?', '[abc]', '', 'attends\n', 'évent', None, 1]:
            with self.subTest(action=action), patch('glob.glob') as discover, \
                    patch('os.path.isfile') as isfile, patch('os.access') as access:
                with self.assertLogs(level='WARNING'):
                    yield self.handler.run_triggers(action)
                discover.assert_not_called()
                isfile.assert_not_called()
                access.assert_not_called()
        self.assertEqual(self.calls, [])

    @gen_test
    def test_supported_actions_keep_their_names(self):
        for action in ['create_event', 'update_event_tickets', 'delete_event',
                       'create_ticket_in_event', 'update_ticket_in_event',
                       'delete_ticket_in_event', 'custom-action_1']:
            script = self.script(self.data / 'triggers' / (action + '.d') / 'safe.sh')
            yield self.handler.run_triggers(action)
            self.assertEqual(self.calls[-1], ([str(script)], '{}', None))

    @gen_test
    def test_script_links_inside_data_root_are_allowed(self):
        target = self.script(self.data / 'triggers-available/safe.sh')
        intermediate = self.data / 'triggers-available/alias.sh'
        intermediate.symlink_to(target.name)
        (self.action_dir / 'enabled.sh').symlink_to('../../triggers-available/alias.sh')
        yield self.handler.run_triggers('attends')
        self.assertEqual(self.calls, [([str(target)], '{}', None)])

    @gen_test
    def test_action_directory_alias_inside_trigger_root_is_allowed(self):
        script = self.script(self.action_dir / 'safe.sh')
        (self.data / 'triggers/alias.d').symlink_to('attends.d', target_is_directory=True)
        yield self.handler.run_triggers('alias')
        self.assertEqual(self.calls, [([str(script)], '{}', None)])

    @gen_test
    def test_handler_without_data_directory_is_a_noop(self):
        del self.handler.data_dir
        with patch('glob.glob') as discover:
            yield self.handler.run_triggers('attends')
            discover.assert_not_called()
        self.assertEqual(self.calls, [])

    @gen_test
    def test_escaping_script_links_are_rejected_before_file_checks(self):
        target = self.script(self.base / 'data-sibling/escape.sh')
        (self.action_dir / 'escape.sh').symlink_to(target)
        with patch('os.path.isfile') as isfile, patch('os.access') as access:
            with self.assertLogs(level='WARNING'):
                yield self.handler.run_triggers('attends')
            isfile.assert_not_called()
            access.assert_not_called()
        self.assertEqual(self.calls, [])

    @gen_test
    def test_action_directory_escape_is_rejected_before_discovery(self):
        outside = self.data / 'triggers-available'
        self.script(outside / 'escape.sh')
        alias = self.data / 'triggers/escape.d'
        alias.symlink_to(outside, target_is_directory=True)
        with patch('glob.glob') as discover:
            with self.assertLogs(level='WARNING'):
                yield self.handler.run_triggers('escape')
            discover.assert_not_called()
        self.assertEqual(self.calls, [])

    @gen_test
    def test_trigger_root_escape_is_rejected_before_discovery(self):
        outside = self.base / 'external-triggers'
        self.script(outside / 'attends.d/escape.sh')
        (self.data / 'redirected').mkdir()
        (self.data / 'redirected/triggers').symlink_to(outside, target_is_directory=True)
        self.handler.data_dir = str(self.data / 'redirected')
        with patch('glob.glob') as discover:
            with self.assertLogs(level='WARNING'):
                yield self.handler.run_triggers('attends')
            discover.assert_not_called()
        self.assertEqual(self.calls, [])

    @gen_test
    def test_missing_action_directory_is_a_noop(self):
        yield self.handler.run_triggers('not_configured')
        self.assertEqual(self.calls, [])

    @gen_test
    def test_configured_data_root_may_be_a_symlink(self):
        script = self.script(self.action_dir / 'safe.sh')
        alias = self.base / 'configured-data'
        alias.symlink_to(self.data, target_is_directory=True)
        self.handler.data_dir = str(alias)
        yield self.handler.run_triggers('attends')
        self.assertEqual(self.calls, [([str(script)], '{}', None)])
