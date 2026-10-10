"""Run from Fusion's Scripts dialog. Creates only a new diagnostic document."""
import adsk.core, adsk.fusion, traceback, json, pathlib, platform, time, sys, importlib, math

def run(context):
    app=adsk.core.Application.get()
    repo=pathlib.Path(__file__).resolve().parents[2]
    sys.path.insert(0,str(repo))
    report={'fusion':app.version,'platform':platform.platform(),'steps':[]}
    out=repo/'docs'/'probe-result.json'
    def log(s):
        report['steps'].append(s);out.write_text(json.dumps(report,indent=2))
    try:
        from PrintableThreads.model import spec as sm
        from PrintableThreads.geometry import profile, backend as b
        importlib.reload(sm);importlib.reload(profile);importlib.reload(b)
        app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        d=adsk.fusion.Design.cast(app.activeProduct)
        d.designIntent=adsk.fusion.DesignIntentTypes.HybridDesignIntentType
        root=d.rootComponent
        P=adsk.core.Point3D.create
        inside=adsk.fusion.PointContainment.PointInsidePointContainment
        cases=[('nominal',sm.Spec()),('three-start',sm.Spec(pitch=2,starts=3,width=1.3,length=12)),
               ('left',sm.Spec(left_hand=True)),('fractional',sm.Spec(length=1.5,entry=.2))]
        for index,(name,s) in enumerate(cases):
            t=time.time();male=b.threaded(root,s,entry=False);female=b.female(root,s)
            log({'case':name,'seconds':time.time()-t,'male_volume_cm3':male.volume,'female_volume_cm3':female.volume})
            # Crest and mid-flank containment in radial–axial sections at multiple angles.
            checks=0
            for z in [s.length*.4,s.length*.5,s.length*.6]:
                theta=sm.phase_at_z(z,s.lead,s.phase,s.left_hand)
                def contains(radius,dz):
                    return male.pointContainment(P(radius*math.cos(theta)/10,radius*math.sin(theta)/10,(z+dz)/10)) == inside
                assert contains(s.major_diameter/2-.03,0), 'crest is too low'
                assert not contains(s.major_diameter/2+.03,0), 'crest is too high'
                r=s.root_diameter/2+s.height*.5
                half=(s.width+(s.crest-s.width)*(s.height*.5+.08)/(s.height+.08))/2
                assert contains(r,half-.06), 'axial section too narrow'
                assert not contains(r,half+.06), 'axial section too wide'
                checks+=4
            log({'case':name,'section_checks':checks,'section_tolerance_mm':.06})
            # A true intersection operation must succeed even when the result is empty.
            volumes=[]
            for angle in [0,.37,1.13]:
                moved=b.manager().copy(male);b.rotate(moved,angle)
                b.move(moved,z=(-1 if s.left_hand else 1)*s.lead*angle/(2*math.pi))
                overlap=b.manager().copy(female)
                ok=b.manager().booleanOperation(overlap,moved,adsk.fusion.BooleanTypes.IntersectionBooleanType)
                assert ok,'Intersection kernel operation failed'
                volume=overlap.volume if overlap.isSolid else 0
                assert volume < 1e-6, f'interference {volume} cm3'
                volumes.append(volume)
            log({'case':name,'intersections_cm3':volumes})
            for label,body,x in [('screw',male,index*32),('female',female,index*32+16)]:
                occ=root.occurrences.addNewComponent(adsk.core.Matrix3D.create());occ.component.name=name+' '+label
                b.move(body,x=x);b.persist(occ.component,[body],name)
        from dataclasses import replace
        from PrintableThreads.fusion_backend import ownership,selection
        importlib.reload(ownership);importlib.reload(selection)
        s=sm.Spec()
        actual=b.screw(root,s); cap=b.female(root,replace(s,blind=True))
        assert cap.pointContainment(P(0,0,-.1))==inside, 'cap floor missing'
        owned=ownership.commit(root,s,[('Screw',actual,b.M())])
        target=owned[0].component.bRepBodies.item(0)
        ownership.regenerate(d,target,replace(s,pitch=3.5))
        assert sm.Spec.from_json(json.dumps(ownership.record_for(target)[2]['recipe'])).pitch==3.5
        log({'owned_regenerate':True,'knob_solid':True,'blind_floor':True})
        # Native apply to a rotated, translated occurrence; unrelated body is invariant.
        for internal in (False,True):
            placement=b.M();placement.setToRotation(.6,b.V(1,1,0),P(0,0,0));placement.translation=b.V(0,4,0)
            occurrence=root.occurrences.addNewComponent(placement);comp=occurrence.component
            blank=b.cylinder(11 if internal else 6,0,18)
            if internal:b.cut(blank,b.cylinder(6,0,18))
            base=b.persist(comp,[blank,b.cylinder(2,0,5,x=30)],'Apply test blank')
            body=base.bodies.item(0);neighbor=base.bodies.item(1);before=neighbor.volume
            candidates=[f for f in body.faces if adsk.core.Cylinder.cast(f.geometry) and abs(f.geometry.radius-.6)<1e-6]
            assert len(candidates)==1
            selection.apply(d,candidates[0].createForAssemblyContext(occurrence),s)
            assert abs(neighbor.volume-before)<1e-10
            assert comp.bRepBodies.count==2
            log({'apply_internal':internal,'target_only':True,'rotated_occurrence':True})
        try:
            ownership.editable(d,target)
            raise AssertionError('Editing after downstream creation should be blocked')
        except ValueError:log({'downstream_edit_blocked':True})
        export=d.exportManager.createFusionArchiveExportOptions(str(repo/'docs'/'geometry-validation.f3d'))
        assert d.exportManager.execute(export)
        app.activeViewport.fit()
        app.activeViewport.saveAsImageFile(str(repo/'docs'/'geometry-validation.png'),1600,1000)
        report['status']='passed';log('rounded profiles, section checks, trim, join, female cut and coordinated fit passed')
    except Exception:
        report['status']='failed';report['error']=traceback.format_exc();log('failure')
    finally:
        sys.path.remove(str(repo))
    app.userInterface.messageBox(json.dumps(report,indent=2),'Printable Threads probe')
