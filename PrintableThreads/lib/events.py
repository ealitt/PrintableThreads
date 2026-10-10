"""Small retained-handler helper following Fusion's generated-template pattern."""
import sys
import traceback
import adsk.core

handlers=[]

def add(event, callback, retain=None):
    annotation=event.add.__annotations__['handler']
    handler_type=getattr(sys.modules[event.__module__],annotation)
    class Handler(handler_type):
        def __init__(self):super().__init__()
        def notify(self,args):
            try:callback(args)
            except Exception:
                adsk.core.Application.get().log(traceback.format_exc())
                adsk.core.Application.get().userInterface.messageBox(traceback.format_exc(),'Printable Threads')
    handler=Handler();event.add(handler)
    (handlers if retain is None else retain).append((event,handler))

def clear(retain=None):
    target=handlers if retain is None else retain
    for event,handler in target:
        try:event.remove(handler)
        except Exception:pass  # Fusion may already have destroyed the command.
    target.clear()
