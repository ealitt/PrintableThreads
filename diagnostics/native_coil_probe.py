"""Run in the disposable native Coil template document's Python console."""
import json,traceback
from pathlib import Path
import adsk.core as core,adsk.fusion as fusion
repo=Path('/Users/eammon/Documents/GitHub/PrintableThreads')
app=core.Application.get();d=fusion.Design.cast(app.activeProduct);c=d.rootComponent
report={}
try:
 for p in c.modelParameters:
  if p.role in ('Diameter','SectionSize','Height','Revolutions'):
   p.expression={'Diameter':'12 mm','SectionSize':'2 mm','Height':'24 mm','Revolutions':'8'}[p.role]
 d.computeAll()
 report['parameters']=[(p.name,p.role,p.expression) for p in c.modelParameters]
 body=c.bRepBodies.item(0)
 report['faces']=[(f.geometry.objectType,f.area) for f in body.faces]
 report['volume']=body.volume
 export=d.exportManager.createFusionArchiveExportOptions(str(repo/'PrintableThreads/resources/coil/circular.f3d'))
 report['exported']=d.exportManager.execute(export)
 faces=[f for f in body.faces if not core.Plane.cast(f.geometry)]
 inp=c.features.offsetFacesFeatures.createInput(faces,core.ValueInput.createByString('-0.2 mm'))
 feature=c.features.offsetFacesFeatures.add(inp);feature.name='Uniform Coil offset'
 report['offset_volume']=feature.bodies.item(0).volume
 for p in c.modelParameters:
  if p.role=='Height':p.expression='32 mm'
 d.computeAll()
 report['health']=[(d.timeline.item(i).entity.name,d.timeline.item(i).entity.errorOrWarningMessage) for i in range(d.timeline.count) if getattr(d.timeline.item(i).entity,'errorOrWarningMessage','')]
 report['passed']=not report['health']
except Exception:report['error']=traceback.format_exc()
(repo/'docs/native-coil-probe.json').write_text(json.dumps(report,indent=2));print(report)
