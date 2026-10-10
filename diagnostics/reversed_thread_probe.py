"""Disposable Fusion document: both cut/join modes, fit, and print placement."""
import sys, importlib, json, math, time, traceback
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
    base=replace(sm.Spec().with_circular_section(2),cut_screw=True,entry=0)
    for name,s in [('reverse',base),('left',replace(base,left_hand=True)),('multi',replace(base.with_circular_section(1),starts=3,pitch=2)),('legacy_swap',replace(base,cut_screw=False)),('trapezoid',replace(sm.Spec(),cut_screw=True,entry=0))]:
        s.validate();t=time.perf_counter();male=b.threaded(d.rootComponent,s,entry=False);female=b.female(d.rootComponent,s)
        overlap=b.manager().copy(female);assert b.manager().booleanOperation(overlap,male,fusion.BooleanTypes.IntersectionBooleanType)
        volume=overlap.volume if overlap.isSolid else 0
        assert volume<1e-6,f'{name}: interference {volume}'
        if s.cut_screw:
            bare=b.threaded(d.rootComponent,s,entry=False)
            assert bare.volume<b.cylinder(s.root_diameter/2,0,s.length).volume,'screw must be cut'
            blank=b.cylinder(s.female_diameter/2,0,s.engagement);b.cut(blank,b.cylinder(s.root_diameter/2+s.radial_clearance,0,s.engagement))
            assert female.volume>blank.volume,'nut must have joined rib'
        report['cases'].append({'name':name,'seconds':time.perf_counter()-t,'intersection_cm3':volume})
    for blind in (False,True):
        s=replace(base,print_on_plate=True,blind=blind,entry=.6)
        male=b.screw(d.rootComponent,s);female=b.female(d.rootComponent,s)
        assert abs(male.boundingBox.minPoint.z)<1e-7,'head not on plate'
        assert abs(female.boundingBox.minPoint.z)<1e-7,'nut not on plate'
    report['print_placement_passed']=True
    for internal in (False,True):
        c=d.rootComponent.occurrences.addNewComponent(b.M()).component
        solid=b.cylinder(10 if internal else 6,0,18)
        if internal:b.cut(solid,b.cylinder(6,0,18))
        b.persist(c,[solid],'Apply test')
        target=c.bRepBodies.item(0);before=target.volume
        face=next(f for f in target.faces if core.Cylinder.cast(f.geometry) and abs(core.Cylinder.cast(f.geometry).radius-.6)<1e-7)
        selection.apply(d,face,base)
        after=target.volume
        assert after>before if internal else after<before,'wrong Apply operation'
    report['apply_passed']=True;report['passed']=True
except Exception:report['error']=traceback.format_exc()
finally:
    (repo/'docs/reversed-thread-probe.json').write_text(json.dumps(report,indent=2));doc.close(False)
print(report)
