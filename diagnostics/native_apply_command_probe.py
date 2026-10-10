"""Run the real Apply command on a regular bore in a disposable Part document."""
import sys,importlib
from pathlib import Path
import adsk.core as core,adsk.fusion as fusion
from dataclasses import replace
repo=Path('/Users/eammon/Documents/GitHub/PrintableThreads');sys.path.insert(0,str(repo))
from PrintableThreads import commands
from PrintableThreads.fusion_backend import native
commands.stop();importlib.reload(native);importlib.reload(commands);commands.start()
from PrintableThreads.lib import events
from PrintableThreads.model.spec import Spec
app=core.Application.get()
app.unregisterCustomEvent('PrintableThreads_test_execute')
commands._original_preference_save=commands.preferences.save
commands.preferences.save=lambda *args:None
commands._probe_document=app.documents.add(core.DocumentTypes.FusionDesignDocumentType)
d=fusion.Design.cast(app.activeProduct);commands._probe_design=d;c=d.rootComponent
sk=c.sketches.add(c.xYConstructionPlane)
for r in (.6,1.1):sk.sketchCurves.sketchCircles.addByCenterRadius(core.Point3D.create(0,0,0),r)
profile=next(p for p in sk.profiles if p.profileLoops.count==2)
inp=c.features.extrudeFeatures.createInput(profile,fusion.FeatureOperations.NewBodyFeatureOperation)
inp.setDistanceExtent(False,core.ValueInput.createByReal(1.2))
body=c.features.extrudeFeatures.add(inp).bodies.item(0)
face=next(f for f in body.faces if core.Cylinder.cast(f.geometry) and abs(core.Cylinder.cast(f.geometry).radius-.6)<1e-6)
marker=d.timeline.markerPosition;downstream=c.sketches.add(c.xYConstructionPlane);downstream.name='Downstream test sketch';d.timeline.markerPosition=marker
commands._probe_face=face

def configure(args):
    session=commands.sessions[-1]
    session.load(replace(Spec().with_circular_section(2),cut_screw=True,knob='None',entry=0,length=12,engagement=12,output='Screw'))
    session.values['target'].addSelection(face)
    commands._probe_session=session
    app.fireCustomEvent('PrintableThreads_test_execute')
def complete(args):commands._probe_session.command.doExecute(True)
events.add(app.registerCustomEvent('PrintableThreads_test_execute'),complete)
definition=app.userInterface.commandDefinitions.itemById('PrintableThreads_apply')
events.add(definition.commandCreated,configure)
definition.execute()
print('Apply to regular bore scheduled before downstream sketch')
