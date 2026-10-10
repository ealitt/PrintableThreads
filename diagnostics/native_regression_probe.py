"""Fusion native features, actual clearances, edits, and timeline insertion."""
import sys,importlib,json,traceback,time,math
from pathlib import Path
import adsk.core as core,adsk.fusion as fusion
repo=Path('/Users/eammon/Documents/GitHub/PrintableThreads');sys.path.insert(0,str(repo))
from PrintableThreads.fusion_backend import native
from PrintableThreads.geometry import backend as exact
from PrintableThreads.model.spec import Spec
from dataclasses import replace
importlib.reload(native)
app=core.Application.get();report={'cases':[]}
inside=fusion.PointContainment.PointInsidePointContainment
P=core.Point3D.create

def placement(offset=0):
 m=core.Matrix3D.create();m.translation=core.Vector3D.create(offset/10,0,0);return m

def entities(d):
 for group in d.timeline.timelineGroups:group.isCollapsed=False
 return [d.timeline.item(i).entity for i in range(d.timeline.count) if d.timeline.item(i).entity]

def health(d):
 return [(e.name,e.errorOrWarningMessage) for e in entities(d) if getattr(e,'errorOrWarningMessage','')]

def solids(c):return [body for body in c.bRepBodies if body.isSolid]

def clearance(body,s,length,frame=None):
 def contains(point):
  if frame:point.transformBy(frame)
  return body.pointContainment(point)==inside
 checks=0
 # Known straight wall region and inward rib crown.
 for radius,expected in ((s.root_diameter/2+.19,False),(s.root_diameter/2+.21,True)):
  z=length*.5;theta=2*math.pi*z/s.lead+math.pi/s.starts
  assert contains(P(radius*math.cos(theta)/10,radius*math.sin(theta)/10,z/10))==expected,'straight wall gap'
  checks+=1
 # Normal offsets on the swept circle include an angular component from lead.
 theta=1.2;z=s.lead*theta/(2*math.pi)+s.lead
 for phi in (math.pi,math.pi-.7,math.pi+.7):
  r=s.root_diameter/2+s.height*math.cos(phi)
  nr=math.cos(phi);nt=-s.lead/(2*math.pi*r)*math.sin(phi);nz=math.sin(phi)
  norm=math.sqrt(nr*nr+nt*nt+nz*nz);nr/=norm;nt/=norm;nz/=norm
  x=r*math.cos(theta);y=r*math.sin(theta);zz=z+s.height*math.sin(phi)
  nx=nr*math.cos(theta)-nt*math.sin(theta);ny=nr*math.sin(theta)+nt*math.cos(theta)
  for gap,expected in ((s.radial_clearance-.015,False),(s.radial_clearance+.015,True)):
   assert contains(P((x-gap*nx)/10,(y-gap*ny)/10,(zz-gap*nz)/10))==expected,'curved normal gap'
   checks+=1
 return checks

base=replace(Spec().with_circular_section(2),cut_screw=True,knob='None',entry=0,length=12,engagement=12,output='Matched pair')
for name,s in [('circular',base),('left_multi',replace(base,left_hand=True,starts=2,phase=37)),('swapped',replace(base,cut_screw=False)),('knob_cap',replace(base,knob='Lobed',blind=True,print_on_plate=True,entry=.6)),('trapezoid',replace(Spec(),cut_screw=True,knob='None',entry=0,length=12,engagement=12))]:
 doc=app.documents.add(core.DocumentTypes.FusionDesignDocumentType);d=fusion.Design.cast(app.activeProduct);d.designIntent=fusion.DesignIntentTypes.HybridDesignIntentType
 result={'name':name};t=time.perf_counter()
 try:
  made=native.create(d,s,placement)
  es=entities(d);assert not any(fusion.BaseFeature.cast(e) for e in es),'baked geometry'
  assert not health(d),str(health(d))
  assert all(len(solids(o.component))==1 for o in made),'not one solid per part'
  if name=='circular':
   result['clearance_checks']=clearance(solids(made[1].component)[0],s,12)
   old=exact.threaded(d.rootComponent,s,entry=False);new=solids(made[0].component)[0]
   result['nominal_volume_difference']=abs(old.volume-new.volume);assert result['nominal_volume_difference']/old.volume<.002
  for key,value in [('pitch','4 mm'),('section','1.8 mm'),('length','14 mm'),('engagement','14 mm'),('tolerance','0.25 mm')]:
   d.userParameters.itemByName('PT1_'+key).expression=value;d.computeAll();assert not health(d),key+': '+str(health(d))
  result.update(passed=True,features=len(es),groups=d.timeline.timelineGroups.count,seconds=time.perf_counter()-t)
 except Exception:result['error']=traceback.format_exc()
 finally:
  report['cases'].append(result);doc.close(False);(repo/'docs/native-regression-probe.json').write_text(json.dumps(report,indent=2))
# Apply to regular native extruded cylinders; insert before a downstream feature.
for internal in (False,True):
 doc=app.documents.add(core.DocumentTypes.FusionDesignDocumentType);d=fusion.Design.cast(app.activeProduct);d.designIntent=fusion.DesignIntentTypes.HybridDesignIntentType
 result={'name':'apply_nut' if internal else 'apply_screw'}
 try:
  c=d.rootComponent;sk=c.sketches.add(c.xYConstructionPlane);sk.sketchCurves.sketchCircles.addByCenterRadius(P(0,0,0),.6)
  if internal:sk.sketchCurves.sketchCircles.addByCenterRadius(P(0,0,0),1.1)
  profile=next(p for p in sk.profiles if p.profileLoops.count==2) if internal else sk.profiles.item(0)
  inp=c.features.extrudeFeatures.createInput(profile,fusion.FeatureOperations.NewBodyFeatureOperation);inp.setDistanceExtent(False,core.ValueInput.createByReal(1.2))
  target=c.features.extrudeFeatures.add(inp).bodies.item(0)
  faces=[f for f in target.faces if core.Cylinder.cast(f.geometry) and abs(core.Cylinder.cast(f.geometry).radius-.6)<1e-6]
  frame=native.cylinder_frame(faces[0])[1]
  marker=d.timeline.markerPosition
  extra=c.sketches.add(c.xYConstructionPlane);extra.name='Downstream sketch'
  d.timeline.markerPosition=marker
  body=native.apply(d,faces[0],replace(base,output='Screw'))
  d.timeline.moveToEnd();assert not health(d),str(health(d))
  if internal:result['clearance_checks']=clearance(body,base,12,frame)
  assert d.timeline.timelineGroups.count==1
  assert not any(fusion.BaseFeature.cast(e) for e in entities(d))
  d.userParameters.itemByName('PT1_pitch').expression='4 mm';d.computeAll();assert not health(d),str(health(d))
  result['passed']=True
 except Exception:result['error']=traceback.format_exc()
 finally:
  report['cases'].append(result);doc.close(False);(repo/'docs/native-regression-probe.json').write_text(json.dumps(report,indent=2))
report['passed']=all(case.get('passed') for case in report['cases']);(repo/'docs/native-regression-probe.json').write_text(json.dumps(report,indent=2));print(report)
