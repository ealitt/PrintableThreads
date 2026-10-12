"""Cylindrical-face placement in the owning component's coordinates."""
import math
from dataclasses import replace
import adsk.core as core
import adsk.fusion as fusion
from ..geometry import backend as b
from ..model.solid import validate_applied

def selected_faces(selected):
    return list(selected) if isinstance(selected,(tuple,list)) else [selected]

def cylinder_frame(selected,reverse=False):
    selected=selected_faces(selected)
    faces=selected
    face=faces[0];surface=core.Cylinder.cast(face.geometry) or core.Cone.cast(face.geometry)
    if not surface or not face.body.isSolid:
        raise ValueError('Select cylindrical or circular drafted faces on a solid body.')
    z=surface.axis.copy();z.normalize()
    points=[];intervals=[];internal=None
    for item,f in zip(selected,faces):
        other=core.Cylinder.cast(f.geometry) or core.Cone.cast(f.geometry)
        if not other:raise ValueError('Every selected face must be cylindrical or circular drafted.')
        axis=other.axis.copy();axis.normalize()
        delta=surface.origin.vectorTo(other.origin);cross=delta.crossProduct(z)
        if abs(abs(axis.dotProduct(z))-1)>1e-7 or cross.length>1e-5:
            raise ValueError('Selected faces must share one circular axis.')
        if core.Cylinder.cast(other) and core.Cylinder.cast(surface) and abs(other.radius-surface.radius)>1e-5:
            raise ValueError('Selected cylindrical faces must have the same diameter.')
        p=f.pointOnFace;offset=surface.origin.vectorTo(p)
        axial=z.copy();axial.scaleBy(offset.dotProduct(z));radial=offset.copy();radial.subtract(axial)
        ok,normal=f.evaluator.getNormalAtPoint(p)
        if not ok:raise ValueError('Cannot evaluate the selected face normal.')
        inward=normal.dotProduct(radial)<0
        if internal is not None and inward!=internal:raise ValueError('Cannot mix bore and outside faces.')
        internal=inward
        face_points=[]
        for edge in f.edges:
            evaluator=edge.evaluator
            ok,a,bound=evaluator.getParameterExtents()
            if not ok:raise ValueError('Cannot evaluate the selected face boundary.')
            ok,samples=evaluator.getStrokes(a,bound,1e-5)
            if not ok:raise ValueError('Cannot measure the selected face boundary.')
            face_points.extend(samples)
        points.extend(face_points)
        axial_values=[surface.origin.vectorTo(p).dotProduct(z) for p in face_points]
        intervals.append((min(axial_values),max(axial_values)))
    if not points:raise ValueError('Selected faces have no measurable boundaries.')
    projections=[surface.origin.vectorTo(p).dotProduct(z) for p in points]
    low,high=min(projections),max(projections)
    if high-low<1e-6:raise ValueError('Selected faces have no axial length.')
    # Verify all faces belong to the same rotational surface, including cones.
    radii=[]
    for p,t in zip(points,projections):
        delta=surface.origin.vectorTo(p);axial=z.copy();axial.scaleBy(t);delta.subtract(axial)
        radii.append(delta.length)
    if core.Cylinder.cast(surface):
        radius=surface.radius
        if any(abs(r-radius)>2e-5 for r in radii):raise ValueError('Selected faces do not share one cylindrical surface.')
    else:
        # Constant-diameter envelope at the widest outside / narrowest bore end.
        # This makes a straight mating thread on a drafted mold, not a tapered fastener.
        lo=min(zip(projections,radii));hi=max(zip(projections,radii))
        slope=(hi[1]-lo[1])/(hi[0]-lo[0])
        if any(abs(r-(lo[1]+slope*(t-lo[0])))>2e-5 for t,r in zip(projections,radii)):
            raise ValueError('Selected drafted faces must share the same taper and circular surface.')
        radius=min(radii) if internal else max(radii)
        if max(radii)-min(radii)>=radius*.5:
            raise ValueError('Draft is too large for a straight reference thread.')
    origin=surface.origin.copy();shift=z.copy();shift.scaleBy(high if reverse else low);origin.translateBy(shift)
    if reverse:z.scaleBy(-1)
    reference=core.Vector3D.create(1,0,0) if abs(z.x)<.9 else core.Vector3D.create(0,1,0)
    y=z.crossProduct(reference);y.normalize();x=y.crossProduct(z);x.normalize()
    m=core.Matrix3D.create();m.setWithCoordinateSystem(origin,x,y,z)
    # Public frame stays in the first owner's coordinates for existing callers.
    context=selected[0].assemblyContext
    if context:
        inverse=context.transform2.copy();inverse.invert();m.transformBy(inverse)
    return face.nativeObject or face,m,radius*20,(high-low)*10,internal

def target_groups(selected):
    groups=[]
    for face in selected_faces(selected):
        native=face.nativeObject or face
        context=face.assemblyContext
        key=(native.body.entityToken,context.fullPathName if context else '')
        group=next((g for k,g in groups if k==key),None)
        if group is None:group=[];groups.append((key,group))
        group.append(face)
    return [g for _,g in groups]

def shared_frames(selected,reverse=False):
    face,local,diameter,available,internal=cylinder_frame(selected,reverse)
    world=local.copy();context=selected_faces(selected)[0].assemblyContext
    if context:world.transformBy(context.transform2)
    result=[]
    for group in target_groups(selected):
        frame=world.copy();context=group[0].assemblyContext
        if context:
            inverse=context.transform2.copy();inverse.invert();frame.transformBy(inverse)
        result.append((group,(frame,diameter,available,internal)))
    return result

def overlaps_interval(group,shared,length):
    inverse=shared[0].copy();inverse.invert();heights=[]
    for item in group:
        face=item.nativeObject or item
        for edge in face.edges:
            ok,a,end=edge.evaluator.getParameterExtents()
            if not ok:raise ValueError('Cannot measure thread interval.')
            ok,points=edge.evaluator.getStrokes(a,end,1e-5)
            if not ok:raise ValueError('Cannot measure thread interval.')
            for point in points:
                point.transformBy(inverse);heights.append(point.z*10)
    return min(max(heights),length)-max(min(heights),0)>1e-5

def validate_draft(selected,spec):
    radii=[]
    for selected_face in selected_faces(selected):
        face=selected_face.nativeObject or selected_face
        cone=core.Cone.cast(face.geometry)
        if not cone:continue
        axis=cone.axis.copy();axis.normalize()
        for edge in face.edges:
            ok,a,bound=edge.evaluator.getParameterExtents()
            if not ok:raise ValueError('Cannot measure draft.')
            ok,points=edge.evaluator.getStrokes(a,bound,1e-5)
            if not ok:raise ValueError('Cannot measure draft.')
            for p in points:
                delta=cone.origin.vectorTo(p);along=axis.copy();along.scaleBy(delta.dotProduct(axis));delta.subtract(along)
                radii.append(delta.length*10)
    if radii:
        variation=max(radii)-min(radii)
        if spec.height<=variation+spec.radial_clearance+1e-5:
            raise ValueError(f'Section size cannot reach the full draft ({variation:g} mm radius change). Increase section radial reach beyond {variation+spec.radial_clearance:g} mm or reduce draft/tolerance.')

def expanded_reference(design,selected,distance):
    """Offset only selected rotational faces; planar cut boundaries stay fixed.

    The reference exists only in a scratch component and is always removed.
    """
    selected=selected_faces(selected);face=selected[0].nativeObject or selected[0]
    indices=[i for i,f in enumerate(face.body.faces) if any(f==(item.nativeObject or item) for item in selected)]
    scratch,c,start=b.scratch_component(design.rootComponent)
    try:
        base=b.persist(c,[b.manager().copy(face.body)],'Temporary thread boundary reference')
        body=base.bodies.item(0)
        faces=[body.faces.item(i).createForAssemblyContext(scratch) if scratch else body.faces.item(i) for i in indices]
        inp=c.features.offsetFacesFeatures.createInput(faces,core.ValueInput.createByReal(distance/10))
        feature=c.features.offsetFacesFeatures.add(inp)
        return b.manager().copy(feature.bodies.item(0).nativeObject or feature.bodies.item(0))
    finally:
        b.remove_scratch(scratch,start)

def preview_tool(design,spec,internal):
    # Same nominal helix and boolean as Apply. Native normal offsets and optional
    # edge chamfers are finishing operations, so remain excluded from this preview.
    shown=spec
    if internal:
        shown=replace(spec,root_diameter=spec.root_diameter+2*spec.radial_clearance)
        if spec.section!='Circular':shown=spec.nut_rib() if spec.cut_screw else spec.cutter(length=spec.length)
        elif spec.radial_clearance:
            size=spec.thread_size+(-2 if spec.cut_screw else 2)*spec.radial_clearance
            shown=shown.with_circular_section(size)
    tool=b.sweep_rib(design.rootComponent,shown,inward=spec.cut_screw)
    if spec.left_hand:
        reflection=b.M();reflection.setCell(1,1,-1);b.transform(tool,reflection)
    b.rotate(tool,math.radians(spec.phase))
    b.intersect(tool,b.cylinder(shown.root_diameter/2+shown.height+1,0,spec.length))
    return tool

def preview_body(design,selected,spec,reverse=False,shared=None,prepared=None):
    face=selected_faces(selected)[0].nativeObject or selected_faces(selected)[0]
    frame,diameter,available,internal=shared or cylinder_frame(selected,reverse)[1:]
    if spec.length>available+1e-5:raise ValueError(f'Thread length exceeds the {available:g} mm axial span.')
    validate_draft(selected,spec)
    if not overlaps_interval(selected_faces(selected),(frame,diameter,available,internal),spec.length):return b.manager().copy(face.body)
    tool=b.manager().copy(prepared) if prepared is not None else preview_tool(design,spec,internal)
    candidate=b.manager().copy(face.body)
    joining=internal==spec.cut_screw
    if internal and spec.radial_clearance:
        # Negative normal offset grows a bore, including its draft.
        candidate=expanded_reference(design,selected,-spec.radial_clearance)
    envelope=expanded_reference(design,selected,spec.height) if joining else None
    for i in range(spec.starts):
        rib=b.rotate(b.manager().copy(tool),2*math.pi*i/spec.starts);b.transform(rib,frame)
        if joining:b.intersect(rib,b.manager().copy(envelope))
        (b.union if joining else b.cut)(candidate,rib)
    return validate_applied(candidate,face.body.lumps.count,joining)

def apply(design,selected,spec,reverse=False,shared=None):
    if shared is None and len(target_groups(selected))>1:
        plans=[(group,frame) for group,frame in shared_frames(selected,reverse) if overlaps_interval(group,frame,spec.length)]
        start=design.timeline.markerPosition
        try:return [apply(design,group,spec,reverse,frame) for group,frame in plans]
        except Exception:
            b.remove_scratch(None,start)
            raise
    face=selected_faces(selected)[0].nativeObject or selected_faces(selected)[0]
    m,diameter,available,internal=shared or cylinder_frame(selected,reverse)[1:]
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
    envelope=expanded_reference(design,selected,spec.height) if internal==spec.cut_screw else None
    for tool in tools:
        b.transform(tool,m)
        if envelope:b.intersect(tool,b.manager().copy(envelope))
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
