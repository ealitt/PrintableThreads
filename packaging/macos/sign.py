#!/usr/bin/env python3
"""Sign, notarize, staple and verify a PKG. Missing credentials never fall back."""
import argparse
import base64
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile


REQUIRED = ('APPLE_INSTALLER_P12_BASE64', 'APPLE_INSTALLER_P12_PASSWORD',
            'APPLE_INSTALLER_IDENTITY', 'APPLE_NOTARY_KEY_BASE64',
            'APPLE_NOTARY_KEY_ID', 'APPLE_NOTARY_ISSUER_ID')


def run(*args, capture=False):
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode:
        # Never echo command arguments: keychain/import passwords are arguments.
        raise RuntimeError(f'{Path(args[0]).name} failed (exit {result.returncode}). Signed release stopped.')
    return result.stdout if capture else None


def sign(package, output):
    missing = [key for key in REQUIRED if not os.environ.get(key)]
    if missing:
        raise RuntimeError('Missing GitHub signing configuration: ' + ', '.join(missing))
    identity = os.environ['APPLE_INSTALLER_IDENTITY']
    if not identity.startswith('Developer ID Installer: '):
        raise RuntimeError('Use a Developer ID Installer identity, not an application or self-signed certificate.')
    original = run('security', 'list-keychains', '-d', 'user', capture=True)
    search_list = [line.strip().strip('"') for line in original.splitlines() if line.strip()]
    with tempfile.TemporaryDirectory(prefix='printablethreads-sign-') as temporary:
        temporary = Path(temporary)
        keychain = temporary / 'signing.keychain-db'
        certificate = temporary / 'installer.p12'
        notary_key = temporary / 'notary.p8'
        certificate.write_bytes(base64.b64decode(os.environ['APPLE_INSTALLER_P12_BASE64'], validate=True))
        notary_key.write_bytes(base64.b64decode(os.environ['APPLE_NOTARY_KEY_BASE64'], validate=True))
        certificate.chmod(0o600)
        notary_key.chmod(0o600)
        password = secrets.token_urlsafe(32)
        try:
            run('security', 'create-keychain', '-p', password, str(keychain))
            run('security', 'set-keychain-settings', '-lut', '21600', str(keychain))
            run('security', 'unlock-keychain', '-p', password, str(keychain))
            run('security', 'import', str(certificate), '-k', str(keychain), '-P',
                os.environ['APPLE_INSTALLER_P12_PASSWORD'], '-T', '/usr/bin/productsign')
            run('security', 'set-key-partition-list', '-S', 'apple-tool:,apple:', '-s', '-k', password, str(keychain))
            run('security', 'list-keychains', '-d', 'user', '-s', str(keychain), *search_list)
            run('productsign', '--timestamp', '--sign', identity, '--keychain', str(keychain), str(package), str(output))
            result = json.loads(run('xcrun', 'notarytool', 'submit', str(output), '--key', str(notary_key),
                                    '--key-id', os.environ['APPLE_NOTARY_KEY_ID'], '--issuer',
                                    os.environ['APPLE_NOTARY_ISSUER_ID'], '--wait', '--timeout', '30m',
                                    '--output-format', 'json', capture=True))
            if result.get('status') != 'Accepted':
                raise RuntimeError('Apple notarization was not accepted. Signed release stopped.')
            run('xcrun', 'stapler', 'staple', str(output))
            run('xcrun', 'stapler', 'validate', str(output))
            signature = run('pkgutil', '--check-signature', str(output), capture=True)
            if identity not in signature:
                raise RuntimeError('Package signature does not match the configured publisher.')
            run('spctl', '--assess', '--type', 'install', '--verbose=2', str(output))
        except Exception:
            output.unlink(missing_ok=True)
            raise
        finally:
            run('security', 'list-keychains', '-d', 'user', '-s', *search_list)
            if keychain.exists():
                run('security', 'delete-keychain', str(keychain))
    print('Mac package signed, notarized, stapled and verified:', output.name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('package', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.package.resolve() == args.output.resolve():
        parser.error('Keep the unsigned input and signed output separate.')
    try:
        sign(args.package, args.output)
    except Exception as error:
        raise SystemExit(str(error))
