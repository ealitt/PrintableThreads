import sys,importlib,json,traceback
from pathlib import Path
from dataclasses import replace
import adsk.core as core,adsk.fusion as fusion
repo=Path('/Users/eammon/Documents/GitHub/PrintableThreads');sys.path.insert(0,str(repo))
from PrintableThreads.fusion_backend import native
from PrintableThreads.model.spec import Spec
importlib.reload(native)
app=core.Application.get();doc=app.documents.add(core.DocumentTypes.FusionDesignDocumentType);d=fusion.Design.cast(app.activeProduct);report={}
try:
 s=replace(Spec().with_circular_section(2),starts=2,phase=37,knob='None',entry=0,cut_screw=True)
 made=native.create(d,s,lambda offset=0:core.Matrix3D.create())
 for group in d.timeline.timelineGroups:group.isCollapsed=False
 d.userParameters.itemByName('PT1_phase').expression='0 deg'
 d.userParameters.itemByName('PT1_starts').expression='1';d.computeAll()
 report['health']=[(d.timeline.item(i).entity.name,d.timeline.item(i).entity.errorOrWarningMessage) for i in range(d.timeline.count) if d.timeline.item(i).entity and getattr(d.timeline.item(i).entity,'errorOrWarningMessage','')]
 report['passed']=not report['health']
except Exception:report['error']=traceback.format_exc()
finally:doc.close(False)
(repo/'docs/native-structure-probe.json').write_text(json.dumps(report,indent=2));print(report)
