"""Real subprocess I/O checks using disposable Python scripts only."""

import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

from tornado import gen
from tornado.testing import AsyncTestCase, gen_test

from eventman_server import CollectionHandler


class TriggerSubprocessTests(AsyncTestCase):
    def setUp(self):
        super().setUp()
        self.handler = CollectionHandler.__new__(CollectionHandler)
        directory = tempfile.TemporaryDirectory(prefix='eventman-subprocess-test-')
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.executions = 0

    def command(self, source):
        self.executions += 1
        script = self.directory / ('fixture_%d.py' % self.executions)
        script.write_text(source, encoding='utf-8')
        return [sys.executable, str(script)]

    @gen_test
    def test_unicode_input_environment_and_both_output_streams(self):
        command = self.command('''import os, sys
sys.stdout.buffer.write(sys.stdin.buffer.read())
sys.stderr.write(os.environ['TEST_VALUE'])
''')
        payload = 'Test attendee é\n'
        out, err = yield self.handler.run_subprocess(command, payload, {'test_value': 42})
        self.assertEqual(out, payload.encode('utf-8'))
        self.assertEqual(err, b'42')

    @gen_test
    def test_missing_input_closes_stdin(self):
        command = self.command('''import sys
assert sys.stdin.buffer.read() == b''
sys.stdout.write('EOF received')
''')
        out, err = yield self.handler.run_subprocess(command)
        self.assertEqual((out, err), (b'EOF received', b''))

    @gen_test
    def test_large_output_is_drained_while_large_input_is_written(self):
        command = self.command('''import sys
sys.stdout.buffer.write(b'o' * 262144)
sys.stdout.flush()
sys.stderr.buffer.write(b'e' * 262144)
sys.stderr.flush()
sys.stdout.buffer.write(sys.stdin.buffer.read())
''')
        payload = b'i' * 262144
        out, err = yield self.handler.run_subprocess(command, payload)
        self.assertEqual(out, b'o' * 262144 + payload)
        self.assertEqual(err, b'e' * 262144)

    @gen_test
    def test_early_nonzero_exit_preserves_stderr(self):
        command = self.command('''import sys
sys.stderr.write('fixture failure')
sys.exit(7)
''')
        out, err = yield self.handler.run_subprocess(command, b'i' * 262144)
        self.assertEqual((out, err), (b'', b'fixture failure'))

    @gen_test
    def test_normal_exit_cancels_kill_timeout(self):
        command = self.command("print('finished')\n")
        with patch('eventman_server.PROCESS_TIMEOUT', 0.3), \
                patch.object(self.handler, 'on_timeout') as timeout:
            out, err = yield self.handler.run_subprocess(command)
            yield gen.sleep(0.35)
            timeout.assert_not_called()
        self.assertEqual((out, err), (b'finished\n', b''))

    @gen_test
    def test_timeout_kills_child_and_returns_output(self):
        command = self.command('''import sys, time
sys.stdout.write('started')
sys.stdout.flush()
time.sleep(30)
''')
        observed = []
        real_timeout = self.handler.on_timeout
        real_exit = self.handler.on_exit

        def timeout(cmd, pipe):
            observed.append(pipe)
            real_timeout(cmd, pipe)

        with patch('eventman_server.PROCESS_TIMEOUT', 0.2), \
                patch.object(self.handler, 'on_timeout', side_effect=timeout), \
                patch.object(self.handler, 'on_exit', wraps=real_exit) as on_exit:
            out, err = yield self.handler.run_subprocess(command)
            yield gen.sleep(0.05)
        self.assertEqual((out, err), (b'started', b''))
        self.assertEqual(len(observed), 1)
        self.assertIsNotNone(observed[0].proc.poll())
        on_exit.assert_called_once()
        self.assertLess(on_exit.call_args.args[0], 0)

    @gen_test
    def test_confined_available_trigger_executes_end_to_end(self):
        self.handler.data_dir = str(self.directory)
        available = self.directory / 'triggers-available'
        action = self.directory / 'triggers/attends.d'
        available.mkdir()
        action.mkdir(parents=True)
        result = self.directory / 'fixture-result.json'
        script = available / 'echo.py'
        script.write_text('#!' + sys.executable + '''
import json, os, sys
with open(os.environ['TEST_RESULT'], 'w') as result:
    json.dump({'stdin': json.load(sys.stdin), 'name': os.environ['NAME']}, result)
''', encoding='utf-8')
        script.chmod(0o700)
        (action / 'enabled.py').symlink_to('../../triggers-available/echo.py')
        payload = {'new': {'name': 'Test attendee'}}
        yield self.handler.run_triggers('attends', payload,
                                       {'name': 'Test attendee', 'test_result': str(result)})
        self.assertEqual(json.loads(result.read_text()),
                         {'stdin': payload, 'name': 'Test attendee'})
