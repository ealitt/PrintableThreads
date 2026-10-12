"""Compare beta snapshot work in a separate disposable Fusion file."""
import sys,importlib,json,time,types,traceback
from pathlib import Path
from dataclasses import replace
import adsk.core as core,adsk.fusion as fusion
repo=Path('/Users/eammon/Documents/GitHub/Fusion-3D-printable-threads');sys.path.insert(0,str(repo))
from PrintableThreads.model.spec import Spec
from PrintableThreads.geometry import backend as b
from PrintableThreads.fusion_backend import selection,preview
for m in (b,selection,preview):importlib.reload(m)
installed=Path.home()/'Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/PrintableThreads/fusion_backend'
old_selection=types.ModuleType('baseline_selection');old_selection.__package__='PrintableThreads.fusion_backend'
exec(compile((installed/'selection.py').read_text(),'baseline_selection.py','exec'),old_selection.__dict__)
old_preview=types.ModuleType('baseline_preview')
exec(compile((installed/'preview.py').read_text(),'baseline_preview.py','exec'),old_preview.__dict__)
app=core.Application.get();original=app.activeDocument;doc=app.documents.add(core.DocumentTypes.FusionDesignDocumentType)
report={};renderer=None
try:
 d=fusion.Design.cast(app.activeProduct);d.designIntent=fusion.DesignIntentTypes.HybridDesignIntentType;c=d.rootComponent
 selected=[]
 for i in range(2):
  b.persist(c,[b.cylinder(6,i*18,(i+1)*18)],'Disposable benchmark target')
  body=c.bRepBodies.item(i)
  selected.append(next(f for f in body.faces if core.Cylinder.cast(f.geometry)))
 spec=replace(Spec().with_circular_section(2),cut_screw=True,root_diameter=12,pitch=3,length=36,knob='None',entry=0,output='Screw').validate()
 plans=selection.shared_frames(selected)
 for baseline in (True,False):
  renderer=(old_preview.Renderer() if baseline else preview.Renderer()).begin(c)
  start=time.perf_counter()
  tool=None if baseline else selection.preview_tool(d,spec,False)
  render_seconds=0
  for group,shared in plans:
   candidate=old_selection.preview_body(d,group,spec,shared=shared) if baseline else selection.preview_body(d,group,spec,shared=shared,prepared=tool)
   render_start=time.perf_counter();renderer.draw_body(candidate,group[0].body);render_seconds+=time.perf_counter()-render_start
  renderer.finish()
  report['baseline' if baseline else 'optimized']={'snapshot_seconds':time.perf_counter()-start,'render_seconds':render_seconds,'helix_builds':2 if baseline else 1,'targets':2}
  renderer.clear();renderer=None
 report['speedup']=report['baseline']['snapshot_seconds']/report['optimized']['snapshot_seconds']
 report['passed']=True
except Exception:report['error']=traceback.format_exc()
finally:
 if renderer:renderer.clear()
 doc.close(False)
 if original and original.isValid:original.activate()
 (repo/'docs/preview-performance-0.5.5.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
