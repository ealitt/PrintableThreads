"""Disposable Fusion document: circular / On Center geometry validation."""
import sys, importlib, json, math, time
from pathlib import Path
import adsk.core as core
import adsk.fusion as fusion
repo=Path('/Users/eammon/Documents/GitHub/PrintableThreads')
sys.path.insert(0,str(repo))
from PrintableThreads.model import spec as sm
from PrintableThreads.geometry import backend as b
importlib.reload(sm);importlib.reload(b)
app=core.Application.get()
probe_document=app.documents.add(core.DocumentTypes.FusionDesignDocumentType)
d=fusion.Design.cast(app.activeProduct);d.designIntent=fusion.DesignIntentTypes.HybridDesignIntentType
report={'cases':[]}
try:
    from dataclasses import replace
    for name,s in [('nominal',sm.Spec().with_circular_section(2)),('small',replace(sm.Spec().with_circular_section(1),pitch=2)),('left',replace(sm.Spec().with_circular_section(2),left_hand=True)),('multi',replace(sm.Spec().with_circular_section(1),starts=3,pitch=2))]:
        s.validate();t=time.perf_counter();male=b.threaded(d.rootComponent,s,entry=False);female=b.female(d.rootComponent,s)
        inside=fusion.PointContainment.PointInsidePointContainment
        checks=0
        for z in (s.length*.4,s.length*.5,s.length*.6):
            angle=sm.phase_at_z(z,s.lead,s.phase,s.left_hand)
            r=s.root_diameter/2+s.height/2
            half=math.sqrt(s.height**2-(r-s.root_diameter/2)**2)
            def contains(dz):return male.pointContainment(core.Point3D.create(r*math.cos(angle)/10,r*math.sin(angle)/10,(z+dz)/10))==inside
            assert contains(half-.05),'circular section too narrow'
            assert not contains(half+.05),'circular section too wide'
            checks+=2
        overlap=b.manager().copy(female);assert b.manager().booleanOperation(overlap,male,fusion.BooleanTypes.IntersectionBooleanType)
        volume=overlap.volume if overlap.isSolid else 0
        assert volume<1e-6,'mating interference'
        report['cases'].append({'name':name,'section_size_mm':s.thread_size,'outside_diameter_mm':s.major_diameter,'section_checks':checks,'intersection_cm3':volume,'seconds':time.perf_counter()-t})
    report['passed']=True
except Exception:
    import traceback
    report['error']=traceback.format_exc()
finally:
    (repo/'docs/circular-section-probe.json').write_text(json.dumps(report,indent=2))
    probe_document.close(False)
print(report)
