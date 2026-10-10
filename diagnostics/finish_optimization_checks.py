"""Export the disposable compact example, remove test hooks, and restore the user's document."""
import sys,json,hashlib
from pathlib import Path
import adsk.core as core,adsk.fusion as fusion
repo=Path('/Users/eammon/Documents/GitHub/PrintableThreads')
installed=Path.home()/'Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/PrintableThreads'
app=core.Application.get();app.unregisterCustomEvent('PrintableThreads_test_execute')
documents=globals().get('installed_probe_documents',[])
if documents and documents[0].isValid:
 doc=documents[0];doc.activate();d=fusion.Design.cast(app.activeProduct)
 for group in d.timeline.timelineGroups:group.isCollapsed=True
 exported=d.exportManager.execute(d.exportManager.createFusionArchiveExportOptions(str(repo/'dist/PrintableThreads-0.5.2-compact-example.f3d')))
 print('Compact example exported:',exported)
for doc in reversed(documents):
 if doc.isValid:doc.close(False)
user=globals().get('optimization_user_document')
if user and user.isValid:user.activate()
entry=next(m for m in sys.modules.values() if str(getattr(m,'__file__',''))==str(installed/'PrintableThreads.py'))
exec(compile((installed/'PrintableThreads.py').read_text(),str(installed/'PrintableThreads.py'),'exec'),entry.__dict__);entry.run({})
report={'version':entry.commands.VERSION,'native_sha256':hashlib.sha256(Path(entry.native.__file__).read_bytes()).hexdigest(),'commands_file':entry.commands.__file__,'preferences_save_module':entry.preferences.save.__module__,'active_document':app.activeDocument.name}
(repo/'docs/installed-loaded-version.json').write_text(json.dumps(report,indent=2));print(report)
