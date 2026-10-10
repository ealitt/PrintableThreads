"""Exercise the actual add-in Create command and deferred native build."""
import sys,importlib
from pathlib import Path
import adsk.core as core,adsk.fusion as fusion
from dataclasses import replace
repo=Path('/Users/eammon/Documents/GitHub/PrintableThreads');sys.path.insert(0,str(repo))
for module in list(sys.modules.values()):
    if '/API/AddIns/PrintableThreads/commands/' in str(getattr(module,'__file__','')):module.stop()
from PrintableThreads import commands
from PrintableThreads.fusion_backend import native
commands.stop();importlib.reload(native);importlib.reload(commands);commands.start()
from PrintableThreads.model.spec import Spec
commands._original_preference_save=commands.preferences.save
commands.preferences.save=lambda *args:None
commands._probe_document=core.Application.get().documents.add(core.DocumentTypes.FusionDesignDocumentType)
commands._probe_design=fusion.Design.cast(core.Application.get().activeProduct)
def configure(args):
    session=commands.sessions[-1]
    session.load(replace(Spec().with_circular_section(2),cut_screw=True,knob='None',entry=0,engagement=12,length=12,print_on_plate=True))
    commands._probe_session=session
    core.Application.get().fireCustomEvent('PrintableThreads_test_execute')
def complete(args):
    commands._probe_session.command.doExecute(True)
from PrintableThreads.lib import events
app=core.Application.get()
events.add(app.registerCustomEvent('PrintableThreads_test_execute'),complete)
definition=app.userInterface.commandDefinitions.itemById('PrintableThreads_create')
events.add(definition.commandCreated,configure)
definition.execute()
print('Create command scheduled for disposable-document test')
