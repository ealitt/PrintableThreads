"""Physical chamfer, +Y print placement, fit and parametric regression in Fusion."""
import sys,importlib,json,traceback,math
from pathlib import Path
from dataclasses import replace
import adsk.core as core,adsk.fusion as fusion
repo=Path('/Users/eammon/Documents/GitHub/PrintableThreads');sys.path.insert(0,str(repo))
from PrintableThreads.fusion_backend import native
from PrintableThreads.model.spec import Spec
from PrintableThreads import commands
importlib.reload(native);importlib.reload(commands)
app=core.Application.get();report=[]
class Value:
 def __init__(self,value):self.value=value
class Session:
 mode='create';values={k:Value(0) for k in ('x','y','z')}
def placement(offset=0):return commands.Session.placement(Session(),offset)
def health(d):
 for group in d.timeline.timelineGroups:group.isCollapsed=False
 return [(d.timeline.item(i).entity.name,d.timeline.item(i).entity.errorOrWarningMessage) for i in range(d.timeline.count) if getattr(d.timeline.item(i).entity,'errorOrWarningMessage','')]
base=replace(Spec().with_circular_section(2),cut_screw=True,knob='None',entry=0,length=12,engagement=12,output='Matched pair',print_on_plate=True)
cases=[('standard',base),('user_size',replace(base.with_circular_section(4),root_diameter=15,pitch=5,length=25.4,engagement=9)),('small',replace(base.with_circular_section(.8),pitch=1.2,radial_clearance=.05,starts=4)),('swapped',replace(base,cut_screw=False)),('left_multi',replace(base,left_hand=True,starts=2,phase=37)),('knob_cap',replace(base,knob='Lobed',blind=True,entry=.6))]
for name,s in cases:
 doc=app.documents.add(core.DocumentTypes.FusionDesignDocumentType);d=fusion.Design.cast(app.activeProduct);d.designIntent=fusion.DesignIntentTypes.HybridDesignIntentType
 result={'name':name}
 try:
  made=native.create(d,s,placement)
  assert not health(d),str(health(d))
  result['parts']=[]
  for o in made:
   body=o.component.bRepBodies.item(0);assert body.isSolid and body.lumps.count==1
   chamfers=list(o.component.features.chamferFeatures);assert len(chamfers)==1,'missing physical chamfer'
   assert chamfers[0].faces.count>0,'empty chamfer'
   z=core.Vector3D.create(0,0,1);z.transformBy(o.transform2);assert abs(z.y-1)<1e-6,'not +Y'
   bounds=body.createForAssemblyContext(o).boundingBox;assert abs(bounds.minPoint.y)<1e-6,'base not on ZX'
   result['parts'].append({'name':o.component.name,'chamfer_faces':chamfers[0].faces.count,'distance_mm':chamfers[0].edgeSets.item(0).distance.value*10,'volume':body.volume,'min_y':bounds.minPoint.y})
  if name in ('standard','swapped','left_multi'):
   manager=fusion.TemporaryBRepManager.get();a=manager.copy(made[0].component.bRepBodies.item(0));b=manager.copy(made[1].component.bRepBodies.item(0))
   intersects=manager.booleanOperation(a,b,fusion.BooleanTypes.IntersectionBooleanType)
   result['intersection_regions']=a.lumps.count if intersects else 0
   result['intersection_volume_cm3']=a.volume if intersects and a.lumps.count else 0
   assert result['intersection_volume_cm3']<1e-8,'mating parts interfere'
  for key,value in [('pitch',f'{s.pitch+1} mm'),('section',f'{s.thread_size*.9} mm'),('tolerance',f'{s.radial_clearance*1.1} mm'),('starts','2'),('starts','1')]:
   d.userParameters.itemByName('PT1_'+key).expression=value;d.computeAll();assert not health(d),key+str(health(d))
  result['passed']=True
 except Exception:result['error']=traceback.format_exc()
 finally:report.append(result);doc.close(False);(repo/'docs/print-finish-probe.json').write_text(json.dumps(report,indent=2))
# Apply in root and translated / rotated occurrence, before a downstream sketch.
for internal,nested,reverse in [(False,False,False),(True,False,False),(False,True,False),(True,True,False),(True,True,True)]:
 doc=app.documents.add(core.DocumentTypes.FusionDesignDocumentType);d=fusion.Design.cast(app.activeProduct);d.designIntent=fusion.DesignIntentTypes.HybridDesignIntentType
 result={'name':'apply','internal':internal,'nested':nested,'reverse':reverse}
 try:
  c=d.rootComponent;occ=None
  if nested:
   matrix=core.Matrix3D.create();matrix.setToRotation(.8,core.Vector3D.create(0,1,0),core.Point3D.create(0,0,0));matrix.translation=core.Vector3D.create(4,3,2)
   occ=c.occurrences.addNewComponent(matrix);c=occ.component
  sk=c.sketches.add(c.xYConstructionPlane)
  for radius in ((.6,1.1) if internal else (.6,)):sk.sketchCurves.sketchCircles.addByCenterRadius(core.Point3D.create(0,0,0),radius)
  profile=next(p for p in sk.profiles if p.profileLoops.count==2) if internal else sk.profiles.item(0)
  inp=c.features.extrudeFeatures.createInput(profile,native.OP.NewBodyFeatureOperation);inp.setDistanceExtent(False,core.ValueInput.createByReal(1.2))
  target=c.features.extrudeFeatures.add(inp).bodies.item(0)
  face=next(f for f in target.faces if core.Cylinder.cast(f.geometry) and abs(core.Cylinder.cast(f.geometry).radius-.6)<1e-6)
  if occ:face=face.createForAssemblyContext(occ)
  marker=d.timeline.markerPosition;c.sketches.add(c.xYConstructionPlane);d.timeline.markerPosition=marker
  body=native.apply(d,face,replace(base,starts=2,output='Screw'),reverse)
  assert c.features.chamferFeatures.count==1,'missing Apply chamfer'
  assert c.features.chamferFeatures.item(0).faces.count>0,'empty Apply chamfer'
  assert body.isSolid and body.lumps.count==1
  d.timeline.moveToEnd();assert not health(d),str(health(d))
  assert d.timeline.timelineGroups.count==1
  for value in ('1','3','2'):
   d.userParameters.itemByName('PT1_starts').expression=value;d.computeAll();assert not health(d),str(health(d))
  result.update(passed=True,chamfer_faces=c.features.chamferFeatures.item(0).faces.count)
 except Exception:result['error']=traceback.format_exc()
 finally:report.append(result);doc.close(False);(repo/'docs/print-finish-probe.json').write_text(json.dumps(report,indent=2))
(repo/'docs/print-finish-probe.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
