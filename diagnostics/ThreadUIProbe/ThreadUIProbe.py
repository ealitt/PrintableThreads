import adsk.core, adsk.fusion, json, pathlib, traceback, threading, time, uuid

handlers=[]

def execute_later(ui,definition):
    event_id='PrintableThreads.UIProbe.'+str(uuid.uuid4())
    event=adsk.core.Application.get().registerCustomEvent(event_id)
    class Handler(adsk.core.CustomEventHandler):
        def notify(self,args):
            try:definition.execute()
            finally:
                event.remove(self);adsk.core.Application.get().unregisterCustomEvent(event_id)
                adsk.terminate()
    handler=Handler();event.add(handler);handlers.append(handler)
    def fire():time.sleep(.25);adsk.core.Application.get().fireCustomEvent(event_id)
    threading.Thread(target=fire,daemon=True).start()
    adsk.autoTerminate(False)

def run(context):
    out=pathlib.Path.home()/'Documents/GitHub/Fusion-3D-printable-threads/docs/ui-probe.json'
    app=adsk.core.Application.get();ui=app.userInterface
    try:
        data={'version':app.version,'active_workspace':ui.activeWorkspace.id,'commands':[]}
        for mode in ('create','edit','apply','fit'):
            data['commands'].append([mode,bool(ui.commandDefinitions.itemById('PrintableThreads_'+mode))])
        panel=ui.workspaces.itemById('FusionSolidEnvironment').toolbarPanels.itemById('SolidCreatePanel')
        data['create_panel_controls']=[panel.controls.item(i).id for i in range(panel.controls.count)]
        menu=panel.controls.itemById('PrintableThreads_menu')
        data['printable_threads_menu']={'found':bool(menu),'items':[menu.controls.item(i).id for i in range(menu.controls.count)] if menu else []}
        out.write_text(json.dumps(data,indent=2))
        ui.messageBox(json.dumps(data,indent=2),'UI registration probe')
        command=ui.commandDefinitions.itemById('PrintableThreads_create')
        if command:execute_later(ui,command)
    except Exception:
        out.write_text(json.dumps({'error':traceback.format_exc()},indent=2));ui.messageBox(traceback.format_exc(),'UI probe failed')
