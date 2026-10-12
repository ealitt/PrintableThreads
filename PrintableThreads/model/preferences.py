"""Last valid settings, stored outside the add-in so updates preserve them."""
import json
import os
import sys
from pathlib import Path
from .spec import Spec
from dataclasses import replace

THREAD_FIELDS=('root_diameter','pitch','section','height','width','crest','radius','starts','length','radial_clearance','axial_clearance','left_hand','phase','cut_screw')

def settings_path():
    if sys.platform=='darwin':root=Path.home()/'Library/Application Support'
    else:root=Path(os.environ.get('APPDATA',Path.home()/'.config'))
    return root/'PrintableThreads'/'settings.json'

def load(mode,path=None):
    try:
        data=json.loads((path or settings_path()).read_text())
        if data.get('schema')!=1:return {}
        value=data.get('modes',{}).get(mode,{})
        if not isinstance(value,dict):return {}
        if mode in ('create','apply'):
            shared=data.get('thread_settings') or (data.get('modes',{}).get('apply',{}) if mode=='create' else {})
            if isinstance(shared,dict) and shared.get('recipe'):
                thread=Spec.from_json(shared['recipe'])
                head=Spec.from_json(value['recipe']) if value.get('recipe') else Spec()
                combined=replace(head,**{key:getattr(thread,key) for key in THREAD_FIELDS})
                value=dict(value,recipe=combined.to_json(),inherit_thread=True)
        return value
    except (OSError,ValueError,TypeError,AttributeError):return {}

def save(mode,state,path=None):
    path=path or settings_path()
    try:data=json.loads(path.read_text())
    except (OSError,ValueError):data={}
    if not isinstance(data,dict) or data.get('schema')!=1 or not isinstance(data.get('modes'),dict):
        data={'schema':1,'modes':{}}
    data['modes'][mode]=state
    if mode in ('create','apply') and state.get('recipe'):data['thread_settings']={'recipe':state['recipe']}
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data,indent=2))
    temporary.replace(path)
