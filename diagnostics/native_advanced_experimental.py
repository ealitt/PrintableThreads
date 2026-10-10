"""Editable native feature construction. Legacy Base Feature recipes are untouched."""
import math
from pathlib import Path
from dataclasses import replace
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

    def component(self,name,matrix=None,parent=None):
        prior_groups=list(self.d.timeline.timelineGroups)
        manager=core.Application.get().importManager
        options=manager.createFusionArchiveImportOptions(str(Path(__file__).resolve().parents[1]/'resources/coil/circular.f3d'))
        imported=manager.importToTarget2(options,parent or self.d.rootComponent)
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

    def point_y(self,sk,point,y):
        dim=sk.sketchDimensions.addDistanceDimension(sk.originPoint,point,fusion.DimensionOrientations.VerticalDimensionOrientation,P(1,1,0))
        dim.parameter.expression=f'abs({y})'

    def circle(self,c,diameter,z='0 mm',name='Circular profile',x='0 mm',y='0 mm'):
        sk=c.sketches.add(self.plane(c,z));sk.name=name
        circle=sk.sketchCurves.sketchCircles.addByCenterRadius(P(self.value(x),self.value(y),0),self.value(diameter)/2)
        if abs(self.value(x))+abs(self.value(y))<1e-9:sk.geometricConstraints.addCoincident(circle.centerSketchPoint,sk.originPoint)
        else:self.point(sk,circle.centerSketchPoint,x,y)
        sk.sketchDimensions.addDiameterDimension(circle,P(1,1,0)).parameter.expression=diameter
        return sk

    def extrude(self,c,sk,length,name):
        inp=c.features.extrudeFeatures.createInput(sk.profiles.item(0),OP.NewBodyFeatureOperation)
        inp.setOneSideExtent(fusion.DistanceExtentDefinition.create(VI(length)),fusion.ExtentDirections.PositiveExtentDirection)
        feature=c.features.extrudeFeatures.add(inp);feature.name=name;sk.isVisible=False
        return feature.bodies.item(0)

    def cylinder(self,c,diameter,length,z='0 mm',name='Cylinder'):
        return self.extrude(c,self.circle(c,diameter,z,name+' profile'),length,name)

    def combine(self,c,target,tools,operation,name):
        target_component=(target.nativeObject or target).parentComponent
        feature_component=getattr(self,'combine_owner',None) or c
        inp=feature_component.features.combineFeatures.createInput(target,collection(tools));inp.operation=operation;inp.isKeepToolBodies=name in ('Join nut rib','Cut thread','Join screw rib','Apply printable thread')
        feature=feature_component.features.combineFeatures.add(inp);feature.name=name
        target=next((body.nativeObject or body for body in feature.bodies if (body.nativeObject or body).parentComponent==target_component and any(core.Cylinder.cast(f.geometry) for f in body.faces)),feature.bodies.item(0).nativeObject or feature.bodies.item(0))
        if name in ('Join nut rib','Cut thread','Join screw rib','Apply printable thread'):
            occ=next((o for o in self.occurrences if o.component==c),None)
            axis=getattr(self,'thread_axis',None) or (c.zConstructionAxis.createForAssemblyContext(occ) if occ else c.zConstructionAxis)
            context=getattr(self,'target_context',None)
            pattern_features=feature_component.features.circularPatternFeatures
            if context:feature=feature.createForAssemblyContext(context);axis=axis.createForAssemblyContext(context)
            entities=[feature]
            inp=pattern_features.createInput(collection(entities),axis)
            inp.patternComputeOption=fusion.PatternComputeOptions.IdenticalPatternCompute
            inp.quantity=VI(self.p['starts']);inp.totalAngle=VI('360 deg');inp.isSymmetric=False
            global _pattern_info
            _pattern_info={'parent':feature.parentComponent.name,'faces':[(f.geometry.objectType,f.body.parentComponent.name) for f in feature.faces],'bodies':[(f.parentComponent.name,f.volume,[v.geometry.objectType for v in f.faces]) for f in feature.bodies],'target':(target.volume,[f.geometry.objectType for f in target.faces])}
            pattern=pattern_features.add(inp);pattern.name='Printable thread starts'
            result=target.nativeObject or target
            for tool in tools:
                owner=tool.nativeObject or tool
                owner.parentComponent.features.removeFeatures.add(owner).name='Consume thread tool'
            return result
        return feature.bodies.item(0)

    def rib(self,c,length,inward=False,offset=0):
        if self.s.section=='Circular':return self.coil_rib(c,length,offset)
        p=self.p;r=f'{p["diameter"]}/2';h=p['height'];lead=p['lead']
        occ=next(o for o in self.occurrences if o.component==c)
        other,guidec=self.component('Helix guide',occ.transform2.copy())
        travel=f'({length})+2*{p["overshoot"]}*{lead}'
        rails=(f'({r})+0.08 mm',f'({r})-({h})') if inward else (f'({r})-0.08 mm',f'({r})+({h})')
        edges=[];guides=[]
        for owner,radius,context in ((c,rails[0],occ),(guidec,rails[1],other)):
            coil=owner.features.coilFeatures.item(0);coil.name='Native helix guide'
            params={item.role:item for item in owner.modelParameters if item.createdBy==coil}
            params['Revolutions'].expression='1'
            params['Diameter'].expression=f'2*({radius})-0.02 mm'
            params['SectionSize'].expression='0.02 mm'
            params['Height'].expression=travel
            params['Revolutions'].expression=f'({travel})/{lead}'
            guide=coil.bodies.item(0);guides.append((owner,guide))
            edge=next(e for e in guide.edges if core.NurbsCurve3D.cast(e.geometry))
            edges.append(edge.createForAssemblyContext(context))
        section=c.sketches.add(c.xZConstructionPlane);section.name='Thread section'
        sign=1 if section.modelToSketchSpace(P(0,0,1)).y>0 else -1
        def pt(radius,z):return section.modelToSketchSpace(P(radius,0,z))
        self.trapezoid(section,r,h,'0 mm',sign,inward,pt,offset)
        paths=[fusion.Path.create(e,fusion.ChainedCurveOptions.noChainedCurves) for e in edges]
        inp=c.features.sweepFeatures.createInput(section.profiles.item(0),paths[0],OP.NewBodyFeatureOperation)
        inp.creationOccurrence=occ;inp.guideRail=paths[1]
        inp.profileScaling=fusion.SweepProfileScalingOptions.SweepProfileNoScalingOption
        sweep=c.features.sweepFeatures.add(inp);sweep.name='Rounded thread sweep';body=sweep.bodies.item(0)
        if offset:
            faces=[face.createForAssemblyContext(occ) for face in body.faces if not core.Plane.cast(face.geometry)]
            feature=c.features.offsetFacesFeatures.add(c.features.offsetFacesFeatures.createInput(faces,VI(f'{offset}*{p["tolerance"]}')))
            feature.name='Uniform normal thread clearance';body=feature.bodies.item(0).nativeObject or feature.bodies.item(0)
        for owner,guide in guides:owner.features.removeFeatures.add(guide).name='Remove helix guide'
        section.isVisible=False
        if self.s.left_hand:
            inp=c.features.mirrorFeatures.createInput(collection([body]),c.xZConstructionPlane.createForAssemblyContext(occ))
            feature=c.features.mirrorFeatures.add(inp);feature.name='Left-hand thread'
            reflected=next(item for item in feature.bodies if item!=body)
            c.features.removeFeatures.add(body).name='Remove right-hand reference';body=reflected
        inp=c.features.moveFeatures.createInput2(collection([body]))
        inp.defineAsTranslateXYZ(VI('0 mm'),VI('0 mm'),VI(f'-{p["overshoot"]}*{lead}'),False)
        body=c.features.moveFeatures.add(inp).bodies.item(0)
        trim=self.cylinder(c,f'{p["diameter"]}+2*{h}+2 mm',length,name='Flush thread end envelope')
        body=self.combine(c,body,[trim],OP.IntersectFeatureOperation,'Trim both thread ends flush')
        inp=c.features.moveFeatures.createInput2(collection([body]));inp.defineAsRotate(c.zConstructionAxis.createForAssemblyContext(occ),VI(p['phase']))
        move=c.features.moveFeatures.add(inp);move.name='Thread phase rotation';body=move.bodies.item(0)
        return [body]

    def coil_rib(self,c,length,offset):
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
        trim=self.cylinder(c,f'{p["diameter"]}+2*{p["height"]}+2 mm',length,name='Flush thread end envelope')
        body=self.combine(c,body,[trim],OP.IntersectFeatureOperation,'Trim both thread ends flush')
        inp=c.features.moveFeatures.createInput2(collection([body]));inp.defineAsRotate(c.zConstructionAxis.createForAssemblyContext(occ),VI(p['phase']))
        move=c.features.moveFeatures.add(inp);move.name='Thread phase rotation';body=move.bodies.item(0)
        return [body]

    def trapezoid(self,sk,r,h,z0,sign,inward,pt,offset=0):
        from ..geometry.profile import rounded_trapezoid
        p=self.p;w=p['width'];crest=p['crest'];rad=p['radius']
        if self.s.balanced_profile:w=f'1.5*({h})';crest=f'0.5*({h})';rad=f'0.15*({h})'
        overlap=f'0.08 mm+3*{p["tolerance"]}' if offset else '0.08 mm'
        overlap_number=.08+3*self.s.radial_clearance if offset else .08
        width_number=self.s.width+(overlap_number-.08)*(self.s.width-self.s.crest)/(self.s.height+.08)
        if offset:w=f'({w})+3*{p["tolerance"]}*(({w})-({crest}))/(({h})+0.08 mm)'
        radius_number=self.s.radius
        if getattr(self,'collapse_corner',False):rad='0 mm';radius_number=0
        if offset<0 and self.s.radius<=self.s.radial_clearance:
            rad='0 mm';radius_number=0
        vertices=[(f'({r})-({overlap})',f'-({w})/2'),(f'({r})+({h})',f'-({crest})/2'),(f'({r})+({h})',f'({crest})/2'),(f'({r})-({overlap})',f'({w})/2')]
        def xy(q):
            x,y=q
            return (f'2*({r})-({x})' if inward else x),f'{sign}*(({y})+({z0}))'
        points=[]
        for vertex in vertices:
            x,y=xy(vertex);point=sk.sketchPoints.add(P(self.value(x),self.value(y),0))
            if len(points)==2:
                sk.geometricConstraints.addVerticalPoints(points[1],point)
                self.point_y(sk,point,y)
            elif len(points)==3:
                sk.geometricConstraints.addVerticalPoints(points[0],point)
                self.point_y(sk,point,y)
            else:self.point(sk,point,x,y)
            points.append(point)
        polygon=[]
        for i,point in enumerate(points):
            line=sk.sketchCurves.sketchLines.addByTwoPoints(point,points[(i+1)%4]);line.isConstruction=True;polygon.append(line)
        segments=rounded_trapezoid(self.s.root_diameter/2,self.s.height,width_number,self.s.crest,radius_number,overlap_number)
        if inward:segments=[(segment[0],*((self.s.root_diameter-q[0],q[1]) for q in segment[1:])) for segment in segments]
        arcs=[];endpoints=[]
        for seg in segments:
            if seg[0]!='arc':continue
            prior=sk.geometricConstraints.count
            pts=[pt(q[0]/10,q[1]/10+self.value(z0)) for q in seg[1:]]
            arc=sk.sketchCurves.sketchArcs.addByThreePoints(*pts)
            for i in range(sk.geometricConstraints.count-1,prior-1,-1):sk.geometricConstraints.item(i).deleteMe()
            a,z=arc.startSketchPoint,arc.endSketchPoint
            if a.geometry.distanceTo(pts[-1])<a.geometry.distanceTo(pts[0]):a,z=z,a
            arcs.append(arc);endpoints.append((a,z))
        if len(arcs)==4:
            lines=[]
            for i,(a,z) in enumerate(endpoints):
                line=sk.sketchCurves.sketchLines.addByTwoPoints(z,endpoints[(i+1)%4][0]);lines.append(line)
                sk.geometricConstraints.addCollinear(line,polygon[i])
            for i,arc in enumerate(arcs):
                sk.geometricConstraints.addTangent(arc,lines[i-1]);sk.geometricConstraints.addTangent(arc,lines[i])
                sk.sketchDimensions.addRadialDimension(arc,P(1,1,0)).parameter.expression=f'min({rad};({overlap})/3)' if i in (0,3) else rad
        else:
            for i,point in enumerate(points):
                sk.sketchCurves.sketchLines.addByTwoPoints(point,points[(i+1)%4])
        sk.isComputeDeferred=False

    def taper(self,c,body,length):
        p=self.p
        major=p['diameter'] if self.s.cut_screw else f'{p["diameter"]}+2*{p["height"]}'
        lower=self.cylinder(c,f'({major})+0.02 mm',f'{length}-{p["entry"]}',name='Entry taper envelope base')
        start=self.circle(c,f'({major})+0.02 mm',f'{length}-{p["entry"]}','Entry taper start')
        end=self.circle(c,f'{p["diameter"]}-0.2 mm',length,'Entry taper end')
        inp=c.features.loftFeatures.createInput(OP.NewBodyFeatureOperation)
        inp.loftSections.add(start.profiles.item(0));inp.loftSections.add(end.profiles.item(0))
        loft=c.features.loftFeatures.add(inp);loft.name='Screw entry taper'
        envelope=self.combine(c,lower,[loft.bodies.item(0)],OP.JoinFeatureOperation,'Join taper envelope')
        start.isVisible=False;end.isVisible=False
        return self.combine(c,body,[envelope],OP.IntersectFeatureOperation,'Trim screw entry')

    def offset_mating(self,c,body,direction,occ=None):
        faces=[]
        for face in body.faces:
            cylinder=core.Cylinder.cast(face.geometry)
            if core.Plane.cast(face.geometry) or core.NurbsSurface.cast(face.geometry) or cylinder and abs(cylinder.radius-self.s.root_diameter/20)<1e-5:
                faces.append(face.createForAssemblyContext(occ) if occ else face)
        inp=c.features.offsetFacesFeatures.createInput(faces,VI(f'{direction}*{self.p["tolerance"]}'))
        feature=c.features.offsetFacesFeatures.add(inp);feature.name='Uniform normal nut mating clearance'
        caps=[face.createForAssemblyContext(occ) if occ else face for face in body.faces if core.Plane.cast(face.geometry)]
        inp=c.features.offsetFacesFeatures.createInput(caps,VI(f'{-direction}*{self.p["tolerance"]}'))
        feature=c.features.offsetFacesFeatures.add(inp);feature.name='Restore flush end faces'
        return body

    def offset_bore(self,c,face):
        if self.s.radial_clearance<=0:return face.body
        # Positive bore face normal points toward the axis; a negative offset
        # removes nut material and grows the bore by tolerance on each side.
        inp=c.features.offsetFacesFeatures.createInput([face],VI('-'+self.p['tolerance']))
        feature=c.features.offsetFacesFeatures.add(inp);feature.name='Uniform normal bore clearance'
        return feature.bodies.item(0).nativeObject or feature.bodies.item(0)

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
        axis_input=c.constructionAxes.createInput();axis_input.setByCircularFace(face)
        builder.thread_axis=c.constructionAxes.add(axis_input);builder.thread_axis.name='Selected cylinder axis';builder.thread_axis.isLightBulbOn=False
        if internal and spec.section=='Circular':target=builder.offset_bore(c,selected)
        if context:target=target.createForAssemblyContext(context)
        # Keep all construction editable in a local frame, and combine into original body.
        root_frame=frame.copy()
        if context:root_frame.transformBy(context.transform2)
        occ,toolc=builder.component('Apply thread construction',root_frame)
        ribs=builder.rib(toolc,builder.p['length'],spec.cut_screw,offset=(-1 if spec.cut_screw else 1) if internal and spec.radial_clearance>0 and spec.section=='Circular' else 0)
        builder.target_context=context
        tools=[body.createForAssemblyContext(occ) for body in ribs]
        global _apply_info
        _apply_info={'frame':frame.asArray(),'root_frame':root_frame.asArray(),'target_bbox':(target.boundingBox.minPoint.asArray(),target.boundingBox.maxPoint.asArray()),'tool_bbox':(tools[0].boundingBox.minPoint.asArray(),tools[0].boundingBox.maxPoint.asArray())}
        target=builder.combine(c,target,tools,OP.JoinFeatureOperation if internal==spec.cut_screw else OP.CutFeatureOperation,'Apply printable thread')
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
                z=f'-{p["floor"]}' if spec.blind else '0 mm'
                body=builder.cylinder(c,p['nut_diameter'],f'({length})'+(f'+{p["floor"]}' if spec.blind else ''),z,'Nut blank')
                bore=builder.cylinder(c,(f'{p["diameter"]}+2*{p["tolerance"]}' if spec.section=='Circular' else p['diameter']),length,name='Nut bore with uniform clearance')
                body=builder.combine(c,body,[bore],OP.CutFeatureOperation,'Cut nominal bore')
            else:body=builder.cylinder(c,p['diameter'],length,name='Nominal screw shaft')
            builder.collapse_corner=female and spec.cut_screw and spec.section!='Circular' and spec.radius<=spec.radial_clearance
            ribs=builder.rib(c,length,spec.cut_screw,offset=(-1 if spec.cut_screw else 1) if female and spec.radial_clearance>0 and spec.section=='Circular' else 0)
            if female and spec.section!='Circular' and not spec.cut_screw:
                cutter=builder.cylinder(c,p['diameter'],length,name='Nominal nut cutter shaft')
                cutter=builder.combine(c,cutter,ribs,OP.JoinFeatureOperation,'Join screw rib')
                if spec.radial_clearance>0:cutter=builder.offset_mating(c,cutter,1,occ)
                body=builder.combine(c,body,[cutter],OP.CutFeatureOperation,'Cut offset nut cavity')
            else:
                body=builder.combine(c,body,ribs,OP.JoinFeatureOperation if female==spec.cut_screw else OP.CutFeatureOperation,'Join nut rib' if female and spec.cut_screw else 'Cut thread' if female or spec.cut_screw else 'Join screw rib')
            if female and spec.section!='Circular' and spec.cut_screw and spec.radial_clearance>0:
                body=builder.offset_mating(c,body,-1,occ)
            if not female and spec.entry>0:body=builder.taper(c,body,length)
            if not female and spec.knob!='None':
                knob=builder.cylinder(c,p['knob_diameter'] if spec.knob=='Cylinder' else f'0.76*{p["knob_diameter"]}',f'{p["knob_height"]}+0.08 mm',f'-{p["knob_height"]}','Knob')
                if spec.knob=='Lobed':
                    for i in range(spec.lobes):
                        a=2*math.pi*i/spec.lobes;r=f'0.375*{p["knob_diameter"]}'
                        sk=builder.circle(c,f'0.25*{p["knob_diameter"]}',f'-{p["knob_height"]}','Knob lobe',f'{math.cos(a):.12g}*({r})',f'{math.sin(a):.12g}*({r})')
                        lobe=builder.extrude(c,sk,f'{p["knob_height"]}+0.08 mm','Extrude knob lobe')
                        knob=builder.combine(c,knob,[lobe],OP.JoinFeatureOperation,'Join knob lobe')
                body=builder.combine(c,body,[knob],OP.JoinFeatureOperation,'Join knob to screw')
            if spec.print_on_plate and ((female and spec.blind) or (not female and spec.knob!='None')):
                inp=c.features.moveFeatures.createInput2(collection([body]))
                inp.defineAsTranslateXYZ(VI('0 mm'),VI('0 mm'),VI(p['floor'] if female else p['knob_height']),False)
                feature=c.features.moveFeatures.add(inp);feature.name='Keep flat face on print plate';body=feature.bodies.item(0)
            body.name='Printable nut' if female else 'Printable screw'
        builder.finish('Printable Threads — Create')
        return made
    except Exception:
        builder.rollback();raise
