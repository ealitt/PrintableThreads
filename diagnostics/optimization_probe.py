"""Compare native optimized solids and recomputation with installed 0.5.1 construction."""
import sys,importlib,json,traceback,time,types
from pathlib import Path
from dataclasses import replace
import adsk.core as core,adsk.fusion as fusion
repo=Path('/Users/eammon/Documents/GitHub/PrintableThreads');sys.path.insert(0,str(repo))
from PrintableThreads.fusion_backend import native
from PrintableThreads.model.spec import Spec
importlib.reload(native)
old=types.ModuleType('PrintableThreads.fusion_backend.baseline');old.__package__='PrintableThreads.fusion_backend';old.__file__=native.__file__
exec(compile((repo/'diagnostics/native_baseline_0_5_1.py').read_text(),old.__file__,'exec'),old.__dict__)
app=core.Application.get();manager=fusion.TemporaryBRepManager.get();report=[]
base=replace(Spec().with_circular_section(2),cut_screw=True,print_on_plate=True,output='Matched pair')
def placement(offset=0):
 m=core.Matrix3D.create();m.translation=core.Vector3D.create(offset/10,0,0);return m
def health(d):
 for g in d.timeline.timelineGroups:g.isCollapsed=False
 return [(e.name,e.errorOrWarningMessage) for i in range(d.timeline.count) if (e:=d.timeline.item(i).entity) and getattr(e,'errorOrWarningMessage','')]
for name,s in [('default',base),('blind',replace(base,blind=True)),('cylinder',replace(base,knob='Cylinder')),('lobes12',replace(base,lobes=12)),('left_swap',replace(base,left_hand=True,cut_screw=False,starts=3,phase=37)),('bare',replace(base,knob='None',entry=0))]:
 result={'name':name};documents=[];copies=[]
 try:
  for label,backend in [('old',old),('new',native)]:
   doc=app.documents.add(core.DocumentTypes.FusionDesignDocumentType);documents.append(doc);d=fusion.Design.cast(app.activeProduct);d.designIntent=fusion.DesignIntentTypes.HybridDesignIntentType
   t=time.perf_counter();made=backend.create(d,s,placement);result[label+'_seconds']=time.perf_counter()-t
   assert not health(d),str(health(d))
   result[label+'_steps']=d.timeline.count;result[label+'_knob_steps']=sum('Knob' in (e.name or '') or 'knob' in (e.name or '') for i in range(d.timeline.count) if (e:=d.timeline.item(i).entity))
   copies.append([manager.copy(o.component.bRepBodies.item(0)) for o in made])
  differences=[]
  for a,b in zip(*copies):
   for left,right in ((a,b),(b,a)):
    diff=manager.copy(left);assert manager.booleanOperation(diff,right,fusion.BooleanTypes.DifferenceBooleanType)
    volume=diff.volume if diff.lumps.count else 0;differences.append(volume);assert volume<1e-7,str(volume)
  result['difference_volumes_cm3']=differences
  for key,val in [('knob_diameter','32 mm'),('knob_height','8 mm'),('length','20 mm'),('engagement','14 mm'),('entry','1.2 mm'),('floor','3 mm'),('pitch','4 mm'),('starts','2'),('starts','1'),('section','1.8 mm'),('tolerance','0.25 mm')]:
   d.userParameters.itemByName('PT1_'+key).expression=val;t=time.perf_counter();d.computeAll();assert not health(d),key+str(health(d))
   result.setdefault('edit_seconds',{})[key]=time.perf_counter()-t
  assert all(o.component.bRepBodies.count==1 and o.component.bRepBodies.item(0).lumps.count==1 for o in made)
  # Compare the edited solids too, including the compact drafted entry.
  new_bodies=[manager.copy(o.component.bRepBodies.item(0)) for o in made]
  documents[0].activate();oldd=fusion.Design.cast(app.activeProduct)
  for key,val in [('knob_diameter','32 mm'),('knob_height','8 mm'),('length','20 mm'),('engagement','14 mm'),('entry','1.2 mm'),('floor','3 mm'),('pitch','4 mm'),('starts','1'),('section','1.8 mm'),('tolerance','0.25 mm')]:oldd.userParameters.itemByName('PT1_'+key).expression=val
  t=time.perf_counter();oldd.computeAll();result['old_full_recompute_seconds']=time.perf_counter()-t;assert not health(oldd),str(health(oldd))
  old_bodies=[manager.copy(o.component.bRepBodies.item(0)) for o in oldd.rootComponent.occurrences]
  edited=[]
  for a,b in zip(old_bodies,new_bodies):
   for left,right in ((a,b),(b,a)):
    diff=manager.copy(left);assert manager.booleanOperation(diff,right,fusion.BooleanTypes.DifferenceBooleanType)
    volume=diff.volume if diff.lumps.count else 0;edited.append(volume);assert volume<1e-7,str(volume)
  result['edited_difference_volumes_cm3']=edited
  result['passed']=True
 except Exception:result['error']=traceback.format_exc()
 finally:
  for doc in reversed(documents):doc.close(False)
  report.append(result);(repo/'docs/optimization-probe.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
