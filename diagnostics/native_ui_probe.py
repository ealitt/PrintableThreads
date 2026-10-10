"""Start a disposable native command test; complete it through Fusion's dialog."""
import sys,importlib
from pathlib import Path
import adsk.core as core,adsk.fusion as fusion
repo=Path('/Users/eammon/Documents/GitHub/PrintableThreads');sys.path.insert(0,str(repo))
for module in list(sys.modules.values()):
    filename=getattr(module,'__file__','') or ''
    if '/API/AddIns/PrintableThreads/commands/' in filename:
        module.stop()
from PrintableThreads import commands
from PrintableThreads.fusion_backend import native
commands.stop();importlib.reload(native);importlib.reload(commands);commands.start()
# Avoid overwriting the user's saved dimensions with test values.
original_save=commands.preferences.save
commands.preferences.save=lambda *args:None
native_ui_doc=core.Application.get().documents.add(core.DocumentTypes.FusionDesignDocumentType)
native_ui_design=fusion.Design.cast(core.Application.get().activeProduct)
core.Application.get().userInterface.commandDefinitions.itemById('PrintableThreads_create').execute()
print('Native Create dialog ready')
