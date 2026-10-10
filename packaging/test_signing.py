"""Exercise signing gates without certificates, keys or network calls."""
import base64
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).parent / 'macos/sign.py'
spec = importlib.util.spec_from_file_location('package_signer', MODULE)
signer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(signer)


class SigningTests(unittest.TestCase):
    def environment(self):
        values = {name: 'test-placeholder' for name in signer.REQUIRED}
        values.update(APPLE_INSTALLER_IDENTITY='Developer ID Installer: Test Publisher (TESTTEAM)',
                      APPLE_INSTALLER_P12_BASE64=base64.b64encode(b'fake-certificate').decode(),
                      APPLE_NOTARY_KEY_BASE64=base64.b64encode(b'fake-key').decode())
        return values

    def test_missing_credentials_never_invokes_tools(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(signer, 'run') as run:
            with self.assertRaisesRegex(RuntimeError, 'Missing GitHub signing configuration'):
                signer.sign(Path('unsigned.pkg'), Path('signed.pkg'))
            run.assert_not_called()

    def test_self_signed_identity_is_rejected(self):
        values = self.environment()
        values['APPLE_INSTALLER_IDENTITY'] = 'Self-signed test'
        with patch.dict(os.environ, values, clear=True), patch.object(signer, 'run') as run:
            with self.assertRaisesRegex(RuntimeError, 'Developer ID Installer'):
                signer.sign(Path('unsigned.pkg'), Path('signed.pkg'))
            run.assert_not_called()

    def scenario(self, accepted):
        calls = []
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'signed.pkg'
            def fake_run(*args, capture=False):
                calls.append(args)
                if args[:2] == ('security', 'list-keychains') and len(args) == 4:
                    return '"/tmp/original.keychain-db"\n'
                if args[0] == 'productsign':
                    output.write_bytes(b'test-signed-output')
                if args[:2] == ('xcrun', 'notarytool'):
                    return json.dumps({'status': 'Accepted' if accepted else 'Invalid'})
                if args[0] == 'pkgutil':
                    return self.environment()['APPLE_INSTALLER_IDENTITY']
                return ''
            with patch.dict(os.environ, self.environment(), clear=True), patch.object(signer, 'run', side_effect=fake_run), patch('builtins.print'):
                if accepted:
                    signer.sign(Path('unsigned.pkg'), output)
                    self.assertTrue(output.exists())
                else:
                    with self.assertRaisesRegex(RuntimeError, 'notarization was not accepted'):
                        signer.sign(Path('unsigned.pkg'), output)
                    self.assertFalse(output.exists())
        return calls

    def test_accepted_run_requires_stapling_and_gatekeeper(self):
        calls = self.scenario(True)
        self.assertTrue(any(c[:3] == ('xcrun', 'stapler', 'staple') for c in calls))
        self.assertTrue(any(c[:3] == ('xcrun', 'stapler', 'validate') for c in calls))
        self.assertTrue(any(c[0] == 'spctl' for c in calls))
        self.assertTrue(any(c[:5] == ('security', 'list-keychains', '-d', 'user', '-s') and c[-1] == '/tmp/original.keychain-db' for c in calls))

    def test_rejection_cannot_leave_signed_download(self):
        calls = self.scenario(False)
        self.assertFalse(any(c[0] == 'spctl' for c in calls))
