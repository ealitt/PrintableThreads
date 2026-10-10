import sys,importlib,json,traceback,time
from pathlib import Path
from dataclasses import replace
import adsk.core as core,adsk.fusion as fusion
repo=Path('/Users/eammon/Documents/GitHub/PrintableThreads');sys.path.insert(0,str(repo))
from PrintableThreads.fusion_backend import native
from PrintableThreads.model.spec import Spec
importlib.reload(native)
app=core.Application.get();report=[]
for radius,cut in [(0,True),(.15,True),(.3,True),(0,False),(.15,False)]:
 doc=app.documents.add(core.DocumentTypes.FusionDesignDocumentType);d=fusion.Design.cast(app.activeProduct)
 result={'radius':radius,'cut_screw':cut};t=time.perf_counter()
 try:
  s=replace(Spec(),radius=radius,cut_screw=cut,knob='None',entry=0,length=6,engagement=6,output='Matched pair')
  made=native.create(d,s,lambda offset=0:core.Matrix3D.create())
  result['volumes']=[o.component.bRepBodies.item(0).volume for o in made]
  for group in d.timeline.timelineGroups:group.isCollapsed=False
  result['health']=[(d.timeline.item(i).entity.name,getattr(d.timeline.item(i).entity,'errorOrWarningMessage','')) for i in range(d.timeline.count) if d.timeline.item(i).entity and getattr(d.timeline.item(i).entity,'errorOrWarningMessage','')]
  result['passed']=not result['health']
 except Exception:result['error']=traceback.format_exc()
 finally:result['seconds']=time.perf_counter()-t;report.append(result);doc.close(False)
(repo/'docs/native-profile-cases.json').write_text(json.dumps(report,indent=2));print(report)
