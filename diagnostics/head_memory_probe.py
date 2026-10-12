"""Head sizing, live parameter links and saved recipes in a disposable file."""
import sys,importlib,json,traceback
from pathlib import Path
from dataclasses import replace
import adsk.core as core,adsk.fusion as fusion
repo=Path('/Users/eammon/Documents/GitHub/Fusion-3D-printable-threads');sys.path.insert(0,str(repo))
from PrintableThreads.model import spec as sm
from PrintableThreads.fusion_backend import native
from PrintableThreads.geometry import backend as b
for m in (sm,b,native):importlib.reload(m)
app=core.Application.get();original=app.activeDocument;doc=app.documents.add(core.DocumentTypes.FusionDesignDocumentType);report={'cases':[]}
try:
 d=fusion.Design.cast(app.activeProduct);d.designIntent=fusion.DesignIntentTypes.HybridDesignIntentType
 for automatic in (True,False):
  diameter,height=sm.default_knob_dimensions(4) if automatic else (11,3.5)
  spec=replace(sm.Spec().with_circular_section(2),root_diameter=4,pitch=4,length=7.3,output='Screw',knob='Lobed',knob_diameter=diameter,knob_height=height,entry=0,cut_screw=True,print_on_plate=True).validate()
  made=native.create(d,spec,lambda offset=0:b.M(),{'_auto_knob':automatic,'_auto_knob_height':automatic})
  body=made[0].component.bRepBodies.item(0)
  prefix=body.attributes.itemByName('PrintableThreads.native','parameters').value
  remembered=native.read_recipe(d,body)
  assert remembered.knob=='Lobed' and abs(remembered.knob_diameter-diameter)<1e-6 and abs(remembered.knob_height-height)<1e-6
  d.userParameters.itemByName(prefix+'diameter').expression='8 mm';d.computeAll()
  body=made[0].component.bRepBodies.item(0);remembered=native.read_recipe(d,body)
  expected=sm.default_knob_dimensions(8) if automatic else (11,3.5)
  assert abs(remembered.root_diameter-8)<1e-6
  assert abs(remembered.knob_diameter-expected[0])<1e-6 and abs(remembered.knob_height-expected[1])<1e-6
  assert body.isSolid
  assert abs(body.boundingBox.maxPoint.x*10-expected[0]/2)<.02
  report['cases'].append({'automatic':automatic,'initial_head':[diameter,height],'after_thread_diameter_8mm':[remembered.knob_diameter,remembered.knob_height],'saved_recipe':True,'solid':body.isSolid})
 report['passed']=True
except Exception:report['error']=traceback.format_exc()
finally:
 doc.close(False)
 if original and original.isValid:original.activate()
 (repo/'docs/head-memory-0.5.5.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
