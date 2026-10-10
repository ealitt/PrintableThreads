"""Run from Fusion's Scripts dialog. Creates a new disposable Part document."""
import adsk.core, adsk.fusion, importlib, json, pathlib, sys, traceback

def run(context):
    app=adsk.core.Application.get()
    repo=pathlib.Path.home()/'Documents/GitHub/Fusion-3D-printable-threads'
    out=repo/'docs'/'part-apply-probe.json'
    report={'fusion':app.version,'status':'running'}
    try:
        sys.path.insert(0,str(repo))
        from PrintableThreads.model import spec as sm
        from PrintableThreads.geometry import backend as b
        from PrintableThreads.fusion_backend import selection
        from PrintableThreads import commands
        for module in (sm,b,selection,commands):importlib.reload(module)
        app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        d=adsk.fusion.Design.cast(app.activeProduct)
        d.designIntent=adsk.fusion.DesignIntentTypes.PartDesignIntentType
        root=d.rootComponent
        base=b.persist(root,[b.cylinder(6,0,12)],'Part apply blank')
        body=base.bodies.item(0) if base else root.bRepBodies.item(0)
        face=next(f for f in body.faces if adsk.core.Cylinder.cast(f.geometry))
        assert d.designIntent==adsk.fusion.DesignIntentTypes.PartDesignIntentType
        assert commands.design(False,True)==d
        assert d.designIntent==adsk.fusion.DesignIntentTypes.PartDesignIntentType
        commands.design(True,True)
        assert d.designIntent==adsk.fusion.DesignIntentTypes.HybridDesignIntentType
        selection.apply(d,face,sm.Spec(length=12))
        assert body.isValid and body.volume>0
        report.update(status='passed',intent='Hybrid',body_count=root.bRepBodies.count,
                      feature_count=root.features.count)
        app.activeViewport.fit()
    except Exception:
        report.update(status='failed',error=traceback.format_exc())
    finally:
        if str(repo) in sys.path:sys.path.remove(str(repo))
        out.write_text(json.dumps(report,indent=2))
    app.userInterface.messageBox(json.dumps(report,indent=2),'Part Apply probe')
