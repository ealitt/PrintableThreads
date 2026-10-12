"""Open the candidate Apply dialog only in a new disposable document."""
import adsk.core as core,adsk.fusion as fusion,sys,importlib
from pathlib import Path
from dataclasses import replace
sys.path.insert(0,'/Users/eammon/Documents/GitHub/Fusion-3D-printable-threads')
from PrintableThreads import commands
from PrintableThreads.geometry import backend as b
from PrintableThreads.fusion_backend import selection,native,preview
from PrintableThreads.lib import events
for m in (selection,native,preview,commands):importlib.reload(m)
app=core.Application.get()
commands._probe_original=app.activeDocument
commands._probe_doc=app.documents.add(core.DocumentTypes.FusionDesignDocumentType)
d=fusion.Design.cast(app.activeProduct)
d.designIntent=fusion.DesignIntentTypes.PartDesignIntentType
# Intentionally keep default Part intent to test the user's ordinary workflow.
sk=d.rootComponent.sketches.add(d.rootComponent.xYConstructionPlane)
sk.sketchCurves.sketchCircles.addByCenterRadius(b.P(0,0,0),.2)
inp=d.rootComponent.features.extrudeFeatures.createInput(sk.profiles.item(0),fusion.FeatureOperations.NewBodyFeatureOperation)
inp.setDistanceExtent(False,core.ValueInput.createByReal(.365))
body=d.rootComponent.features.extrudeFeatures.add(inp).bodies.item(0)
sk.isVisible=False
face=next(f for f in body.faces if core.Cylinder.cast(f.geometry))
commands.preferences.save=lambda *args:None
commands._probe_definition=app.userInterface.commandDefinitions.addButtonDefinition('PrintableThreads_solid_preview_probe','Disposable solid preview test','Test')
def configure(args):
    session=commands.Session(args.command,'apply');commands.sessions.append(session)
    session.load(replace(commands.Spec().with_circular_section(3),root_diameter=4,length=3.65,pitch=5,axial_clearance=0,radial_clearance=.1,knob='None',entry=0,output='Screw',cut_screw=True))
    session.values['target'].addSelection(face)
    session.loading=True;session.values['live_preview'].value=True;session.loading=False
    session.toggle_solid_preview()
    commands._probe_session=session
    print('preview test document',app.activeDocument.name,'intent',d.designIntent)
commands._probe_configure=configure
events.add(commands._probe_definition.commandCreated,configure)
app.activeViewport.fit()
commands._probe_definition.execute()
