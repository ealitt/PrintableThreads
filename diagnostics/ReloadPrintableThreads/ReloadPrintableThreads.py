import adsk.core,importlib,sys,traceback

def run(context):
    ui=adsk.core.Application.get().userInterface
    try:
        module=next((value for name,value in sys.modules.items()
                     if name.endswith('.commands') and '/API/AddIns/PrintableThreads/' in str(getattr(value,'__file__',''))),None)
        if not module:raise RuntimeError('Printable Threads command module is not loaded.')
        module.stop()
        entry=sys.modules[module.__name__.rsplit('.',1)[0]]
        from pathlib import Path
        exec(compile(Path(entry.__file__).read_text(),entry.__file__,'exec'),entry.__dict__)
        entry.run(None)
        ui.messageBox('Printable Threads reloaded from installed source. Open a tool and check the version at the top.','Reload complete')
    except Exception:ui.messageBox(traceback.format_exc(),'Reload failed')
