"""Check nut ribs reach both end planes without axial protrusions."""
import sys,importlib,json,math,traceback
from pathlib import Path
from dataclasses import replace
import adsk.core as core
import adsk.fusion as fusion
repo=Path('/Users/eammon/Documents/GitHub/PrintableThreads');sys.path.insert(0,str(repo))
from PrintableThreads.model import spec as sm
from PrintableThreads.geometry import backend as b
importlib.reload(sm);importlib.reload(b)
app=core.Application.get();doc=app.documents.add(core.DocumentTypes.FusionDesignDocumentType)
d=fusion.Design.cast(app.activeProduct);d.designIntent=fusion.DesignIntentTypes.HybridDesignIntentType
report={'cases':[]}
try:
    base=replace(sm.Spec().with_circular_section(2),cut_screw=True,print_on_plate=True)
    for name,s in [('default',base),('fractional',replace(base,engagement=7.4,phase=37)),('left',replace(base,left_hand=True)),('multi',replace(base.with_circular_section(1),starts=3,pitch=2)),('blind',replace(base,blind=True))]:
        body=b.female(d.rootComponent,s);shift=s.floor if s.blind else 0
        assert abs(body.boundingBox.minPoint.z)<1e-7
        assert abs(body.boundingBox.maxPoint.z-(s.engagement+shift)/10)<1e-7
        checks=0
        for z in (.005,s.engagement-.005):
            angle=sm.phase_at_z(z,s.lead,s.phase,s.left_hand);r=s.root_diameter/2+s.radial_clearance-s.height/2
            point=core.Point3D.create(r*math.cos(angle)/10,r*math.sin(angle)/10,(z+shift)/10)
            assert body.pointContainment(point)==fusion.PointContainment.PointInsidePointContainment, f'{name}: recessed rib at z={z}'
            checks+=1
        report['cases'].append({'name':name,'end_rib_checks':checks,'z_min_mm':body.boundingBox.minPoint.z*10,'z_max_mm':body.boundingBox.maxPoint.z*10})
    report['passed']=True
except Exception:report['error']=traceback.format_exc()
finally:
    (repo/'docs/flush-nut-probe.json').write_text(json.dumps(report,indent=2));doc.close(False)
print(report)
