"""Last valid settings, stored outside the add-in so updates preserve them."""
import json
import os
import sys
from pathlib import Path

def settings_path():
    if sys.platform=='darwin':root=Path.home()/'Library/Application Support'
    else:root=Path(os.environ.get('APPDATA',Path.home()/'.config'))
    return root/'PrintableThreads'/'settings.json'

def load(mode,path=None):
    try:
        data=json.loads((path or settings_path()).read_text())
        if data.get('schema')!=1:return {}
        value=data.get('modes',{}).get(mode,{})
        return value if isinstance(value,dict) else {}
    except (OSError,ValueError,TypeError,AttributeError):return {}

def save(mode,state,path=None):
    path=path or settings_path()
    try:data=json.loads(path.read_text())
    except (OSError,ValueError):data={}
    if not isinstance(data,dict) or data.get('schema')!=1 or not isinstance(data.get('modes'),dict):
        data={'schema':1,'modes':{}}
    data['modes'][mode]=state
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data,indent=2))
    temporary.replace(path)
