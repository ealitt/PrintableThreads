"""Cylindrical-face placement in the owning component's coordinates."""
import math
from dataclasses import replace
import adsk.core as core
import adsk.fusion as fusion
from ..geometry import backend as b
from ..model.solid import validate_applied

def cylinder_frame(selected,reverse=False):
    face=selected.nativeObject or selected
    cylinder=core.Cylinder.cast(face.geometry)
    if not cylinder or not face.body.isSolid: raise ValueError('Select a circular cylindrical face on a solid body.')
    circles=[]
    for edge in face.edges:
        circle=core.Circle3D.cast(edge.geometry)
        if circle:circles.append(circle)
    if len(circles)!=2 or any(abs(v.radius-cylinder.radius)>1e-5 for v in circles):
        raise ValueError('Select a full cylindrical face bounded by two circular ends. Partial and interrupted cylinders are not supported.')
    z=cylinder.axis.copy();z.normalize()
    centers=sorted((v.center for v in circles),key=lambda p:cylinder.origin.vectorTo(p).dotProduct(z))
    origin=centers[1] if reverse else centers[0]
    length=centers[0].distanceTo(centers[1])*10
    if reverse:z.scaleBy(-1)
    reference=core.Vector3D.create(1,0,0) if abs(z.x)<.9 else core.Vector3D.create(0,1,0)
    y=z.crossProduct(reference);y.normalize();x=y.crossProduct(z);x.normalize()
    m=core.Matrix3D.create();m.setWithCoordinateSystem(origin,x,y,z)
    p=face.pointOnFace;offset=cylinder.origin.vectorTo(p)
    axial=z.copy();axial.scaleBy(offset.dotProduct(z));radial=offset.copy();radial.subtract(axial)
    ok,normal=face.evaluator.getNormalAtPoint(p)
    if not ok:raise ValueError('Cannot evaluate cylinder normal.')
    internal=normal.dotProduct(radial)<0
    return face, m, cylinder.radius*20, length, internal

def apply(design,selected,spec,reverse=False):
    face,m,diameter,available,internal=cylinder_frame(selected,reverse)
    if spec.length>available+1e-5:raise ValueError(f'Thread length exceeds selected face ({available:g} mm).')
    if abs(spec.root_diameter-diameter)>1e-5: raise ValueError('Root diameter must match the selected cylinder.')
    target=face.body
    c=target.parentComponent
    if internal and not spec.cut_screw:
        tool=b.threaded(design.rootComponent,spec.cutter(length=spec.length),entry=False)
    else:
        shown=spec.nut_rib() if internal else spec
        if internal:shown=replace(shown,length=spec.length)
        tool=b.sweep_rib(design.rootComponent,shown,inward=spec.cut_screw)
        if spec.left_hand:
            reflection=b.M();reflection.setCell(1,1,-1);b.transform(tool,reflection)
        b.rotate(tool,math.radians(spec.phase))
        b.intersect(tool,b.cylinder(spec.major_diameter/2+1,0,spec.length))
        # Multiple disconnected ribs cannot be unioned until joined to the target.
        tools=[b.rotate(b.manager().copy(tool),2*math.pi*i/spec.starts) for i in range(spec.starts)]
    if internal and not spec.cut_screw: tools=[tool]
    for tool in tools:b.transform(tool,m)
    candidate=b.manager().copy(target)
    for tool in tools:
        (b.cut if internal != spec.cut_screw else b.union)(candidate,tool)
    core.Application.get().log(f'Printable Threads Apply: joining={internal == spec.cut_screw}, original_regions={target.lumps.count}, result_regions={candidate.lumps.count}, solid={candidate.isSolid}, volume_cm3={candidate.volume:g}')
    validate_applied(candidate,target.lumps.count,joining=internal == spec.cut_screw)
    # Native combine preserves the original target body's feature identity.
    # Persist separate tools, then restrict combine to exactly that target.
    base=b.persist(c,tools,'Printable Thread tools')
    tool_bodies=[base.bodies.item(i) for i in range(base.bodies.count)] if base else list(c.bRepBodies)[-len(tools):]
    collection=core.ObjectCollection.create()
    for item in tool_bodies:collection.add(item)
    inp=c.features.combineFeatures.createInput(target,collection)
    inp.operation=fusion.FeatureOperations.CutFeatureOperation if internal != spec.cut_screw else fusion.FeatureOperations.JoinFeatureOperation
    inp.isKeepToolBodies=False
    feature=c.features.combineFeatures.add(inp)
    if not feature:raise ValueError('Fusion could not apply the thread.')
    feature.name='Printable Threads — '+('cut groove' if internal != spec.cut_screw else 'joined rib')
    feature.attributes.add('PrintableThreads.v1','applied_recipe',spec.to_json())
    return feature
