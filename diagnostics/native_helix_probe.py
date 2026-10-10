import adsk.core as core, adsk.fusion as fusion, json, traceback
from pathlib import Path
app=core.Application.get()
doc=app.documents.add(core.DocumentTypes.FusionDesignDocumentType)
d=fusion.Design.cast(app.activeProduct);d.designIntent=fusion.DesignIntentTypes.HybridDesignIntentType
c=d.rootComponent
P=core.Point3D.create
report={}
try:
    s=c.sketches.add(c.xYConstructionPlane)
    line=s.sketchCurves.sketchLines.addByTwoPoints(P(.5,0,0),P(.7,0,0))
    pathsk=c.sketches.add(c.xZConstructionPlane)
    linepath=pathsk.sketchCurves.sketchLines.addByTwoPoints(pathsk.modelToSketchSpace(P(0,0,0)),pathsk.modelToSketchSpace(P(0,0,2.4)))
    inp=c.features.sweepFeatures.createInput(c.createOpenProfile(line),fusion.Path.create(linepath,fusion.ChainedCurveOptions.noChainedCurves),fusion.FeatureOperations.NewBodyFeatureOperation)
    inp.isSolid=False;inp.twistAngle=core.ValueInput.createByString('8 * 360 deg')
    surf=c.features.sweepFeatures.add(inp)
    report['surface']=surf.bodies.count
    body=surf.bodies.item(0)
    report['edges']=[{'type':e.geometry.objectType,'length':e.length,'start':e.startVertex.geometry.asArray(),'end':e.endVertex.geometry.asArray()} for e in body.edges]
    edges=sorted(list(body.edges),key=lambda e:e.length,reverse=True)[:2]
    edges.sort(key=lambda e:(e.startVertex.geometry.x**2+e.startVertex.geometry.y**2))
    sk=c.sketches.add(c.xZConstructionPlane)
    sk.sketchCurves.sketchCircles.addByCenterRadius(sk.modelToSketchSpace(P(.6,0,0)),.1)
    inp=c.features.sweepFeatures.createInput(sk.profiles.item(0),fusion.Path.create(edges[0],fusion.ChainedCurveOptions.noChainedCurves),fusion.FeatureOperations.NewBodyFeatureOperation)
    inp.guideRail=fusion.Path.create(edges[1],fusion.ChainedCurveOptions.noChainedCurves)
    inp.profileScaling=fusion.SweepProfileScalingOptions.SweepProfileNoScalingOption
    sweep=c.features.sweepFeatures.add(inp)
    report['rib']={'volume':sweep.bodies.item(0).volume,'solid':sweep.bodies.item(0).isSolid}
except Exception:report['error']=traceback.format_exc()
finally:
    Path('/Users/eammon/Documents/GitHub/PrintableThreads/docs/native-helix-probe.json').write_text(json.dumps(report,indent=2))
    doc.close(False)
print(report)
