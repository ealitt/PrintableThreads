"""Cross-body / occurrence phase and precision regressions in disposable files."""
import sys,importlib,json,traceback
from pathlib import Path
from dataclasses import replace
import adsk.core as core,adsk.fusion as fusion
repo=Path('/Users/eammon/Documents/GitHub/Fusion-3D-printable-threads');sys.path.insert(0,str(repo))
from PrintableThreads.model import spec as sm
from PrintableThreads.geometry import backend as b
from PrintableThreads.fusion_backend import selection,native,preview
for m in (sm,b,selection,native,preview):importlib.reload(m)
app=core.Application.get();original=app.activeDocument;report={'cases':[]}
try:
 for placement in ('bodies','occurrences','rotated','nested'):
  for internal,cut in ((False,True),(False,False),(True,True),(True,False)):
   for reverse in (False,True):
    doc=app.documents.add(core.DocumentTypes.FusionDesignDocumentType)
    try:
     d=fusion.Design.cast(app.activeProduct);d.designIntent=fusion.DesignIntentTypes.HybridDesignIntentType
     root=d.rootComponent;selected=[];targets=[]
     world=b.M()
     if placement in ('rotated','nested'):
      world.setToRotation(.7,b.V(1,1,0),b.P(0,0,0));world.translation=b.V(1,2,3)
     parent=root.occurrences.addNewComponent(world) if placement=='nested' else None
     for i in range(2):
      body=b.cylinder(6 if internal else 2,0,3.649991775936984)
      if internal:b.cut(body,b.cylinder(2,0,3.649991775936984))
      if placement=='bodies':
       b.move(body,z=i*3.649991775936984);c=root;occ=None
      else:
       matrix=b.M();matrix.translation=b.V(0,0,i*.3649991775936984)
       if placement=='nested':
        child=parent.component.occurrences.addNewComponent(matrix);c=child.component;occ=child.createForAssemblyContext(parent)
       else:
        matrix.transformBy(world);occ=root.occurrences.addNewComponent(matrix);c=occ.component
      b.persist(c,[body],'Separate test target')
      target=c.bRepBodies.item(c.bRepBodies.count-1);targets.append(target)
      f=next(f for f in target.faces if core.Cylinder.cast(f.geometry) and abs(core.Cylinder.cast(f.geometry).radius-.2)<1e-6)
      selected.append(f.createForAssemblyContext(occ) if occ else f)
     _,frame,diameter,length,inside=selection.cylinder_frame(selected,reverse)
     assert abs(length-7.299983551873968)<1e-6 and inside==internal
     spec=replace(sm.Spec().with_circular_section(2),root_diameter=diameter,pitch=4,length=length,radial_clearance=.3,axial_clearance=0,knob='None',entry=0,output='Screw',cut_screw=cut).validate()
     previews=[]
     global_frame=frame.copy()
     if selected[0].assemblyContext:global_frame.transformBy(selected[0].assemblyContext.transform2)
     for group,shared in selection.shared_frames(selected,reverse):
      mapped=shared[0].copy()
      if group[0].assemblyContext:mapped.transformBy(group[0].assemblyContext.transform2)
      assert all(abs(mapped.getCell(row,col)-global_frame.getCell(row,col))<1e-7 for row in range(4) for col in range(4)), 'thread phase reset between components' 
     for group,shared in selection.shared_frames(selected,reverse):
      previews.append(selection.preview_body(d,group,spec,reverse,shared))
     before=[t.volume for t in targets]
     results=native.apply(d,selected,spec,reverse)
     after=[t.volume for t in targets]
     assert len(results)==2 and all(t.isSolid for t in targets)
     assert all(abs(a-p.volume)/a<.07 for a,p in zip(after,previews))
     # Both segments must be changed; their asymmetry exercises the common phase.
     assert all(abs(a-v)>1e-5 for a,v in zip(after,before))
     report['cases'].append({'placement':placement,'internal':internal,'cut':cut,'reverse':reverse,'diameter':diameter,'length':length,'before':before,'after':after})
    finally:
     (repo/'docs/multi-body-probe.json').write_text(json.dumps(report,indent=2))
     doc.close(False)
 report['passed']=True
except Exception:report['error']=traceback.format_exc()
finally:
 if original and original.isValid:original.activate()
 (repo/'docs/multi-body-probe.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
