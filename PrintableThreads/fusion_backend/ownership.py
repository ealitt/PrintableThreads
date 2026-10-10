import json
import uuid
import adsk.core as core
import adsk.fusion as fusion
from ..model.spec import Spec
from ..geometry import backend as b

GROUP='PrintableThreads.v1'

def commit(root,spec,bodies,expressions=None):
    """bodies: (role, transient BRep, placement matrix). All geometry is ready first."""
    made=[]
    try:
        for role,body,matrix in bodies:
            occ=root.occurrences.addNewComponent(matrix);made.append(occ)
            c=occ.component;c.name=f'PT {role} · {spec.root_diameter:g} / P{spec.pitch:g} / {spec.starts} start'
            base=b.persist(c,[body],'Printable thread — regenerate with add-in')
            c.bRepBodies.item(0).name=c.name
            record={'id':str(uuid.uuid4()),'recipe':json.loads(spec.to_json()),'role':role,
                    'expressions':expressions or {},'base_token':base.entityToken if base else None,
                    'placement':matrix.asArray(),'body_token':c.bRepBodies.item(0).entityToken}
            c.attributes.add(GROUP,'recipe',json.dumps(record))
        design=fusion.Design.cast(core.Application.get().activeProduct)
        # Strict gate: edits are allowed only while this operation remains at timeline end.
        end=design.timeline.count if design.designType==fusion.DesignTypes.ParametricDesignType else None
        for occ in made:
            attr=occ.component.attributes.itemByName(GROUP,'recipe');record=json.loads(attr.value)
            record['timeline_count']=end;attr.value=json.dumps(record)
        return made
    except Exception:
        for occ in reversed(made):
            if occ.isValid: occ.deleteMe()
        raise

def record_for(body):
    native=body.nativeObject or body
    parameter_record=native.attributes.itemByName('PrintableThreads.native','parameters')
    if parameter_record:raise ValueError('This is a native printable thread. Use Modify > Change Parameters and edit '+parameter_record.value+' values, or expand its timeline group and edit the Coil / Offset Faces features.')
    attr=native.parentComponent.attributes.itemByName(GROUP,'recipe')
    if not attr: raise ValueError('Select a body created by Printable Threads. Applied threads cannot be regenerated safely.')
    return native,attr,json.loads(attr.value)

def editable(design,body):
    body,attr,record=record_for(body);c=body.parentComponent
    if not record.get('base_token'): raise ValueError('Regeneration requires a design with history enabled at creation.')
    if design.timeline.count!=record.get('timeline_count') or design.timeline.markerPosition!=design.timeline.count:
        raise ValueError('Regeneration is limited to the latest creation operation, with no later timeline features. Create a new fastener instead.')
    if c.bRepBodies.count!=1 or c.features.count!=1 or c.occurrences.count or c.sketches.count:
        raise ValueError('This component has additional geometry or features; regeneration is blocked.')
    if len(design.rootComponent.allJoints) or len(design.rootComponent.allAsBuiltJoints):
        raise ValueError('Regeneration is blocked in assemblies containing joints. Create a new fastener instead.')
    found=design.findEntityByToken(record['base_token'])
    if len(found)!=1 or not fusion.BaseFeature.cast(found[0]): raise ValueError('Saved base feature is missing or ambiguous.')
    return body,attr,record,found[0]

def regenerate(design,body,spec,expressions=None):
    body,attr,record,base=editable(design,body)
    role=record['role']
    replacement=b.screw(design.rootComponent,spec) if role=='Screw' else b.female(design.rootComponent,spec)
    # Kernel generation and validation finish before the original is touched.
    backup=b.manager().copy(body)
    if not base.startEdit(): raise ValueError('Cannot edit owned base feature.')
    try:
        source=base.bodies.item(0)
        try:
            if not base.updateBody(source,replacement): raise ValueError('Fusion rejected the replacement body.')
        except Exception:
            base.updateBody(source,backup)
            raise
    finally: base.finishEdit()
    record['recipe']=json.loads(spec.to_json());record['expressions']=expressions or {}
    attr.value=json.dumps(record)
    body.parentComponent.name=f'PT {role} · {spec.root_diameter:g} / P{spec.pitch:g} / {spec.starts} start'
    body.name=body.parentComponent.name
