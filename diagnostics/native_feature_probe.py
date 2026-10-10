import sys,importlib,json,traceback,time
from pathlib import Path
import adsk.core as core,adsk.fusion as fusion
repo=Path('/Users/eammon/Documents/GitHub/PrintableThreads');sys.path.insert(0,str(repo))
from PrintableThreads.fusion_backend import native
from PrintableThreads.model.spec import Spec
from dataclasses import replace
importlib.reload(native)
app=core.Application.get();doc=app.documents.add(core.DocumentTypes.FusionDesignDocumentType)
d=fusion.Design.cast(app.activeProduct);d.designIntent=fusion.DesignIntentTypes.HybridDesignIntentType
report={'cases':[]}
def placement(offset=0):
 m=core.Matrix3D.create();m.translation=core.Vector3D.create(offset/10,0,0);return m
try:
 s=replace(Spec().with_circular_section(2),cut_screw=True,knob='None',entry=0,output='Matched pair')
 t=time.perf_counter();made=native.create(d,s,placement)
 for group in d.timeline.timelineGroups:group.isCollapsed=False
 report['cases'].append({'name':'create','seconds':time.perf_counter()-t,'volumes':[o.component.bRepBodies.item(0).volume for o in made],'features':[(d.timeline.item(i).entity.objectType if d.timeline.item(i).entity else 'Timeline group') for i in range(d.timeline.count)],'groups':d.timeline.timelineGroups.count})
 p=d.userParameters.itemByName('PT1_pitch');p.expression='4 mm';d.computeAll()
 report['edit_health']=[{'name':getattr(d.timeline.item(i).entity,'name','group'),'message':getattr(d.timeline.item(i).entity,'errorOrWarningMessage','')} for i in range(d.timeline.count) if getattr(d.timeline.item(i).entity,'errorOrWarningMessage','')]
 report['passed']=not report['edit_health']
except Exception:report['error']=traceback.format_exc()
finally:
 (repo/'docs/native-feature-probe.json').write_text(json.dumps(report,indent=2));doc.close(False)
print(report)
