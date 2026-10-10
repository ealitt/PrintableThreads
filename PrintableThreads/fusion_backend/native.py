"""Editable native feature construction. Legacy Base Feature recipes are untouched."""
import math
from pathlib import Path
import adsk.core as core
import adsk.fusion as fusion
from .selection import cylinder_frame
from ..geometry import backend as b

P=core.Point3D.create
VI=core.ValueInput.createByString
OP=fusion.FeatureOperations

def collection(items):
    result=core.ObjectCollection.create()
    for item in items:result.add(item)
    return result

class Builder:
    def __init__(self,design,spec,expressions=None):
        if design.designType!=fusion.DesignTypes.ParametricDesignType:
            raise ValueError('Enable Capture Design History to create editable printable threads.')
        self.d=design;self.s=spec;self.start=design.timeline.markerPosition
        self.params=[];self.occurrences=[];self.expr=expressions or {}
        n=1
        while design.userParameters.itemByName(f'PT{n}_diameter'):n+=1
        self.prefix=f'PT{n}_';self.p={}
        values={'diameter':('root_diameter',spec.root_diameter),'pitch':('pitch',spec.pitch),
                'section':('thread_size',spec.thread_size),'length':('length',spec.length),
                'tolerance':('radial_clearance',spec.radial_clearance),'nut_diameter':('female_diameter',spec.female_diameter),
                'engagement':('engagement',spec.engagement),'floor':('floor',spec.floor),
                'knob_diameter':('knob_diameter',spec.knob_diameter),'knob_height':('knob_height',spec.knob_height),
                'entry':('entry',spec.entry),'width':('width',spec.width),'crest':('crest',spec.crest),'radius':('radius',spec.radius)}
        for key,(input_key,value) in values.items():self.parameter(key,self.expr.get(input_key,f'{value:.12g} mm'),'mm')
        self.parameter('edge_chamfer',f'min(0.2 mm;min({self.p["section"]}/10;({self.p["pitch"]}-{self.p["section"]})/4))','mm')
        self.parameter('starts',str(spec.starts),'')
        self.parameter('phase',f'{spec.phase:.12g} deg','deg')
        self.parameter('lead',f'{self.p["pitch"]} * {self.p["starts"]}','mm')
        self.parameter('height',self.p['section']+'/2' if spec.section=='Circular' else self.p['section'],'mm')
        overshoot=max(1,math.ceil((spec.width/2+spec.radius+.1)/spec.lead))
        self.parameter('overshoot',str(overshoot),'')

    def parameter(self,key,expression,unit):
        name=self.prefix+key
        item=self.d.userParameters.add(name,VI(expression),unit,'Printable Threads: '+key.replace('_',' '))
        self.params.append(item);self.p[key]=name
        return name

    def value(self,expression):return self.d.unitsManager.evaluateExpression(expression,'mm')

    def component(self,name,matrix=None):
        prior_groups=list(self.d.timeline.timelineGroups)
        manager=core.Application.get().importManager
        options=manager.createFusionArchiveImportOptions(str(Path(__file__).resolve().parents[1]/'resources/coil/circular.f3d'))
        imported=manager.importToTarget2(options,self.d.rootComponent)
        occ=next(fusion.Occurrence.cast(item) for item in imported if fusion.Occurrence.cast(item))
        for group in list(self.d.timeline.timelineGroups):
            if group not in prior_groups:group.deleteMe(False)
        if matrix:
            occ.transform2=matrix
            if self.d.snapshots.hasPendingSnapshot:self.d.snapshots.add()
        self.occurrences.append(occ);occ.component.name=self.prefix+name
        return occ,occ.component

    def plane(self,c,z):
        if abs(self.value(z))<1e-10 and z=='0 mm':return c.xYConstructionPlane
        inp=c.constructionPlanes.createInput();inp.setByOffset(c.xYConstructionPlane,VI(z))
        plane=c.constructionPlanes.add(inp);plane.name='Thread axial datum';plane.isLightBulbOn=False
        return plane

    def point(self,sk,point,x,y):
        """Drive each sketch coordinate with an expression; zero uses alignment."""
        for expression,orientation,constraint in ((x,fusion.DimensionOrientations.HorizontalDimensionOrientation,'addVerticalPoints'),(y,fusion.DimensionOrientations.VerticalDimensionOrientation,'addHorizontalPoints')):
            if abs(self.value(expression))<1e-9:
                getattr(sk.geometricConstraints,constraint)(sk.originPoint,point)
            else:
                dim=sk.sketchDimensions.addDistanceDimension(sk.originPoint,point,orientation,P(1,1,0))
                dim.parameter.expression=f'abs({expression})'

    def circle(self,c,diameter,z='0 mm',name='Circular profile',x='0 mm',y='0 mm'):
        sk=c.sketches.add(self.plane(c,z));sk.name=name
        circle=sk.sketchCurves.sketchCircles.addByCenterRadius(P(self.value(x),self.value(y),0),self.value(diameter)/2)
        if abs(self.value(x))+abs(self.value(y))<1e-9:sk.geometricConstraints.addCoincident(circle.centerSketchPoint,sk.originPoint)
        else:self.point(sk,circle.centerSketchPoint,x,y)
        sk.sketchDimensions.addDiameterDimension(circle,P(1,1,0)).parameter.expression=diameter
        return sk

    def extrude(self,c,sk,length,name,z='0 mm',operation=OP.NewBodyFeatureOperation,profiles=None,target=None):
        inp=c.features.extrudeFeatures.createInput(profiles or sk.profiles.item(0),operation)
        if z!='0 mm':inp.startExtent=fusion.OffsetStartDefinition.create(VI(z))
        if target:inp.participantBodies=[target]
        inp.setOneSideExtent(fusion.DistanceExtentDefinition.create(VI(length)),fusion.ExtentDirections.PositiveExtentDirection)
        feature=c.features.extrudeFeatures.add(inp);feature.name=name;sk.isVisible=False
        return feature.bodies.item(0)

    def cylinder(self,c,diameter,length,z='0 mm',name='Cylinder'):
        return self.extrude(c,self.circle(c,diameter,name=name+' profile'),length,name,z)

    def knob(self,c,shaft):
        """One sketch and one joining extrusion for the union of all grip circles."""
        p=self.p
        sk=self.circle(c,p['knob_diameter'] if self.s.knob=='Cylinder' else f'0.76*{p["knob_diameter"]}',name='Knob profile')
        sk.isComputeDeferred=True
        try:
            if self.s.knob=='Lobed':
                for i in range(self.s.lobes):
                    a=2*math.pi*i/self.s.lobes
                    x=f'{math.cos(a):.12g}*0.375*{p["knob_diameter"]}'
                    y=f'{math.sin(a):.12g}*0.375*{p["knob_diameter"]}'
                    circle=sk.sketchCurves.sketchCircles.addByCenterRadius(P(self.value(x),self.value(y),0),self.value(f'0.25*{p["knob_diameter"]}')/2)
                    self.point(sk,circle.centerSketchPoint,x,y)
                    sk.sketchDimensions.addDiameterDimension(circle,P(1,1,0)).parameter.expression=f'0.25*{p["knob_diameter"]}'
        finally:sk.isComputeDeferred=False
        return self.extrude(c,sk,f'{p["knob_height"]}+0.08 mm','Join knob',f'-{p["knob_height"]}',OP.JoinFeatureOperation,collection(sk.profiles),shaft)

    def nut_blank(self,c,length):
        p=self.p
        if self.s.blind:
            body=self.cylinder(c,p['nut_diameter'],f'({length})+{p["floor"]}',f'-{p["floor"]}','Nut blank')
            bore=self.circle(c,f'{p["diameter"]}+2*{p["tolerance"]}',name='Nut bore profile')
            return self.extrude(c,bore,length,'Cut nut bore',operation=OP.CutFeatureOperation,target=body)
        sk=self.circle(c,p['nut_diameter'],name='Nut annulus profile')
        circle=sk.sketchCurves.sketchCircles.addByCenterRadius(P(0,0,0),self.value(f'{p["diameter"]}+2*{p["tolerance"]}')/2)
        sk.geometricConstraints.addCoincident(circle.centerSketchPoint,sk.originPoint)
        sk.sketchDimensions.addDiameterDimension(circle,P(1,1,0)).parameter.expression=f'{p["diameter"]}+2*{p["tolerance"]}'
        annulus=next(profile for profile in sk.profiles if profile.profileLoops.count==2)
        return self.extrude(c,sk,length,'Extrude nut annulus',profiles=annulus)

    def combine(self,c,target,tools,operation,name):
        inp=c.features.combineFeatures.createInput(target,collection(tools));inp.operation=operation;inp.isKeepToolBodies=False
        feature=c.features.combineFeatures.add(inp);feature.name=name
        return feature.bodies.item(0).nativeObject or feature.bodies.item(0)

    def rib(self,c,length,inward=False,offset=0,trim=True):
        if self.s.section!='Circular':raise ValueError('Native construction currently supports Circular / On Center; use the preserved legacy profile path for Balanced / Custom.')
        return self.coil_rib(c,length,offset,trim)

    def coil_rib(self,c,length,offset,trim):
        """Native Coil history imported from a minimal, original F3D template."""
        p=self.p;occ=next(o for o in self.occurrences if o.component==c)
        coil=c.features.coilFeatures.item(0);coil.name='On-center circular thread Coil'
        params={item.role:item for item in c.modelParameters if item.createdBy==coil}
        # Keep the intermediate Coil from self-intersecting while rebinding it.
        params['Revolutions'].expression='1'
        params['Diameter'].expression=p['diameter']
        params['SectionSize'].expression=p['section']
        params['Height'].expression=f'({length})+2*{p["overshoot"]}*{p["lead"]}'
        params['Revolutions'].expression=f'(({length})+2*{p["overshoot"]}*{p["lead"]})/{p["lead"]}'
        body=coil.bodies.item(0)
        if self.s.left_hand:
            inp=c.features.mirrorFeatures.createInput(collection([body]),c.xZConstructionPlane.createForAssemblyContext(occ))
            mirror=c.features.mirrorFeatures.add(inp);mirror.name='Left-hand thread'
            reflected=next(item for item in mirror.bodies if item!=body)
            c.features.removeFeatures.add(body).name='Remove right-hand reference'
            body=reflected
        if offset:
            faces=[face.createForAssemblyContext(occ) for face in body.faces if not core.Plane.cast(face.geometry)]
            feature=c.features.offsetFacesFeatures.add(c.features.offsetFacesFeatures.createInput(faces,VI(f'{offset}*{p["tolerance"]}')))
            feature.name='Uniform normal thread clearance';body=feature.bodies.item(0).nativeObject or feature.bodies.item(0)
        inp=c.features.moveFeatures.createInput2(collection([body]))
        inp.defineAsTranslateXYZ(VI('0 mm'),VI('0 mm'),VI(f'-{p["overshoot"]}*{p["lead"]}'),False)
        move=c.features.moveFeatures.add(inp);move.name='Extend thread past both ends';body=move.bodies.item(0)
        if trim:
            envelope=self.cylinder(c,f'{p["diameter"]}+2*{p["height"]}+2 mm',length,name='Flush thread end envelope')
            body=self.combine(c,body,[envelope],OP.IntersectFeatureOperation,'Trim both thread ends flush')
        inp=c.features.moveFeatures.createInput2(collection([body]));inp.defineAsRotate(c.zConstructionAxis.createForAssemblyContext(occ),VI(p['phase']))
        move=c.features.moveFeatures.add(inp);move.name='Thread phase rotation';body=move.bodies.item(0)
        # Always retain four tool identities. Rearrange the quarter-turn copies
        # into the requested 1–4 starts; unused copies coincide with an active
        # start. A single native Combine handles the coincident tools. This
        # avoids missing tool references when a pattern quantity is reduced.
        inp=c.features.circularPatternFeatures.createInput(collection([body]),c.zConstructionAxis.createForAssemblyContext(occ))
        inp.quantity=VI('4');inp.totalAngle=VI('360 deg');inp.isSymmetric=False
        pattern=c.features.circularPatternFeatures.add(inp);pattern.name='Printable thread starts'
        bodies=[element.faces[0].body for element in pattern.patternElements]
        for i,copy in enumerate(bodies[1:],1):
            angle=f'{i}*(360 deg/{p["starts"]}-360 deg*max(0;2-{p["starts"]})-90 deg)'
            inp=c.features.moveFeatures.createInput2(collection([copy]))
            inp.defineAsRotate(c.zConstructionAxis.createForAssemblyContext(occ),VI(angle))
            feature=c.features.moveFeatures.add(inp);feature.name=f'Arrange thread start {i+1}'
            bodies[i]=feature.bodies.item(0)
        return bodies

    def taper(self,c,body,length):
        """One annular profile and one drafted cut replace the entry envelope."""
        p=self.p
        major=p['diameter'] if self.s.cut_screw else f'{p["diameter"]}+2*{p["height"]}'
        sk=self.circle(c,f'({major})+2 mm',name='Entry taper profile')
        circle=sk.sketchCurves.sketchCircles.addByCenterRadius(P(0,0,0),self.value(f'({major})+0.02 mm')/2)
        sk.geometricConstraints.addCoincident(circle.centerSketchPoint,sk.originPoint)
        sk.sketchDimensions.addDiameterDimension(circle,P(1,1,0)).parameter.expression=f'({major})+0.02 mm'
        annulus=next(profile for profile in sk.profiles if profile.profileLoops.count==2)
        inp=c.features.extrudeFeatures.createInput(annulus,OP.CutFeatureOperation)
        inp.startExtent=fusion.OffsetStartDefinition.create(VI(f'{length}-{p["entry"]}'))
        inp.setOneSideExtent(fusion.DistanceExtentDefinition.create(VI(p['entry'])),fusion.ExtentDirections.PositiveExtentDirection)
        inp.taperAngle=VI(f'atan((({major})+0.02 mm-({p["diameter"]}-0.2 mm))/(2*{p["entry"]}))')
        inp.participantBodies=[body]
        feature=c.features.extrudeFeatures.add(inp);feature.name='Screw entry taper';sk.isVisible=False
        return feature.bodies.item(0).nativeObject or feature.bodies.item(0)

    def offset_bore(self,c,face):
        if self.s.radial_clearance<=0:return face.body
        # Positive bore face normal points toward the axis; a negative offset
        # removes nut material and grows the bore by tolerance on each side.
        inp=c.features.offsetFacesFeatures.createInput([face],VI('-'+self.p['tolerance']))
        feature=c.features.offsetFacesFeatures.add(inp);feature.name='Uniform normal bore clearance'
        return feature.bodies.item(0).nativeObject or feature.bodies.item(0)

    def chamfer_lands(self,c,body,internal=False,context=None):
        """Bevel the boundaries of cylindrical thread lands.

        Limit the distance by section and inter-turn spacing. Try progressively
        smaller native chamfers for difficult intersections; an optional edge
        finish must never discard a successfully constructed thread.
        """
        native_body=body.nativeObject or body
        radius=(self.s.root_diameter/2+(self.s.radial_clearance if internal else 0))/10
        if abs(self.value(self.p['edge_chamfer']))<1e-8:return body
        faces=[f for f in native_body.faces if core.Cylinder.cast(f.geometry)
               and abs(core.Cylinder.cast(f.geometry).radius-radius)<1e-5]
        if not faces:return body
        context=context or body.assemblyContext
        if not context:
            context=next((o for o in self.occurrences if o.component==c),None)
        for factor in (1,.5,.25,.125):
            feature=None
            try:
                edges={e.entityToken:e for f in faces for e in f.edges}
                chosen=[e.createForAssemblyContext(context) if context else e for e in edges.values()]
                inp=c.features.chamferFeatures.createInput2()
                inp.chamferEdgeSets.addEqualDistanceChamferEdgeSet(collection(chosen),VI(f'{factor}*{self.p["edge_chamfer"]}'),True)
                feature=c.features.chamferFeatures.add(inp)
                if not feature.faces.count:raise ValueError('Chamfer has no resulting faces.')
                if feature.healthState!=fusion.FeatureHealthStates.HealthyFeatureHealthState:
                    raise ValueError(feature.errorOrWarningMessage)
                feature.name='Print edge chamfer'
                # Preserve the original body identity; chamfer modifies it in place.
                return native_body
            except Exception as error:
                core.Application.get().log('Thread chamfer reduced or skipped: '+str(error))
                if feature and feature.isValid:feature.deleteMe()
        return body

    def finish(self,name):
        end=self.d.timeline.markerPosition-1
        if end>self.start:
            group=self.d.timeline.timelineGroups.add(self.start,end);group.name=name;group.isCollapsed=True

    def rollback(self):
        # Delete only this operation's timeline entries, in dependency order.
        end=self.d.timeline.markerPosition
        for i in range(end-1,self.start-1,-1):
            try:self.d.timeline.item(i).entity.deleteMe()
            except Exception:pass
        for occ in reversed(self.occurrences):
            if occ.isValid:
                try:occ.deleteMe()
                except Exception:pass
        for param in reversed(self.params):
            if param.isValid:
                try:param.deleteMe()
                except Exception:pass


def validate_clearance(spec,nut):
    if spec.section!='Circular':raise ValueError('Native profile conversion is unfinished for Balanced / Custom. Their legacy commands remain available.')
    if not nut or spec.section!='Circular':return
    if spec.cut_screw and spec.height<=2*spec.radial_clearance+1e-6:
        raise ValueError('Section size must exceed four times the nut tolerance so the inward rib stays joined to the bore wall.')
    if not spec.cut_screw and spec.thread_size+2*spec.radial_clearance>=spec.pitch-.1:
        raise ValueError('Section size plus twice the nut tolerance must leave at least 0.1 mm between turns. Increase pitch or reduce section size/tolerance.')


def apply(design,selected,spec,reverse=False,expressions=None):
    face,frame,diameter,available,internal=cylinder_frame(selected,reverse)
    if spec.length>available+1e-5:raise ValueError(f'Thread length exceeds selected face ({available:g} mm).')
    if abs(spec.root_diameter-diameter)>1e-5:raise ValueError('Diameter must match the selected cylinder.')
    validate_clearance(spec,internal)
    builder=Builder(design,spec,expressions)
    try:
        context=selected.assemblyContext
        target=face.body;c=target.parentComponent
        if internal and spec.section=='Circular':target=builder.offset_bore(c,selected)
        if context:target=target.createForAssemblyContext(context)
        # Keep all construction editable in a local frame, and combine into original body.
        root_frame=frame.copy()
        if context:root_frame.transformBy(context.transform2)
        occ,toolc=builder.component('Apply thread construction',root_frame)
        ribs=builder.rib(toolc,builder.p['length'],spec.cut_screw,offset=(-1 if spec.cut_screw else 1) if internal and spec.radial_clearance>0 and spec.section=='Circular' else 0)
        tools=[body.createForAssemblyContext(occ) for body in ribs]
        target=builder.combine(c,target,tools,OP.JoinFeatureOperation if internal==spec.cut_screw else OP.CutFeatureOperation,'Apply printable thread')
        target=builder.chamfer_lands(c,target,internal,context)
        b.check(target,'Applied native thread')
        target.attributes.add('PrintableThreads.native','parameters',builder.prefix)
        builder.finish('Printable Threads — Apply nut' if internal else 'Printable Threads — Apply screw')
        return target
    except Exception:
        builder.rollback();raise


def create(design,spec,placement,expressions=None):
    validate_clearance(spec,spec.output!='Screw')
    builder=Builder(design,spec,expressions);p=builder.p;made=[]
    try:
        for female in ([False,True] if spec.output=='Matched pair' else [spec.output=='Female']):
            offset=(max(spec.knob_diameter,spec.major_diameter)+spec.female_diameter)/2+5 if female and spec.output=='Matched pair' else 0
            matrix=placement(offset)
            occ,c=builder.component('Nut' if female else 'Screw',matrix);made.append(occ)
            length=p['engagement'] if female else p['length']
            if female:
                body=builder.nut_blank(c,length)
            else:body=builder.cylinder(c,p['diameter'],length,name='Nominal screw shaft')
            # Cuts are bounded by the new blank; joins and blind floors need a trimmed tool.
            trim=female==spec.cut_screw or (female and spec.blind)
            ribs=builder.rib(c,length,spec.cut_screw,offset=(-1 if spec.cut_screw else 1) if female and spec.radial_clearance>0 else 0,trim=trim)
            body=builder.combine(c,body,ribs,OP.JoinFeatureOperation if female==spec.cut_screw else OP.CutFeatureOperation,'Join nut rib' if female and spec.cut_screw else 'Cut thread' if female or spec.cut_screw else 'Join screw rib')
            body=builder.chamfer_lands(c,body,female)
            if not female and spec.entry>0:body=builder.taper(c,body,length)
            if not female and spec.knob!='None':
                body=builder.knob(c,body)
            if spec.print_on_plate and ((female and spec.blind) or (not female and spec.knob!='None')):
                inp=c.features.moveFeatures.createInput2(collection([body]))
                inp.defineAsTranslateXYZ(VI('0 mm'),VI('0 mm'),VI(p['floor'] if female else p['knob_height']),False)
                feature=c.features.moveFeatures.add(inp);feature.name='Keep flat face on print plate';body=feature.bodies.item(0)
            b.check(body,'Created native thread')
            body.attributes.add('PrintableThreads.native','parameters',builder.prefix)
            body.name='Printable nut' if female else 'Printable screw'
        builder.finish('Printable Threads — Create')
        return made
    except Exception:
        builder.rollback();raise
