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
d.designIntent=fusion.DesignIntentTypes.HybridDesignIntentType
faces=[]
for i in range(2):
    transform=b.M();transform.translation=b.V(0,0,i*.3649991775936984)
    occurrence=d.rootComponent.occurrences.addNewComponent(transform);c=occurrence.component
    body=b.cylinder(2,0,3.649991775936984)
    b.persist(c,[body],'Disposable separate component')
    body=c.bRepBodies.item(0)
    face=next(f for f in body.faces if core.Cylinder.cast(f.geometry))
    faces.append(face.createForAssemblyContext(occurrence))
_,_,diameter,length,_=selection.cylinder_frame(faces)
commands.preferences.save=lambda *args:None
commands._probe_definition=app.userInterface.commandDefinitions.addButtonDefinition('PrintableThreads_solid_preview_probe','Disposable solid preview test','Test')
def configure(args):
    session=commands.Session(args.command,'apply');commands.sessions.append(session)
    session.load(replace(commands.Spec().with_circular_section(2),root_diameter=diameter,length=length,pitch=4,axial_clearance=0,radial_clearance=.1,knob='None',entry=0,output='Screw',cut_screw=True))
    for face in faces:session.values['target'].addSelection(face)
    session.measured_dimension('root_diameter',diameter);session.measured_dimension('length',length)
    session.loading=True;session.values['live_preview'].value=True;session.loading=False
    session.toggle_solid_preview()
    commands._probe_session=session
    assert session.values['root_diameter'].expression=='4 mm'
    assert session.values['length'].expression=='7.3 mm'
    assert abs(session.read().length-length)<1e-12
    assert session.expressions()['length']!='7.3 mm' 
    print('preview test document',app.activeDocument.name,'intent',d.designIntent)
commands._probe_configure=configure
events.add(commands._probe_definition.commandCreated,configure)
app.activeViewport.fit()
commands._probe_definition.execute()
