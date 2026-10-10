"""Fusion kernel backend: exact helix wires, guided sweeps, temporary booleans.

All returned bodies are transient; only commit() persists final geometry.
No undocumented commands and no designType changes.
"""
import math
from dataclasses import replace
import adsk.core as core
import adsk.fusion as fusion
from .profile import rounded_trapezoid

P=core.Point3D.create
V=core.Vector3D.create
M=core.Matrix3D.create

class GeometryError(RuntimeError): pass

def manager(): return fusion.TemporaryBRepManager.get()

def check(body, label):
    if not body or not body.isSolid or body.lumps.count != 1 or body.volume <= 0:
        raise GeometryError(f'{label} did not produce one closed solid.')
    return body

def boolean(a,b,operation,label):
    if not manager().booleanOperation(a,b,operation): raise GeometryError(label+' failed in Fusion.')
    return a

def union(a,b): return boolean(a,b,fusion.BooleanTypes.UnionBooleanType,'Union')
def cut(a,b): return boolean(a,b,fusion.BooleanTypes.DifferenceBooleanType,'Cut')
def intersect(a,b): return boolean(a,b,fusion.BooleanTypes.IntersectionBooleanType,'Trim')

def cylinder(radius,z0,z1,x=0,y=0,r1=None):
    b=manager().createCylinderOrCone(P(x/10,y/10,z0/10),radius/10,
                                   P(x/10,y/10,z1/10),(radius if r1 is None else r1)/10)
    if not b: raise GeometryError('Cylinder/cone creation failed.')
    return b

def transform(body,matrix):
    if not manager().transform(body,matrix): raise GeometryError('Body transform failed.')
    return body

def move(body,x=0,y=0,z=0):
    m=M(); m.translation=V(x/10,y/10,z/10); return transform(body,m)

def rotate(body,angle):
    m=M(); m.setToRotation(angle,V(0,0,1),P(0,0,0)); return transform(body,m)

def persist(component, bodies, name):
    design=fusion.Design.cast(core.Application.get().activeProduct)
    if design.designType == fusion.DesignTypes.ParametricDesignType:
        base=component.features.baseFeatures.add(); base.name=name
        if not base.startEdit(): raise GeometryError('Cannot edit base feature.')
        try:
            for body in bodies:
                if not component.bRepBodies.add(body,base): raise GeometryError('Cannot persist BRep body.')
        finally: base.finishEdit()
        return base
    for body in bodies:
        if not component.bRepBodies.add(body): raise GeometryError('Cannot persist BRep body.')
    return None

def sweep_rib(root,spec,inward=False):
    """Scratch component is deleted even on failure; returned BRep is independent."""
    scratch=root.occurrences.addNewComponent(M()); c=scratch.component
    c.name='Printable Threads construction (temporary)'
    try:
        r=spec.root_diameter/2
        # The smallest whole-turn overshoot keeps the z=0 phase invariant while
        # avoiding two unnecessary turns at each end in the common case.
        overshoot=max(1,math.ceil((spec.width/2+spec.radius+.1)/spec.lead))
        z0=-overshoot*spec.lead
        turns=spec.length/spec.lead+2*overshoot
        paths=[]
        for radius in ((r-spec.height,r+spec.height) if spec.section=='Circular' else (r+.08,r-spec.height) if inward else (r-.08,r+spec.height)):
            wire=manager().createHelixWire(P(0,0,0),V(0,0,1),P(radius/10,0,z0/10),spec.lead/10,turns,0)
            if not wire: raise GeometryError('Helix wire creation failed.')
            paths.append(wire)
        base=persist(c,paths,'Helix rails')
        wires=base.bodies if base else c.bRepBodies
        sk=c.sketches.add(c.xZConstructionPlane)
        def pt(t): return sk.modelToSketchSpace(P(t[0]/10,0,(t[1]+z0)/10))
        if spec.section=='Circular':
            # Native circle for nominal sections, ellipse for axial fit allowance.
            # Nominal section is circular; only the female cutter widens axially.
            if math.isclose(spec.width/2,spec.height,abs_tol=1e-9):
                sk.sketchCurves.sketchCircles.addByCenterRadius(pt((r,0)),spec.height/10)
            else:
                if spec.width/2>=spec.height:
                    sk.sketchCurves.sketchEllipses.add(pt((r,0)),pt((r,spec.width/2)),pt((r+spec.height,0)))
                else:
                    sk.sketchCurves.sketchEllipses.add(pt((r,0)),pt((r+spec.height,0)),pt((r,spec.width/2)))
        else:
            segments=rounded_trapezoid(r,spec.height,spec.width,spec.crest,spec.radius)
            if inward:segments=[(segment[0],*((2*r-p[0],p[1]) for p in segment[1:])) for segment in segments]
            for segment in segments:
                if segment[0]=='line': sk.sketchCurves.sketchLines.addByTwoPoints(pt(segment[1]),pt(segment[2]))
                else: sk.sketchCurves.sketchArcs.addByThreePoints(pt(segment[1]),pt(segment[2]),pt(segment[3]))
        if sk.profiles.count != 1: raise GeometryError('Rounded section is not one closed profile.')
        path=fusion.Path.create(wires.item(0).edges.item(0).createForAssemblyContext(scratch),fusion.ChainedCurveOptions.noChainedCurves)
        rail=fusion.Path.create(wires.item(1).edges.item(0).createForAssemblyContext(scratch),fusion.ChainedCurveOptions.noChainedCurves)
        inp=c.features.sweepFeatures.createInput(sk.profiles.item(0),path,fusion.FeatureOperations.NewBodyFeatureOperation)
        inp.creationOccurrence=scratch
        inp.guideRail=rail
        inp.profileScaling=fusion.SweepProfileScalingOptions.SweepProfileNoScalingOption
        sweep=c.features.sweepFeatures.add(inp)
        if not sweep or sweep.bodies.count != 1: raise GeometryError('Guided sweep failed.')
        return check(manager().copy(sweep.bodies.item(0)),'Thread rib')
    finally:
        if scratch.isValid: scratch.deleteMe()

def threaded(root,spec,entry=True):
    rib=sweep_rib(root,spec,inward=spec.cut_screw)
    if spec.left_hand:
        m=M(); m.setCell(1,1,-1); transform(rib,m)
    rotate(rib,math.radians(spec.phase))
    result=cylinder(spec.root_diameter/2,0,spec.length)
    clip=cylinder(spec.major_diameter/2+1,0,spec.length)
    intersect(rib,clip)
    for i in range(spec.starts):
        rotated=rib if i==0 else manager().copy(rib)
        if i:rotate(rotated,2*math.pi*i/spec.starts)
        (cut if spec.cut_screw else union)(result,rotated)
    if entry and spec.entry>0:
        envelope=cylinder(spec.major_diameter/2+.01,0,spec.length-spec.entry)
        union(envelope,cylinder(spec.major_diameter/2+.01,spec.length-spec.entry,spec.length,
                                r1=spec.root_diameter/2-.1))
        intersect(result,envelope)
    return check(result,'Threaded shaft')

def screw(root,spec):
    body=threaded(root,spec)
    if spec.knob!='None':
        radius=spec.knob_diameter/2
        if spec.knob=='Cylinder': knob=cylinder(radius,-spec.knob_height,.08)
        else:
            lobe_radius=radius*.25
            centers=radius-lobe_radius
            knob=cylinder(radius*.76,-spec.knob_height,.08)
            for i in range(spec.lobes):
                a=i*2*math.pi/spec.lobes
                union(knob,cylinder(lobe_radius,-spec.knob_height,.08,centers*math.cos(a),centers*math.sin(a)))
        union(body,knob)
    if spec.print_on_plate and spec.knob!='None':move(body,z=spec.knob_height)
    return check(body,'Screw')

def female(root,spec):
    body=cylinder(spec.female_diameter/2,-spec.floor if spec.blind else 0,spec.engagement)
    if spec.cut_screw:
        cut(body,cylinder(spec.root_diameter/2+spec.radial_clearance,0,spec.engagement))
        rib_spec=spec.nut_rib();rib=sweep_rib(root,rib_spec,inward=True)
        if spec.left_hand:
            reflection=M();reflection.setCell(1,1,-1);transform(rib,reflection)
        rotate(rib,math.radians(spec.phase))
        intersect(rib,cylinder(spec.female_diameter/2,0,spec.engagement))
        for i in range(spec.starts):
            part=manager().copy(rib)
            rotate(part,2*math.pi*i/spec.starts);union(body,part)
    else:
        cutter=threaded(root,spec.cutter(),entry=False)
        cut(body,cutter)
    # Nut ribs and grooves terminate on the two planar end faces. Entry
    # easing belongs to the screw; on an inward rib it recessed the whole end.
    intersect(body,cylinder(spec.female_diameter/2,-spec.floor if spec.blind else 0,spec.engagement))
    if spec.print_on_plate and spec.blind:move(body,z=spec.floor)
    return check(body,'Female member')
