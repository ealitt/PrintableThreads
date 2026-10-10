"""Use Fusion's UI interpreter to exercise the installed command lifecycle."""
import sys,json,traceback,hashlib
from pathlib import Path
from dataclasses import replace
import adsk.core as core,adsk.fusion as fusion
repo=Path('/Users/eammon/Documents/GitHub/PrintableThreads')
installed=Path.home()/'Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/PrintableThreads'
app=core.Application.get()
for module in list(sys.modules.values()):
 if str(getattr(module,'__file__','')).endswith('/PrintableThreads/commands/__init__.py'):
  module.stop()
app.unregisterCustomEvent('PrintableThreads_test_execute')
entry=next(m for m in sys.modules.values() if str(getattr(m,'__file__',''))==str(installed/'PrintableThreads.py'))
exec(compile((installed/'PrintableThreads.py').read_text(),str(installed/'PrintableThreads.py'),'exec'),entry.__dict__)
entry.run({})
commands=entry.commands;native=entry.native;events=commands.events;Spec=entry.spec.Spec
commands.preferences.save=lambda *args:None
probe_documents=globals().setdefault('installed_probe_documents',[])
mode=globals().get('probe_mode','create');internal=globals().get('probe_internal',False);nested=globals().get('probe_nested',False)
commands._probe_document=app.documents.add(core.DocumentTypes.FusionDesignDocumentType);probe_documents.append(commands._probe_document)
commands._probe_document.name='PrintableThreads 0.5.2 '+('legacy ' if globals().get('probe_legacy',False) else '')+mode+' test'
d=fusion.Design.cast(app.activeProduct);commands._probe_design=d
report={'native_sha256':hashlib.sha256(Path(native.__file__).read_bytes()).hexdigest(),'version':commands.VERSION,'path':str(Path(commands.__file__).parent.parent),'mode':mode,'internal':internal,'nested':nested}
face=None
if mode=='apply':
 c=d.rootComponent;occ=None
 if nested:
  d.designIntent=fusion.DesignIntentTypes.HybridDesignIntentType
  transform=core.Matrix3D.create();transform.setToRotation(.8,core.Vector3D.create(0,1,0),core.Point3D.create(0,0,0));transform.translation=core.Vector3D.create(4,3,2)
  occ=c.occurrences.addNewComponent(transform);c=occ.component
 sk=c.sketches.add(c.xYConstructionPlane)
 for r in ((.6,1.1) if internal else (.6,)):sk.sketchCurves.sketchCircles.addByCenterRadius(core.Point3D.create(0,0,0),r)
 profile=next(p for p in sk.profiles if p.profileLoops.count==2) if internal else sk.profiles.item(0)
 inp=c.features.extrudeFeatures.createInput(profile,fusion.FeatureOperations.NewBodyFeatureOperation);inp.setDistanceExtent(False,core.ValueInput.createByReal(1.2))
 body=c.features.extrudeFeatures.add(inp).bodies.item(0);report['original_volume']=body.volume
 face=next(f for f in body.faces if core.Cylinder.cast(f.geometry) and abs(core.Cylinder.cast(f.geometry).radius-.6)<1e-6)
 if occ:face=face.createForAssemblyContext(occ)
 marker=d.timeline.markerPosition;extra=c.sketches.add(c.xYConstructionPlane);extra.name='Downstream test sketch';d.timeline.markerPosition=marker
original=getattr(native,mode)
def checked(*args,**kwargs):
 try:
  result=original(*args,**kwargs)
  for group in d.timeline.timelineGroups:group.isCollapsed=False
  entities=[d.timeline.item(i).entity for i in range(d.timeline.count) if d.timeline.item(i).entity]
  report['timeline_entries']=d.timeline.count;report['groups']=d.timeline.timelineGroups.count;report['health']=[(e.name,e.errorOrWarningMessage) for e in entities if getattr(e,'errorOrWarningMessage','')]
  report['chamfers']=[{'name':e.name,'faces':e.faces.count} for e in entities if fusion.ChamferFeature.cast(e)]
  report['features']=[e.objectType for e in entities];report['parameters']=[p.name for p in d.userParameters]
  report['solids']=[{'component':c.name,'volume':b.volume,'regions':b.lumps.count} for c in d.allComponents for b in c.bRepBodies if b.isSolid]
  report['passed']=report['groups']==1 and not report['health'] and not any(fusion.BaseFeature.cast(e) for e in entities) and len(report['solids'])==(2 if mode=='create' else 1) and all(b['regions']==1 for b in report['solids']) and len(report['chamfers'])==(2 if mode=='create' else 1) and all(ch['faces']>0 for ch in report['chamfers']) and report['starts_in_main']
  for group in d.timeline.timelineGroups:group.isCollapsed=True
  return result
 except Exception:report['error']=traceback.format_exc();raise
 finally:(repo/f'docs/installed-{mode}-{internal}-{nested}-probe.json').write_text(json.dumps(report,indent=2))
setattr(native,mode,checked)
def configure(args):
 session=commands.sessions[-1]
 report['starts_in_main']=session.values['starts'].parentCommandInput is None
 profile_spec=Spec() if globals().get('probe_legacy',False) else Spec().with_circular_section(2)
 session.load(replace(profile_spec,cut_screw=True,knob='Lobed' if globals().get('probe_optimized_knob',False) else 'None',entry=.6 if globals().get('probe_optimized_knob',False) else 0,engagement=12,length=12,print_on_plate=True,starts=2 if nested else 1))
 if face:session.values['target'].addSelection(face)
 commands._probe_session=session;app.fireCustomEvent('PrintableThreads_test_execute')
def complete(args):commands._probe_session.command.doExecute(True)
events.add(app.registerCustomEvent('PrintableThreads_test_execute'),complete)
definition=app.userInterface.commandDefinitions.itemById('PrintableThreads_'+mode);events.add(definition.commandCreated,configure);definition.execute()
print('Installed '+commands.VERSION+' '+mode+' command scheduled')
