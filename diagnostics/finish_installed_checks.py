"""Remove test hooks and leave a native example in the installed add-in session."""
import sys,json,hashlib
from pathlib import Path
import adsk.core as core,adsk.fusion as fusion
repo=Path('/Users/eammon/Documents/GitHub/PrintableThreads')
installed=Path.home()/'Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/PrintableThreads'
app=core.Application.get();app.unregisterCustomEvent('PrintableThreads_test_execute')
documents=globals().get('installed_probe_documents',[])
keep=documents[0] if documents else None
for doc in documents[1:]:
 if doc.isValid:doc.close(False)
if keep and keep.isValid:
 keep.activate();keep.name='PrintableThreads 0.5.2 native example'
 d=fusion.Design.cast(app.activeProduct)
 for group in d.timeline.timelineGroups:group.isCollapsed=False
 d.timeline.moveToEnd();app.activeViewport.fit()
 repo.joinpath('dist').mkdir(exist_ok=True)
 exported=d.exportManager.execute(d.exportManager.createFusionArchiveExportOptions(str(repo/'dist/PrintableThreads-0.5.2-native-example.f3d')))
 print('Native example exported:',exported)
entry=next(m for m in sys.modules.values() if str(getattr(m,'__file__',''))==str(installed/'PrintableThreads.py'))
exec(compile((installed/'PrintableThreads.py').read_text(),str(installed/'PrintableThreads.py'),'exec'),entry.__dict__);entry.run({})
report={'version':entry.commands.VERSION,'commands_file':entry.commands.__file__,'native_sha256':hashlib.sha256(Path(entry.native.__file__).read_bytes()).hexdigest(),'preferences_save_module':entry.preferences.save.__module__,'example_name':keep.name if keep and keep.isValid else None}
(repo/'docs/installed-loaded-version.json').write_text(json.dumps(report,indent=2));print(report)
