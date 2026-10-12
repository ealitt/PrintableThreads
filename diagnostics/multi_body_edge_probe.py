"""Shared instances, partial lengths and gap regressions; disposable documents."""
import sys,importlib,json,traceback
from pathlib import Path
from dataclasses import replace
import adsk.core as core,adsk.fusion as fusion
repo=Path('/Users/eammon/Documents/GitHub/Fusion-3D-printable-threads');sys.path.insert(0,str(repo))
from PrintableThreads.geometry import backend as b
from PrintableThreads.model.spec import Spec
from PrintableThreads.fusion_backend import selection,native
for m in (b,selection,native):importlib.reload(m)
app=core.Application.get();original=app.activeDocument;report={'cases':[]}
try:
 for kind in ('shared-compatible','shared-incompatible','gap','gap-joined','partial-length'):
  doc=app.documents.add(core.DocumentTypes.FusionDesignDocumentType)
  try:
   d=fusion.Design.cast(app.activeProduct);d.designIntent=fusion.DesignIntentTypes.HybridDesignIntentType
   selected=[];targets=[];first=None
   for i in range(2):
    transform=b.M();transform.translation=b.V(0,0,i*(.4 if kind.startswith('shared') and kind!='shared-incompatible' else .365 if kind=='shared-incompatible' else .5))
    if i and kind.startswith('shared'):occ=d.rootComponent.occurrences.addExistingComponent(first.component,transform)
    else:
     occ=d.rootComponent.occurrences.addNewComponent(transform)
     b.persist(occ.component,[b.cylinder(2,0,4 if kind.startswith('shared') else 3.65)],'Disposable target')
    if not i:first=occ
    target=occ.component.bRepBodies.item(0);targets.append(target)
    face=next(f for f in target.faces if core.Cylinder.cast(f.geometry))
    selected.append(face.createForAssemblyContext(occ))
   _,_,diameter,length,inside=selection.cylinder_frame(selected)
   spec=replace(Spec().with_circular_section(2),root_diameter=diameter,length=3 if kind=='partial-length' else length,pitch=4,radial_clearance=0,axial_clearance=0,knob='None',entry=0,output='Screw',cut_screw=kind!='gap-joined').validate()
   before=[t.volume for t in targets];count=d.timeline.count
   if kind=='shared-incompatible':
    try:native.apply(d,selected,spec)
    except ValueError as error:assert 'Paste New' in str(error)
    else:raise AssertionError('incompatible shared definitions were edited')
    assert d.timeline.count==count and [t.volume for t in targets]==before
   else:
    result=native.apply(d,selected,spec)
    assert len(result)==(1 if kind in ('shared-compatible','partial-length') else 2)
    assert targets[0].volume>before[0] if kind=='gap-joined' else targets[0].volume<before[0]
    if kind=='partial-length':assert targets[1].volume==before[1]
   report['cases'].append({'kind':kind,'passed':True})
  finally:doc.close(False)
 report['passed']=True
except Exception:report['error']=traceback.format_exc()
finally:
 if original and original.isValid:original.activate()
 (repo/'docs/multi-body-edge-probe.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
