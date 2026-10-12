"""Browser security checks. Set EVENTMAN_BROWSER to a Chromium executable.

Run: EVENTMAN_BROWSER=/path/to/chrome python3 -m unittest discover -s tests \
     -p 'test_frontend_routes.py'
API and live-update connections are stubbed; no service or database is used.
"""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


@unittest.skipUnless(os.environ.get('EVENTMAN_BROWSER'), 'Set EVENTMAN_BROWSER for browser checks')
class FrontendRouteTests(unittest.TestCase):
    def test_routes_and_links_in_desktop_and_mobile_browser(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / 'angular_app/js/modern-app.js').read_text()
        bootstrap = "window.addEventListener('hashchange', render);\nawait refreshInfo();\nrender();"
        self.assertIn(bootstrap, source)
        source = source.replace(bootstrap, '')
        checks = (root / 'tests/frontend_routes_checks.js').read_text()
        shell = (root / 'angular_app/index.html').read_text()
        # Inline the real client and local styles so the test needs no HTTP server.
        shell = shell.replace('<link rel="stylesheet" href="/static/css/eventman-modern.css">',
                              '<style>' + (root / 'static/css/eventman-modern.css').read_text() + '</style>')
        script = source + '\ntry {\n' + checks + '''
document.querySelector('#test-result').textContent = 'PASS';
} catch (error) {
document.querySelector('#test-result').textContent = 'FAIL: ' + error.message;
}
'''
        shell = shell.replace('<script type="module" src="/js/modern-app.js"></script>',
                              '<script type="module">' + script.replace('</', '<\\/') + '</script>')
        shell = shell.replace('</body>', '<pre id="test-result">PENDING</pre></body>')
        with tempfile.TemporaryDirectory(prefix='eventman-browser-') as directory:
            page = Path(directory) / 'routes.html'
            page.write_text(shell)
            for size in ['1280,900', '390,844']:
                with self.subTest(size=size):
                    result = subprocess.run([
                        os.environ['EVENTMAN_BROWSER'], '--headless', '--no-sandbox',
                        '--disable-gpu', '--disable-background-networking',
                        '--no-first-run', '--no-default-browser-check',
                        '--user-data-dir=' + str(Path(directory) / ('profile-' + size)),
                        '--window-size=' + size, '--virtual-time-budget=3000',
                        '--dump-dom', page.as_uri(),
                    ], capture_output=True, text=True, timeout=45)
                    self.assertEqual(result.returncode, 0, result.stderr[-2000:])
                    self.assertTrue('<pre id="test-result">PASS</pre>' in result.stdout,
                                    result.stdout[-3000:])
