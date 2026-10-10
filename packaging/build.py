#!/usr/bin/env python3
"""Maintainer build: clean Fusion payload, portable ZIP and native macOS PKG."""
from pathlib import Path
import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = json.loads((ROOT / 'PrintableThreads/PrintableThreads.manifest').read_text())['version']


def payload_files():
    for path in sorted((ROOT / 'PrintableThreads').rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts and path.name != '.DS_Store' and path.suffix != '.pyc':
            yield path


def portable(output):
    target = output / f'PrintableThreads-{VERSION}.zip'
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in payload_files():
            archive.write(path, path.relative_to(ROOT))
        for name in ('README.md', 'install.py', 'Install-macOS.command', 'Install-Windows.cmd', 'docs/INSTALLATION.md'):
            archive.write(ROOT / name, name)
    return target


def macos(output):
    if platform.system() != 'Darwin':
        raise RuntimeError('Build macOS packages on macOS.')
    target = output / f'PrintableThreads-{VERSION}-macOS-unsigned.pkg'
    with tempfile.TemporaryDirectory(prefix='printablethreads-package-') as temporary:
        stage = Path(temporary)
        scripts = stage / 'scripts'
        scripts.mkdir()
        for name in ('postinstall', 'install-user.sh'):
            shutil.copy2(ROOT / 'packaging/macos' / name, scripts / name)
            (scripts / name).chmod(0o755)
        for path in payload_files():
            destination = scripts / path.relative_to(ROOT)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
        component = stage / 'component.pkg'
        subprocess.run(['pkgbuild', '--nopayload', '--scripts', str(scripts), '--identifier',
                        'com.ealitt.printablethreads', '--version', VERSION, str(component)], check=True)
        resources = stage / 'resources'
        resources.mkdir()
        for name, source in [('welcome.html', 'INSTALL.txt'), ('conclusion.html', 'ACTIVATE.txt')]:
            import html
            text = html.escape((ROOT / 'packaging' / source).read_text())
            (resources / name).write_text('<html><body><pre style="font:14px -apple-system;white-space:pre-wrap">' + text + '</pre></body></html>')
        distribution = stage / 'Distribution.xml'
        distribution.write_text(f'''<?xml version="1.0" encoding="utf-8"?>
<installer-gui-script minSpecVersion="2">
  <title>Printable Threads {VERSION} for Autodesk Fusion</title>
  <welcome file="welcome.html" mime-type="text/html"/>
  <conclusion file="conclusion.html" mime-type="text/html"/>
  <options customize="never" require-scripts="true" rootVolumeOnly="true"/>
  <domains enable_anywhere="false" enable_currentUserHome="false" enable_localSystem="true"/>
  <choices-outline><line choice="default"/></choices-outline>
  <choice id="default" visible="false"><pkg-ref id="com.ealitt.printablethreads"/></choice>
  <pkg-ref id="com.ealitt.printablethreads" version="{VERSION}" auth="Root">component.pkg</pkg-ref>
</installer-gui-script>''')
        subprocess.run(['productbuild', '--distribution', str(distribution), '--package-path', str(stage),
                        '--resources', str(resources), str(target)], check=True)
    return target


def checksums(output):
    files = sorted(p for p in output.iterdir() if p.is_file() and p.suffix in ('.zip', '.pkg', '.exe'))
    (output / 'SHA256SUMS.txt').write_text(''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n' for p in files))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--macos', action='store_true')
    parser.add_argument('--checksums-only', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if not args.checksums_only:
        print(portable(args.output))
        if args.macos:
            print(macos(args.output))
    checksums(args.output)
