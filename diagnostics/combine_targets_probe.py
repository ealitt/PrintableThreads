"""Verify Apply consumes thread tools into each intended solid, in disposable files."""
import sys,importlib,json,traceback
from pathlib import Path
from dataclasses import replace
import adsk.core as core,adsk.fusion as fusion
repo=Path('/Users/eammon/Documents/GitHub/Fusion-3D-printable-threads');sys.path.insert(0,str(repo))
from PrintableThreads.geometry import backend as b
from PrintableThreads.fusion_backend import native,selection
from PrintableThreads.model import solid
from PrintableThreads.model.spec import Spec
for m in (b,solid,selection,native):importlib.reload(m)
app=core.Application.get();original=app.activeDocument;report={'cases':[]}
try:
 for placement in ('bodies','occurrences'):
  for internal,cut in ((False,True),(False,False),(True,True),(True,False)):
   doc=app.documents.add(core.DocumentTypes.FusionDesignDocumentType)
   try:
    d=fusion.Design.cast(app.activeProduct);d.designIntent=fusion.DesignIntentTypes.HybridDesignIntentType
    root=d.rootComponent;selected=[];targets=[];components=[]
    for i in range(2):
     body=b.cylinder(6 if internal else 2,0,4)
     if internal:b.cut(body,b.cylinder(2,0,4))
     if placement=='bodies':b.move(body,z=4*i);c=root;occ=None
     else:
      t=b.M();t.setToRotation(.7,b.V(1,1,0),b.P(0,0,0));shift=b.V(0,0,.4*i);shift.transformBy(t);t.translation=shift
      occ=root.occurrences.addNewComponent(t);c=occ.component
     b.persist(c,[body],'Selected test body')
     target=c.bRepBodies.item(c.bRepBodies.count-1);targets.append(target);components.append(c)
     f=next(f for f in target.faces if core.Cylinder.cast(f.geometry) and abs(f.geometry.radius-.2)<1e-6)
     selected.append(f.createForAssemblyContext(occ) if occ else f)
    unrelated=b.cylinder(3,0,8,x=20);b.persist(root,[unrelated],'Unselected control')
    control=root.bRepBodies.item(root.bRepBodies.count-1);control_volume=control.volume
    before=[t.volume for t in targets]
    spec=replace(Spec().with_circular_section(2),root_diameter=4,pitch=4,length=8,radial_clearance=.2,axial_clearance=0,knob='None',entry=0,output='Screw',cut_screw=cut).validate()
    results=native.apply(d,selected,spec)
    joining=internal==cut
    assert len(results)==2
    for target,volume in zip(targets,before):
     assert target.isValid and target.isSolid and target.lumps.count==1
     assert (target.volume>volume+1e-6) if joining else (target.volume<volume-1e-6)
     assert target.attributes.itemByName('PrintableThreads.native','recipe')
    assert abs(control.volume-control_volume)<1e-10
    # All imported thread construction bodies must have been consumed by Combine.
    constructions=[c for c in d.allComponents if c.name.endswith('Apply thread construction')]
    assert len(constructions)==2 and all(c.bRepBodies.count==0 for c in constructions), [(c.name,c.bRepBodies.count) for c in d.allComponents]
    combines=[f for c in d.allComponents for f in c.features.combineFeatures if f.name.startswith('Apply printable thread')]
    assert len(combines)==2 and all(not f.isKeepToolBodies for f in combines), [(c.name,[(f.name,f.isKeepToolBodies) for f in c.features.combineFeatures]) for c in d.allComponents]
    assert sum(c.bRepBodies.count for c in d.allComponents)==3
    report['cases'].append({'placement':placement,'internal':internal,'cut':cut,'target_solids':2,'combine_features':len(combines),'remaining_thread_tools':0,'unselected_unchanged':True,'before':before,'after':[t.volume for t in targets]})
   finally:doc.close(False)
 report['passed']=True
except Exception:report['error']=traceback.format_exc()
finally:
 if original and original.isValid:original.activate()
 (repo/'docs/combine-targets-0.5.5.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
