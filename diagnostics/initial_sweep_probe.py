import adsk.core, adsk.fusion, traceback, json, pathlib, platform, time

def run(context):
    app=adsk.core.Application.get()
    report={'fusion':app.version,'platform':platform.platform(),'steps':[]}
    out=pathlib.Path(__file__).resolve().parents[2]/'docs'/'probe-result.json'
    def log(s):
        report['steps'].append(s); out.write_text(json.dumps(report,indent=2))
    try:
        app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        d=adsk.fusion.Design.cast(app.activeProduct); c=d.rootComponent
        log('new document')
        tm=adsk.fusion.TemporaryBRepManager.get()
        P=adsk.core.Point3D.create; V=adsk.core.Vector3D.create
        bf=c.features.baseFeatures.add(); bf.startEdit()
        wires=[]
        for r in [.595,.7]:
            w=tm.createHelixWire(P(0,0,0),V(0,0,1),P(r,0,-.45),.3,9,0)
            assert w, 'helix failed'
            b=c.bRepBodies.add(w,bf); wires.append(b)
        bf.finishEdit()
        log('persisted two helix wires')
        # Reacquire output bodies after leaving base-feature edit.
        wires=[bf.bodies.item(i) for i in range(bf.bodies.count)]
        sk=c.sketches.add(c.xZConstructionPlane)
        pts=[P(.595,0,-.45-.075),P(.7,0,-.45-.025),P(.7,0,-.45+.025),P(.595,0,-.45+.075)]
        pts=[sk.modelToSketchSpace(p) for p in pts]
        lines=sk.sketchCurves.sketchLines
        for i in range(4): lines.addByTwoPoints(pts[i],pts[(i+1)%4])
        path=adsk.fusion.Path.create(wires[0].edges.item(0),adsk.fusion.ChainedCurveOptions.noChainedCurves)
        guide=adsk.fusion.Path.create(wires[1].edges.item(0),adsk.fusion.ChainedCurveOptions.noChainedCurves)
        inp=c.features.sweepFeatures.createInput(sk.profiles.item(0),path,adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        inp.guideRail=guide
        inp.profileScaling=adsk.fusion.SweepProfileScalingOptions.SweepProfileNoScalingOption
        t=time.time(); sw=c.features.sweepFeatures.add(inp)
        log({'sweep':bool(sw),'seconds':time.time()-t,'solid':sw.bodies.item(0).isSolid})
        rib=tm.copy(sw.bodies.item(0))
        clip=tm.createCylinderOrCone(P(0,0,0),.8,P(0,0,1.8),.8)
        assert tm.booleanOperation(rib,clip,adsk.fusion.BooleanTypes.IntersectionBooleanType)
        core=tm.createCylinderOrCone(P(0,0,0),.6,P(0,0,1.8),.6)
        assert tm.booleanOperation(core,rib,adsk.fusion.BooleanTypes.UnionBooleanType)
        log({'trim_join':True,'volume':core.volume,'solid':core.isSolid,'lumps':core.lumps.count})
        b2=c.features.baseFeatures.add(); b2.startEdit(); result=c.bRepBodies.add(core,b2); b2.finishEdit()
        sw.bodies.item(0).isVisible=False
        for b in wires: b.isVisible=False
        sk.isVisible=False
        app.activeViewport.fit()
        report['status']='sweep_candidate_passed'; log('needs section and clearance verification')
    except Exception:
        report['status']='failed'; report['error']=traceback.format_exc(); log('failure')
    app.userInterface.messageBox(json.dumps(report,indent=2),'Printable Threads probe')
