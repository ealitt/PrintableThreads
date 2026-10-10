import sys,importlib,json,traceback,math
from pathlib import Path
from dataclasses import replace
import adsk.core as core,adsk.fusion as fusion
repo=Path('/Users/eammon/Documents/GitHub/PrintableThreads');sys.path.insert(0,str(repo))
from PrintableThreads.fusion_backend import native
from PrintableThreads.model.spec import Spec
importlib.reload(native)
app=core.Application.get();report=[]
for shape in ('Circular','Trapezoid'):
 doc=app.documents.add(core.DocumentTypes.FusionDesignDocumentType);d=fusion.Design.cast(app.activeProduct)
 s=replace(Spec(),cut_screw=True,knob='None',entry=0,length=6,engagement=6,output='Screw')
 if shape=='Circular':s=s.with_circular_section(2)
 result={'shape':shape}
 try:
  b=native.Builder(d,s);occ,c=b.component('Probe');p=b.p
  sk=c.sketches.add(c.xZConstructionPlane);sk.name='Thread section'
  if shape=='Circular':
   circle=sk.sketchCurves.sketchCircles.addByCenterRadius(core.Point3D.create(s.root_diameter/20,0,0),s.height/10)
   b.point(sk,circle.centerSketchPoint,f'{p["diameter"]}/2','0 mm')
   sk.sketchDimensions.addDiameterDimension(circle,core.Point3D.create(1,1,0)).parameter.expression=p['section']
  else:b.trapezoid(sk,f'{p["diameter"]}/2',p['height'],'0 mm',-1,True,lambda r,z:sk.modelToSketchSpace(core.Point3D.create(r,0,z)))
  guide=c.sketches.add(c.xZConstructionPlane)
  line=guide.sketchCurves.sketchLines.addByTwoPoints(core.Point3D.create(0,0,0),core.Point3D.create(0,-s.length/10,0))
  b.point(guide,line.startSketchPoint,'0 mm','0 mm');b.point(guide,line.endSketchPoint,'0 mm','-'+p['length'])
  inp=c.features.sweepFeatures.createInput(sk.profiles.item(0),fusion.Path.create(line.createForAssemblyContext(occ),fusion.ChainedCurveOptions.noChainedCurves),fusion.FeatureOperations.NewBodyFeatureOperation)
  inp.creationOccurrence=occ;inp.orientation=fusion.SweepOrientationTypes.ParallelOrientationType
  inp.twistAngle=native.VI(f'360 deg*{p["length"]}/{p["lead"]}')
  f=c.features.sweepFeatures.add(inp);body=f.bodies.item(0)
  result['faces']=body.faces.count;result['volume']=body.volume
  faces=[face.createForAssemblyContext(occ) for face in body.faces if not core.Plane.cast(face.geometry)]
  off=c.features.offsetFacesFeatures.add(c.features.offsetFacesFeatures.createInput(faces,native.VI('-'+p['tolerance'])))
  result['offset']=off.bodies.item(0).volume
  d.userParameters.itemByName(p['pitch']).expression='4 mm';d.computeAll()
  result['health']=[(f.name,f.errorOrWarningMessage) for f in c.features if f.errorOrWarningMessage]
  result['passed']=not result['health']
 except Exception:result['error']=traceback.format_exc()
 finally:report.append(result);doc.close(False)
(repo/'docs/native-twist-probe.json').write_text(json.dumps(report,indent=2));print(report)
