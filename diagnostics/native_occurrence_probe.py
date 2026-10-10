import sys,importlib,json,traceback,math
from pathlib import Path
from dataclasses import replace
import adsk.core as core,adsk.fusion as fusion
repo=Path('/Users/eammon/Documents/GitHub/PrintableThreads');sys.path.insert(0,str(repo))
from PrintableThreads.fusion_backend import native
from PrintableThreads.model.spec import Spec
importlib.reload(native)
app=core.Application.get();report=[]
for internal,reverse in [(False,False),(True,False),(True,True)]:
 doc=app.documents.add(core.DocumentTypes.FusionDesignDocumentType);d=fusion.Design.cast(app.activeProduct);d.designIntent=fusion.DesignIntentTypes.HybridDesignIntentType
 result={'internal':internal,'reverse':reverse}
 try:
  matrix=core.Matrix3D.create();matrix.setToRotation(.8,core.Vector3D.create(0,1,0),core.Point3D.create(0,0,0));matrix.translation=core.Vector3D.create(4,3,2)
  occ=d.rootComponent.occurrences.addNewComponent(matrix);c=occ.component
  sk=c.sketches.add(c.xYConstructionPlane)
  for r in ((.6,1.1) if internal else (.6,)):sk.sketchCurves.sketchCircles.addByCenterRadius(core.Point3D.create(0,0,0),r)
  profile=next(p for p in sk.profiles if p.profileLoops.count==2) if internal else sk.profiles.item(0)
  inp=c.features.extrudeFeatures.createInput(profile,native.OP.NewBodyFeatureOperation);inp.setDistanceExtent(False,core.ValueInput.createByReal(1.2))
  target=c.features.extrudeFeatures.add(inp).bodies.item(0)
  face=next(f for f in target.faces if core.Cylinder.cast(f.geometry) and abs(core.Cylinder.cast(f.geometry).radius-.6)<1e-6).createForAssemblyContext(occ)
  s=replace(Spec().with_circular_section(2),cut_screw=True,knob='None',entry=0,length=12,engagement=12,starts=2,output='Screw')
  body=native.apply(d,face,s,reverse)
  body=c.bRepBodies.item(0)
  assert body.isSolid and body.lumps.count==1
  if not internal:
   from PrintableThreads.geometry import backend
   expected=backend.threaded(d.rootComponent,s,entry=False)
   result['expected_volume']=expected.volume
   assert abs(body.volume-expected.volume)/expected.volume<.005, f'{body.volume} vs {expected.volume}'
  for group in d.timeline.timelineGroups:group.isCollapsed=False
  def health():return [(d.timeline.item(i).entity.name,getattr(d.timeline.item(i).entity,'errorOrWarningMessage','')) for i in range(d.timeline.count) if d.timeline.item(i).entity and getattr(d.timeline.item(i).entity,'errorOrWarningMessage','')]
  assert not health(),str(health())
  result['volume']=body.volume
  for starts in (1,3,2):
   d.userParameters.itemByName('PT1_starts').expression=str(starts);d.computeAll();assert not health(),str(health())
  result['passed']=True
 except Exception:result['error']=traceback.format_exc();result['pattern_info']=getattr(native,'_pattern_info',None);result['apply_info']=getattr(native,'_apply_info',None)
 finally:report.append(result);doc.close(False)
(repo/'docs/native-occurrence-probe.json').write_text(json.dumps(report,indent=2));print(report)
