import sys,importlib,json,traceback
from pathlib import Path
import adsk.core as core,adsk.fusion as fusion
repo=Path('/Users/eammon/Documents/GitHub/PrintableThreads');sys.path.insert(0,str(repo))
from PrintableThreads.fusion_backend import native
from PrintableThreads.model.spec import Spec
from dataclasses import replace
importlib.reload(native)
app=core.Application.get();report=[]
for sign in (-1,1):
 doc=app.documents.add(core.DocumentTypes.FusionDesignDocumentType);d=fusion.Design.cast(app.activeProduct);d.designIntent=fusion.DesignIntentTypes.HybridDesignIntentType
 try:
  s=replace(Spec().with_circular_section(2),cut_screw=True,knob='None',entry=0,output='Female')
  builder=native.Builder(d,s);occ,c=builder.component('Probe');ribs=builder.rib(c,builder.p['length'],True,offset=sign)
  report.append({'sign':sign,'volume':ribs[0].volume,'passed':True})
 except Exception:report.append({'sign':sign,'error':traceback.format_exc()})
 finally:doc.close(False)
(repo/'docs/native-offset-probe.json').write_text(json.dumps(report,indent=2));print(report)
