"""Open the candidate Apply dialog only in a new disposable document."""
import adsk.core as core,adsk.fusion as fusion,sys,importlib
from pathlib import Path
import json,time
from types import SimpleNamespace
from dataclasses import replace
sys.path.insert(0,'/Users/eammon/Documents/GitHub/Fusion-3D-printable-threads')
from PrintableThreads import commands
from PrintableThreads.geometry import backend as b
from PrintableThreads.fusion_backend import selection,native,preview
from PrintableThreads.lib import events
for m in (b,selection,native,preview,commands):importlib.reload(m)
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
commands._probe_log=[]
commands._probe_sweep_calls=0
commands._probe_original_sweep=b.sweep_rib
def counted_sweep(*args,**kwargs):
    commands._probe_sweep_calls+=1
    return commands._probe_original_sweep(*args,**kwargs)
b.sweep_rib=counted_sweep
def configure(args):
    session=commands.Session(args.command,'apply');commands.sessions.append(session)
    session.load(replace(commands.Spec().with_circular_section(2),root_diameter=diameter,length=length,pitch=4,axial_clearance=0,radial_clearance=.1,knob='None',entry=0,output='Screw',cut_screw=True))
    for face in faces:session.values['target'].addSelection(face)
    session.measured_dimension('root_diameter',diameter);session.measured_dimension('length',length)
    session.loading=True;session.values['live_preview'].value=True;session.loading=False
    session.toggle_solid_preview()
    commands._probe_session=session
    def record(kind):
        entry={'event':kind,'time':time.perf_counter(),'sweeps':commands._probe_sweep_calls,'pitch':session.values['pitch'].expression,'dirty':session.preview_dirty,'requested':session.preview_requested,'valid':bool(session.renderer.group and session.renderer.group.isValid),'visible':all(f.body.isLightBulbOn for f in faces)}
        commands._probe_log.append(entry)
        Path('/Users/eammon/Documents/GitHub/Fusion-3D-printable-threads/docs/beta-preview-events-0.5.5.json').write_text(json.dumps(commands._probe_log,indent=2))
    events.add(args.command.inputChanged,lambda a:record(a.input.id))
    tested=[False]
    def verify(a):
        record('preview')
        if tested[0]:return
        tested[0]=True
        report={}
        assert commands._probe_sweep_calls==1 and session.renderer.group.isValid
        report['initial_snapshot']=True
        session.loading=True;session.values['pitch'].expression='5 mm';session.loading=False
        start=time.perf_counter();session.changed(SimpleNamespace(input=session.values['pitch']))
        for _ in range(5):session.render_preview()
        report['edit_seconds']=time.perf_counter()-start
        assert session.preview_dirty and commands._probe_sweep_calls==1
        assert all(f.body.isLightBulbOn for f in faces)
        report['edit_without_geometry']=True
        session.preview_requested=True;session.render_preview()
        assert commands._probe_sweep_calls==2 and session.renderer.group.isValid
        report['explicit_refresh']=True
        session.preview_requested=True;session.render_preview()
        assert commands._probe_sweep_calls==2
        report['unchanged_refresh_reuses_cache']=True
        start=time.perf_counter()
        for _ in range(5):session.render_preview()
        report['five_cached_redraws_seconds']=time.perf_counter()-start
        assert commands._probe_sweep_calls==2 and session.renderer.group.isValid
        report['cached_redraw_without_geometry']=True
        session.renderer.clear()
        assert all(f.body.isLightBulbOn for f in faces)
        report['visibility_restored']=True
        session.render_preview()
        report['passed']=True
        Path('/Users/eammon/Documents/GitHub/Fusion-3D-printable-threads/docs/beta-preview-command-0.5.5.json').write_text(json.dumps(report,indent=2))
        print(report)
    commands._probe_verify=verify
    events.add(args.command.executePreview,verify)
    events.add(args.command.destroy,lambda a:record('destroy'))
    assert session.values['root_diameter'].expression=='4 mm'
    assert session.values['length'].expression=='7.3 mm'
    assert abs(session.read().length-length)<1e-12
    assert session.expressions()['length']!='7.3 mm' 
    print('preview test document',app.activeDocument.name,'intent',d.designIntent)
commands._probe_configure=configure
events.add(commands._probe_definition.commandCreated,configure)
app.activeViewport.fit()
commands._probe_definition.execute()
