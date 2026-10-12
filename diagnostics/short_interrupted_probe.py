"""Native-kernel regressions in disposable documents; never saves user models."""
import sys,json,traceback,importlib
from pathlib import Path
from dataclasses import replace
import adsk.core as core
import adsk.fusion as fusion
repo=Path('/Users/eammon/Documents/GitHub/Fusion-3D-printable-threads')
sys.path.insert(0,str(repo))
from PrintableThreads.model import spec as sm
from PrintableThreads.geometry import backend as b
from PrintableThreads.fusion_backend import selection,native,preview
for m in (sm,b,selection,native,preview):importlib.reload(m)
app=core.Application.get();original=app.activeDocument
report={'cases':[]}
def box(cx,cy,cz,l,w,h):
    return b.manager().createBox(core.OrientedBoundingBox3D.create(b.P(cx/10,cy/10,cz/10),b.V(1,0,0),b.V(0,1,0),l/10,w/10,h/10))
try:
    for kind in ('short','partial','slot','draft','slant'):
      for internal,cut in ((False,True),(False,False),(True,True),(True,False)):
        doc=app.documents.add(core.DocumentTypes.FusionDesignDocumentType)
        try:
            d=fusion.Design.cast(app.activeProduct);d.designIntent=fusion.DesignIntentTypes.HybridDesignIntentType
            c=d.rootComponent
            length=3.65 if kind=='short' else 12
            radius=2 if kind=='short' else 6
            body=b.cylinder(radius if not internal else radius+4,0,length,r1=radius+.3 if kind=='draft' and not internal else None)
            if internal:b.cut(body,b.cylinder(radius,0,length,r1=radius+.3 if kind=='draft' else None))
            missing=None
            if kind=='partial':missing=box(radius+5,0,length/2,2*(radius+5),30,length+4)
            elif kind=='slot':missing=box(0,0,length/2,1,30,length+4)
            elif kind=='slant':
                missing=box(0,0,length+4,30,30,8)
                rot=b.M();rot.setToRotation(.12,b.V(1,0,0),b.P(0,0,length/10));b.transform(missing,rot)
            if missing:b.cut(body,missing)
            b.persist(c,[body],'Regression target');target=c.bRepBodies.item(0)
            faces=[f for f in target.faces if (core.Cone.cast(f.geometry) if kind=='draft' else core.Cylinder.cast(f.geometry)) and ((core.Cone.cast(f.geometry) or core.Cylinder.cast(f.geometry)).radius< (radius+1)/10)]
            selected=tuple(faces)
            f,frame,diameter,available,inside=selection.cylinder_frame(selected)
            assert inside==internal
            size=3 if kind=='short' else 1.4
            spec=replace(sm.Spec().with_circular_section(size),root_diameter=diameter,length=min(length,available),pitch=5 if kind=='short' else 3,radial_clearance=.1,axial_clearance=0,entry=0,knob='None',cut_screw=cut,output='Screw').validate()
            before=target.volume;count=c.bRepBodies.count;timeline=d.timeline.count
            candidate=selection.preview_body(d,selected,spec)
            assert c.bRepBodies.count==count
            renderer=preview.Renderer().begin(c);renderer.draw_body(candidate,target);renderer.clear()
            assert target.isLightBulbOn
            result=native.apply(d,selected,spec)
            assert result.isSolid and result.volume>0
            total=sum(item.volume for item in c.bRepBodies)
            assert total>before if internal==cut and not internal else total>0
            assert abs(total-candidate.volume)/candidate.volume<.06,'preview/result volumes differ too far'
            if missing:
                for item in c.bRepBodies:
                    overlap=b.manager().copy(item)
                    b.manager().booleanOperation(overlap,missing,fusion.BooleanTypes.IntersectionBooleanType)
                    assert not overlap.isSolid or overlap.volume<1e-7,'thread filled the removed region' 
            report['cases'].append({'kind':kind,'internal':internal,'cut':cut,'faces':len(faces),'diameter':diameter,'available':available,'volume_before':before,'volume_after':total,'result_bodies':c.bRepBodies.count,'preview_volume':candidate.volume})
        finally:
            (repo/'docs/short-interrupted-probe.json').write_text(json.dumps(report,indent=2))
            doc.close(False)
    report['passed']=True
except Exception:
    report['error']=traceback.format_exc()
finally:
    if original and original.isValid:original.activate()
    (repo/'docs/short-interrupted-probe.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
