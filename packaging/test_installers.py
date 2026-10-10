"""Exercise the macOS package script against temporary homes, never Fusion files."""
from pathlib import Path
import hashlib
import json
import platform
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(platform.system() == 'Darwin', 'macOS installer uses ditto')
class MacInstallerTests(unittest.TestCase):
    def run_install(self, source, home, check=True):
        return subprocess.run(['sh', str(ROOT / 'packaging/macos/install-user.sh'),
                               str(source), str(home), 'unused-nonroot-test-user'],
                              capture_output=True, text=True, check=check)

    def test_install_upgrade_and_settings(self):
        with tempfile.TemporaryDirectory(prefix='Printable Threads test ') as temporary:
            home = Path(temporary)
            parent = home / 'Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns'
            settings = home / 'Library/Application Support/PrintableThreads/settings.json'
            settings.parent.mkdir(parents=True)
            settings.write_text('{"tolerance":0.5}')
            target = parent / 'PrintableThreads'
            target.mkdir(parents=True)
            (target / 'old-version.txt').write_text('preserve')
            self.run_install(ROOT / 'PrintableThreads', home)
            self.assertEqual(json.loads((target / 'PrintableThreads.manifest').read_text())['version'], '0.5.2')
            self.assertTrue(list((parent.parent / 'PrintableThreads-backups').rglob('old-version.txt')))
            self.assertEqual(settings.read_text(), '{"tolerance":0.5}')
            for source in (ROOT / 'PrintableThreads').rglob('*'):
                if source.is_file() and '__pycache__' not in source.parts and source.suffix != '.pyc' and source.name != '.DS_Store':
                    self.assertEqual(hashlib.sha256(source.read_bytes()).digest(),
                                     hashlib.sha256((target / source.relative_to(ROOT / 'PrintableThreads')).read_bytes()).digest())
            self.run_install(ROOT / 'PrintableThreads', home)
            self.assertEqual(len(list((parent.parent / 'PrintableThreads-backups').iterdir())), 2)

    def test_symlink_target_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            parent = home / 'Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns'
            parent.mkdir(parents=True)
            outside = home / 'keep'
            outside.mkdir()
            (parent / 'PrintableThreads').symlink_to(outside)
            self.assertNotEqual(self.run_install(ROOT / 'PrintableThreads', home, check=False).returncode, 0)
            self.assertTrue(outside.exists())

    def test_missing_payload_keeps_install(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            target = home / 'Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/PrintableThreads'
            target.mkdir(parents=True)
            marker = target / 'old-version.txt'
            marker.write_text('preserve')
            self.assertNotEqual(self.run_install(home / 'missing', home, check=False).returncode, 0)
            self.assertEqual(marker.read_text(), 'preserve')
