import sys
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import dashboard as d

class DashboardTests(unittest.TestCase):
    def test_workspace_counts_hardlinks_once_and_does_not_follow_symlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'model').write_bytes(b'x' * 65536)
            with patch.object(d, 'WORKSPACE', root):
                d.scan_workspace()
                before = d._disk_cache['workspace_bytes']
                (root/'alias').hardlink_to(root/'model')
                (root/'loop').symlink_to(root, target_is_directory=True)
                d.scan_workspace()
                self.assertEqual(d._disk_cache['workspace_bytes'], before)

    def test_all_logs_download_includes_full_files_and_requires_auth(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp)/'container.log'
            first.write_text('FIRST LINE\n' + 'middle\n' * 2000 + 'LAST LINE\n')
            second = Path(tmp)/'models.log'
            second.write_text('MODEL ERROR\n')
            files = {'container': first, 'models': second, 'jupyter': Path(tmp)/'absent.log'}
            with patch.object(d, 'LOG_FILES', files), patch.object(d, 'DASHBOARD_PASSWORD', ''):
                server = d.ThreadingHTTPServer(('127.0.0.1', 0), d.Handler)
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                base = f'http://127.0.0.1:{server.server_port}'
                try:
                    with urllib.request.urlopen(base+'/api/logs/all?download=1') as response:
                        text = response.read().decode()
                        self.assertIn('attachment;', response.headers['Content-Disposition'])
                    for expected in ['FIRST LINE', 'LAST LINE', 'MODEL ERROR', '(no output yet)']:
                        self.assertIn(expected, text)
                    with patch.object(d, 'DASHBOARD_PASSWORD', 'test'):
                        with self.assertRaises(urllib.error.HTTPError) as error:
                            urllib.request.urlopen(base+'/api/logs/all')
                        self.assertEqual(error.exception.code, 401)
                finally:
                    server.shutdown();server.server_close();thread.join()
