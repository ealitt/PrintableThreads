#!/usr/bin/env python3
"""Install a self-contained copy; existing installs are backed up, never deleted."""
from pathlib import Path
import argparse
import datetime
import os
import platform
import shutil

def destination():
    if platform.system()=='Darwin':return Path.home()/'Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns'
    if platform.system()=='Windows':return Path(os.environ['APPDATA'])/'Autodesk/Autodesk Fusion 360/API/AddIns'
    raise RuntimeError('Fusion requires macOS or Windows. Use --destination for packaging tests.')

def install(parent):
    source=Path(__file__).resolve().parent/'PrintableThreads';target=parent/'PrintableThreads'
    parent.mkdir(parents=True,exist_ok=True)
    if target.exists():
        backup=parent.parent/'PrintableThreads-backups'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        backup.parent.mkdir(parents=True,exist_ok=True)
        shutil.move(str(target),str(backup));print('Previous installation backed up to:',backup)
    try:shutil.copytree(source,target,ignore=shutil.ignore_patterns('__pycache__','*.pyc','.DS_Store'))
    except Exception:
        if target.exists():shutil.rmtree(target)
        if 'backup' in locals():shutil.move(str(backup),str(target))
        raise
    print('Installed:',target)
    print('Fusion: Utilities > Add-Ins > Scripts and Add-Ins > PrintableThreads > Run.')
    print('Then open Design > Solid > Create > Printable Threads.')
    print('Enable Run on Startup if desired. Restart Fusion if it does not appear.')
    return target

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--destination',type=Path)
    args=parser.parse_args();install(args.destination or destination())
