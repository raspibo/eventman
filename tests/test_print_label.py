"""Label temporary-file security tests; CUPS is mocked and never contacted."""

import importlib.util
import io
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch

try:
    from PIL import Image, ImageFont
except ImportError:
    Image = ImageFont = None


@unittest.skipIf(Image is None, 'Install Pillow from requirements-printing.txt')
class LabelTemporaryFileTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location(
            'print_label', Path(__file__).resolve().parents[1]
            / 'data/triggers-available/print_label.py'
        )
        self.label = importlib.util.module_from_spec(spec)
        self.cups = Mock()
        with patch.dict(sys.modules, {'cups': self.cups}):
            spec.loader.exec_module(self.label)
        directory = tempfile.TemporaryDirectory(prefix='eventman-label-test-')
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        # Exercise real Pillow PNG output without requiring external barcode fonts.
        font = ImageFont.load_default()
        for guard in [
            patch.object(self.label, '_get_resource', return_value='test-font'),
            patch.object(self.label.ImageFont, 'truetype', return_value=font),
            patch.object(self.label.tempfile, 'tempdir', directory.name),
        ]:
            guard.start()
            self.addCleanup(guard.stop)

    def build_label(self):
        return self.label.build_label(64, 32, '123', 'Test attendee', 'Company')

    def test_private_complete_png_and_retention_in_both_modes(self):
        for keep in [False, True]:
            with self.subTest(keep=keep), patch.object(self.label, 'KEEP_IMG', keep):
                with self.build_label() as label_file:
                    path = Path(label_file.name)
                    self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
                    with Image.open(path) as image:
                        self.assertEqual(image.format, 'PNG')
                        self.assertEqual(image.size, (64, 32))
                        image.load()
                self.assertTrue(label_file.closed)
                self.assertEqual(path.exists(), keep)

    def test_concurrent_creations_have_distinct_names(self):
        with patch.object(self.label, 'KEEP_IMG', False):
            with ThreadPoolExecutor(max_workers=4) as executor:
                files = list(executor.map(lambda _: self.build_label(), range(8)))
            try:
                self.assertEqual(len({item.name for item in files}), 8)
                self.assertTrue(all(Path(item.name).is_file() for item in files))
            finally:
                for item in files:
                    item.close()
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_generation_failure_closes_and_removes_partial_files(self):
        def fail_save(image, destination, **kwargs):
            destination.write(b'partial PNG')
            opened_files.append(destination)
            raise OSError('test generation failure')

        for keep in [False, True]:
            opened_files = []
            with self.subTest(keep=keep), patch.object(self.label, 'KEEP_IMG', keep):
                with patch.object(Image.Image, 'save', fail_save):
                    with self.assertRaisesRegex(OSError, 'test generation failure'):
                        self.build_label()
                self.assertTrue(opened_files[0].closed)
                self.assertEqual(list(self.directory.iterdir()), [])

    def check_submission(self, keep, fail):
        opened_files = []
        real_build = self.label.build_label

        def capture_build(*args):
            result = real_build(*args)
            opened_files.append(result)
            return result

        def submit(printer, filename, name, options):
            self.assertEqual(printer, 'mock-printer')
            self.assertFalse(opened_files[0].closed)
            with Image.open(filename) as image:
                image.load()
            if fail:
                raise OSError('test CUPS failure')

        self.cups.Connection.return_value.getDefault.return_value = 'mock-printer'
        self.cups.Connection.return_value.printFile.side_effect = submit
        with patch.object(self.label, 'KEEP_IMG', keep), \
                patch.object(self.label, 'LABEL_WIDTH', 64), \
                patch.object(self.label, 'LABEL_HEIGHT', 32), \
                patch.object(self.label, 'build_label', side_effect=capture_build), \
                patch.object(sys, 'stdin', io.StringIO('{}')), \
                patch.dict(os.environ, {'NAME': 'Test', 'SURNAME': 'Attendee'}):
            if fail:
                with self.assertRaisesRegex(OSError, 'test CUPS failure'):
                    self.label.run()
            else:
                self.label.run()
        self.assertTrue(opened_files[0].closed)
        self.assertEqual(Path(opened_files[0].name).exists(), keep)

    def test_submission_closes_file_and_preserves_retention(self):
        for keep in [False, True]:
            with self.subTest(keep=keep):
                self.check_submission(keep, fail=False)

    def test_submission_failure_closes_file_and_preserves_retention(self):
        for keep in [False, True]:
            with self.subTest(keep=keep):
                self.check_submission(keep, fail=True)
