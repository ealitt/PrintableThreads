import sys,importlib,json,traceback
from pathlib import Path
from dataclasses import replace
import adsk.core as core,adsk.fusion as fusion
repo=Path('/Users/eammon/Documents/GitHub/PrintableThreads');sys.path.insert(0,str(repo))
from PrintableThreads.fusion_backend import native
from PrintableThreads.model.spec import Spec
importlib.reload(native)
app=core.Application.get();report=[]
for label,mode in [('sharp',fusion.ShellTypes.SharpOffsetShellType),('rounded',fusion.ShellTypes.RoundedOffsetShellType)]:
 doc=app.documents.add(core.DocumentTypes.FusionDesignDocumentType);d=fusion.Design.cast(app.activeProduct)
 s=replace(Spec(),cut_screw=True,knob='None',entry=0,length=6,engagement=6,radial_clearance=.2,output='Screw')
 result={'type':label}
 try:
  b=native.Builder(d,s);occ,c=b.component('Probe');body=b.rib(c,b.p['length'],True)[0]
  before={item.entityToken for item in c.bRepBodies}
  inp=c.features.offsetFeatures.createInput(native.collection([f.createForAssemblyContext(occ) for f in body.faces]),native.VI('0 mm'),native.OP.NewBodyFeatureOperation,False)
  f=c.features.offsetFeatures.add(inp)
  result["offset_bodies"]=[(x.name,x.isSolid,x.parentComponent.name,x.faces.count) for x in f.bodies]
  copied=next(item for item in f.bodies if item.entityToken not in before)
  root=d.rootComponent
  stitch=root.features.stitchFeatures.add(root.features.stitchFeatures.createInput(native.collection([copied]),native.VI("0.001 mm"),native.OP.NewBodyFeatureOperation))
  result["stitch"]=[(x.name,x.isSolid,x.parentComponent.name,x.faces.count) for x in stitch.bodies]
  copied=next(x for x in stitch.bodies if x.isSolid)
  result['copy_solid']=copied.isSolid
  inp=root.features.shellFeatures.createInput(native.collection([copied]),False)
  inp.insideThickness=native.VI(b.p['tolerance']);inp.shellType=mode
  f=root.features.shellFeatures.add(inp);shell=f.bodies.item(0)
  result['shell']=shell.volume
  body=b.combine(c,body,[shell],native.OP.CutFeatureOperation,'Erode nominal rib')
  result['result']=body.volume
  d.userParameters.itemByName(b.p['pitch']).expression='4 mm';d.computeAll()
  result['health']=[(f.name,f.errorOrWarningMessage) for f in c.features if f.errorOrWarningMessage]
  result['passed']=not result['health']
 except Exception:result['error']=traceback.format_exc()
 finally:report.append(result);doc.close(False)
(repo/'docs/native-shell-probe.json').write_text(json.dumps(report,indent=2));print(report)
