import sys,importlib,json,traceback
from pathlib import Path
import adsk.core as core,adsk.fusion as fusion
from dataclasses import replace
repo=Path('/Users/eammon/Documents/GitHub/PrintableThreads');sys.path.insert(0,str(repo))
from PrintableThreads.fusion_backend import native
from PrintableThreads.model.spec import Spec
importlib.reload(native)
app=core.Application.get();doc=app.documents.add(core.DocumentTypes.FusionDesignDocumentType);d=fusion.Design.cast(app.activeProduct)
report={}
original_point=native.Builder.point
def debug_point(self,sk,point,x,y):
 if sk.name=='Thread section':
  report.setdefault('points',[]).append({'geometry':point.geometry.asArray(),'x':x,'y':y,'constraints':[item.objectType for item in sk.geometricConstraints],'dimensions':[(item.parameter.name,item.parameter.expression) for item in sk.sketchDimensions]})
 try:return original_point(self,sk,point,x,y)
 except Exception:
  report['failed_dimensions']=[(item.parameter.name,item.parameter.expression) for item in sk.sketchDimensions]
  raise
native.Builder.point=debug_point
try:
 s=replace(Spec(),cut_screw=True,knob='None',entry=0,length=12,output='Matched pair',radial_clearance=.2)
 made=native.create(d,s,lambda offset=0:core.Matrix3D.create())
 for group in d.timeline.timelineGroups:group.isCollapsed=False
 report['features']=[(d.timeline.item(i).entity.name,d.timeline.item(i).entity.objectType) for i in range(d.timeline.count) if d.timeline.item(i).entity]
 report['health']=[(d.timeline.item(i).entity.name,getattr(d.timeline.item(i).entity,'errorOrWarningMessage','')) for i in range(d.timeline.count) if d.timeline.item(i).entity and getattr(d.timeline.item(i).entity,'errorOrWarningMessage','')]
 d.userParameters.itemByName('PT1_pitch').expression='4 mm';d.computeAll()
 report['edit_health']=[(d.timeline.item(i).entity.name,getattr(d.timeline.item(i).entity,'errorOrWarningMessage','')) for i in range(d.timeline.count) if d.timeline.item(i).entity and getattr(d.timeline.item(i).entity,'errorOrWarningMessage','')]
 report['passed']=not report['health'] and not report['edit_health']
except Exception:report['error']=traceback.format_exc()
finally:doc.close(False)
(repo/'docs/native-profile-probe.json').write_text(json.dumps(report,indent=2));print(report)
