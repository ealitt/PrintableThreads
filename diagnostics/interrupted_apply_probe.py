"""Disposable partial / slotted cylindrical Apply regression."""
import sys,importlib,json,traceback
from pathlib import Path
from dataclasses import replace
import adsk.core as core
import adsk.fusion as fusion
repo=Path('/Users/eammon/Documents/GitHub/PrintableThreads');sys.path.insert(0,str(repo))
from PrintableThreads.model import spec as sm
from PrintableThreads.geometry import backend as b
from PrintableThreads.fusion_backend import selection
importlib.reload(sm);importlib.reload(b);importlib.reload(selection)
app=core.Application.get();doc=app.documents.add(core.DocumentTypes.FusionDesignDocumentType)
d=fusion.Design.cast(app.activeProduct);d.designIntent=fusion.DesignIntentTypes.HybridDesignIntentType
report={'cases':[]}
try:
    def box(cx,cy,cz,l,w,h):
        return b.manager().createBox(core.OrientedBoundingBox3D.create(b.P(cx/10,cy/10,cz/10),b.V(1,0,0),b.V(0,1,0),l/10,w/10,h/10))
    for internal,cut_screw in ((False,True),(False,False),(True,True),(True,False)):
        c=d.rootComponent.occurrences.addNewComponent(b.M()).component
        body=b.cylinder(10 if internal else 6,0,18)
        if internal:b.cut(body,b.cylinder(6,0,18))
        missing=box(10,0,9,20,30,22);b.cut(body,missing)
        b.persist(c,[body],'Partial cylinder')
        target=c.bRepBodies.item(0)
        face=next(f for f in target.faces if core.Cylinder.cast(f.geometry) and abs(core.Cylinder.cast(f.geometry).radius-.6)<1e-7)
        _,_,diameter,length,_=selection.cylinder_frame(face)
        assert abs(diameter-12)<1e-5 and abs(length-18)<1e-4
        before=target.volume
        s=replace(sm.Spec().with_circular_section(1),cut_screw=cut_screw,knob='None',entry=0)
        selection.apply(d,face,s)
        assert target.isSolid
        overlap=b.manager().copy(target);assert b.manager().booleanOperation(overlap,missing,fusion.BooleanTypes.IntersectionBooleanType)
        volume=overlap.volume if overlap.isSolid else 0
        assert volume<1e-7,'thread bridged the removed half'
        report['cases'].append({'internal':internal,'cut_screw':cut_screw,'volume_before':before,'volume_after':target.volume,'missing_region_overlap_cm3':volume})
    report['passed']=True
except Exception:report['error']=traceback.format_exc()
finally:
    (repo/'docs/interrupted-apply-probe.json').write_text(json.dumps(report,indent=2));doc.close(False)
print(report)
