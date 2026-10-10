"""Developer console probe. Opens disposable documents and real command dialogs.

Load into Fusion's Python console, then call open_preview(commands_module, mode).
Cancel each dialog after inspection. Report includes actual viewport refresh time.
"""
import adsk.core as core
import adsk.fusion as fusion
import json
import time
from pathlib import Path
from types import SimpleNamespace

retained=[]
report={}
out=Path(__file__).resolve().parents[1]/'docs'/'preview-probe.json'

def open_preview(pt,mode):
    app=core.Application.get();ui=app.userInterface
    app.documents.add(core.DocumentTypes.FusionDesignDocumentType)
    design=fusion.Design.cast(app.activeProduct)
    design.designIntent=fusion.DesignIntentTypes.HybridDesignIntentType
    root=design.rootComponent;target=None
    if mode=='apply':
        base=pt.b.persist(root,[pt.b.cylinder(6,0,18)],'Preview test cylinder')
        target=next(face for face in base.bodies.item(0).faces if core.Cylinder.cast(face.geometry))
    elif mode=='edit':
        owned=pt.ownership.commit(root,pt.Spec(),[('Screw',pt.b.cylinder(6,0,18),pt.b.M())])
        target=owned[0].component.bRepBodies.item(0).createForAssemblyContext(owned[0])
    definition=ui.commandDefinitions.itemById(pt.PREFIX+mode)
    once={'done':False}

    def inspect(args):
        if once['done']:return
        once['done']=True
        session=next(s for s in pt.sessions if s.command==args.firingEvent.sender)
        data={}
        try:
            if target and not session.values['target'].selectionCount:
                session.values['target'].addSelection(target)
                session.changed(SimpleNamespace(input=session.values['target']))
            session.preview_key=None;session.render_preview()
            assert session.renderer.group and session.renderer.group.isValid,'No live graphics'
            data['entities']=session.renderer.group.count
            before=design.timeline.count
            session.values['live_preview'].value=False;session.render_preview()
            assert session.renderer.group is None,'Preview off did not clear graphics'
            session.values['live_preview'].value=True
            session.loading=True;session.values['thread_size'].expression='1.2 mm';session.loading=False
            start=time.perf_counter()
            session.changed(SimpleNamespace(input=session.values['thread_size']))
            session.render_preview()
            data['update_ms']=(time.perf_counter()-start)*1000
            assert session.renderer.group and session.renderer.group.isValid,'Input change did not redraw'
            assert abs(session.read().height-1.2)<1e-8
            data['toggle_and_change']=True
            data['timeline_unchanged']=design.timeline.count==before
            app.activeViewport.fit()
            app.activeViewport.saveAsImageFile(str(out.parent/f'preview-{mode}.png'),1200,800)
            data['status']='passed'
        except Exception as error:
            data['status']='failed';data['error']=str(error)
        report[mode]=data;out.write_text(json.dumps(report,indent=2))

    def created(args):
        if target:
            def activated(event_args):
                session=next(s for s in pt.sessions if s.command==args.command)
                if not session.values['target'].selectionCount:
                    session.values['target'].addSelection(target)
                    session.changed(SimpleNamespace(input=session.values['target']))
            pt.events.add(args.command.activate,activated,retained)
        pt.events.add(args.command.executePreview,inspect,retained)
        def destroyed(event_args):
            report.setdefault(mode,{})['cleared_after_cancel']=root.customGraphicsGroups.count==0
            out.write_text(json.dumps(report,indent=2))
        pt.events.add(args.command.destroy,destroyed,retained)
    pt.events.add(definition.commandCreated,created,retained)
    definition.execute()
