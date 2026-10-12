"""Fusion command UI: one Create-panel menu, simple inputs, fast live previews."""
import json
import math
import traceback
from dataclasses import asdict,replace
from pathlib import Path
import adsk.core as core
import adsk.fusion as fusion
from ..model.spec import Spec,fit_clearances
from ..model import preferences
from ..model.target import TargetReference
from ..geometry import backend as b
from ..geometry import preview as mesh
from ..fusion_backend import ownership,selection,native
from ..fusion_backend import preview as graphics
from ..lib import events

PREFIX='PrintableThreads_'
MENU_ID=PREFIX+'menu'
VERSION='0.5.3'
COMMANDS=[('create','Create Printable Thread','Create a screw, female part, or matched pair.'),
          ('apply','Apply Printable Thread','Add a printable thread to a cylindrical face.'),
          ('edit','Edit Printable Thread','Regenerate a fastener made by this add-in.'),
          ('fit','Printable Thread Fit Test','Create four clearly marked clearance samples.')]
controls=[]
sessions=[]
NATIVE_EVENT=PREFIX+'native_build'
pending=[]

def build_pending(args):
    work=list(pending);pending.clear()
    for callback in work:
        try:callback()
        except Exception as error:
            core.Application.get().log(traceback.format_exc())
            core.Application.get().userInterface.messageBox(str(error),'Printable Threads — build failed')


TIPS={
 'target':('Choose the part','Select circular cylinder or drafted faces sharing one axis on the same body, including faces interrupted by a cut. Edit selects one add-in-owned body.'),
 'output':('What to make','Screw makes the male part, Female makes the mating part, and Matched pair makes both.'),
 'swap_threads':('Swap screw and nut thread operations','Off: cut a groove in the screw and join an inward rib to the nut. On: join a rib to the screw and cut a groove in the nut.'),
 'root_diameter':('Coil diameter for an on-center circular section','Circular mode centers the section on this diameter, just like Coil / On Center. With a joined screw, outside diameter equals Diameter plus Section size. With a cut screw, outside diameter stays at Diameter. In legacy trapezoid modes this is the base cylinder diameter.'),
 'pitch':('Distance between neighboring ridges','Pitch is measured along the axis. Lead equals pitch multiplied by the number of starts.'),
 'thread_size':('Circular section diameter, like Coil Section Size','Circular / On Center uses the full circle diameter. Half extends outside the base cylinder and half inside. Circular Create/Apply also add an automatic print-edge chamfer, up to 0.2 mm and smaller for tight sections. Legacy Balanced and Custom modes use radial height.'),
 'length':('Axial threaded length','Revolutions are calculated automatically as length divided by lead.'),
 'live_preview':('Show live preview','Apply: select all required faces, then turn Solid Preview on. Turn it off to change the faces. Shows the resulting part with shaded surfaces and edges; final native normal clearance and chamfers may differ slightly.'),
 'starts':('Number of intertwined helices','One start is conventional. Multiple starts increase lead while keeping the entered pitch between adjacent ridges.'),
 'left_hand':('Reverse the turning direction','A left-hand thread tightens counterclockwise when viewed from the entering end.'),
 'phase':('Rotate the thread start','Changes where the first ridge begins around the circumference.'),
 'profile_mode':('Section shape','Circular / On Center matches Coil sizing and placement. Balanced and Custom use the original legacy geometry and fit allowances; their native offset conversion is unfinished.'),
 'width':('Width at the thread root','Axial width where the thread meets the shaft.'),
 'crest':('Width at the thread tip','Axial flat width at the outside of the thread.'),
 'radius':('Rounded section corners','Small radii improve printable transitions. Zero makes a sharp trapezoid.'),
 'entry':('Screw entry taper length','Eases the screw tip for starting. Nut threads remain full-depth and flush with both end faces.'),
 'radial_clearance':('3D print tolerance per side','Circular Create/Apply: uniform distance normal to every nut mating surface, including its straight bore and curved thread. 0.2 mm grows the bore diameter by 0.4 mm. The screw stays nominal. Balanced/Custom, legacy Edit, and Fit Test retain the earlier radial and flank allowances.'),
 'axial_clearance':('Gap on each thread flank','Widens the female groove without changing its pitch or lead.'),
 'fit_preset':('Common printer-fit choices','Select a starting clearance or choose Custom and enter your own values.'),
 'female_diameter':('Outside diameter of the female part','Increase this value for a thicker wall around the internal thread.'),
 'engagement':('Length of the female thread','This can be shorter than the male threaded length.'),
 'blind':('Close the bottom of the female part','Creates a cap instead of a through nut.'),
 'floor':('Thickness below a blind thread','Material between the thread opening and the closed end.'),
 'knob':('Grip on the screw','Choose a lobed hand grip, a plain cylinder, or no grip.'),
 'knob_diameter':('Outside diameter of the grip','A larger grip gives more turning leverage.'),
 'knob_height':('Axial grip thickness','The grip extends behind the start of the threaded shaft.'),
 'lobes':('Number of rounded grip lobes','More lobes make a finer grip; fewer lobes make larger finger surfaces.'),
 'reverse':('Start from the opposite circular edge','Flips the selected cylinder axis without changing thread handedness.'),
 'x':('X position','Root-component position of a newly created part.'),
 'y':('Y position','Root-component position of a newly created part.'),
 'z':('Z position','Root-component position of a newly created part.'),
}

def design(promote=True,allow_existing_part=False):
    d=fusion.Design.cast(core.Application.get().activeProduct)
    if not d:raise ValueError('Open a Fusion Design document first.')
    marker=d.timeline.markerPosition if d.designType==fusion.DesignTypes.ParametricDesignType else None
    if d.designIntent==fusion.DesignIntentTypes.PartDesignIntentType:
        root=d.rootComponent
        populated=root.bRepBodies.count or root.occurrences.count or root.features.count or root.sketches.count
        if populated and not allow_existing_part:
            raise ValueError('Create and Fit Test need Hybrid or Assembly design intent in a populated document. Change Document Settings > Design Intent.')
        if promote:
            d.designIntent=fusion.DesignIntentTypes.HybridDesignIntentType
            if d.designIntent==fusion.DesignIntentTypes.PartDesignIntentType:
                raise ValueError('Fusion could not promote this Part document to Hybrid design intent.')
            if marker is not None:d.timeline.markerPosition=min(marker,d.timeline.count)
    return d

def _remove_ui(ui):
    workspace=ui.workspaces.itemById('FusionSolidEnvironment')
    for panel_id in ('SolidCreatePanel','SolidScriptsAddinsPanel'):
        panel=workspace.toolbarPanels.itemById(panel_id)
        if not panel:continue
        menu=panel.controls.itemById(MENU_ID)
        if menu:menu.deleteMe()
        for mode,_,_ in COMMANDS:
            control=panel.controls.itemById(PREFIX+mode)
            if control:control.deleteMe()

def start():
    app=core.Application.get();ui=app.userInterface;_remove_ui(ui)
    events.add(app.registerCustomEvent(NATIVE_EVENT),build_pending)
    workspace=ui.workspaces.itemById('FusionSolidEnvironment')
    panel=workspace.toolbarPanels.itemById('SolidCreatePanel')
    resources=str(Path(__file__).resolve().parents[1]/'resources')
    definitions=[]
    for mode,name,description in COMMANDS:
        ident=PREFIX+mode
        definition=ui.commandDefinitions.itemById(ident)
        if not definition:definition=ui.commandDefinitions.addButtonDefinition(ident,name,description,resources)
        definition.tooltip=description
        definition.tooltipDescription='Modeled rounded threads for FDM printing. Hover over each input for a plain-language explanation.'
        events.add(definition.commandCreated,lambda args,mode=mode:created(args,mode))
        definitions.append(definition)
    menu=panel.controls.addDropDown('Printable Threads',resources,MENU_ID)
    for definition in definitions:menu.controls.addCommand(definition)
    try:menu.isPromoted=True
    except Exception:pass
    controls.append(menu)

def stop():
    ui=core.Application.get().userInterface
    for session in list(sessions):
        session.renderer.clear();events.clear(session.handlers)
    sessions.clear();events.clear();pending.clear();_remove_ui(ui);controls.clear()
    try:core.Application.get().unregisterCustomEvent(NATIVE_EVENT)
    except Exception:pass
    for mode,_,_ in COMMANDS:
        definition=ui.commandDefinitions.itemById(PREFIX+mode)
        if definition:definition.deleteMe()

def created(args,mode):
    design(False,mode in ('apply','create'))
    session=Session(args.command,mode);sessions.append(session)

class Session:
    def __init__(self,command,mode):
        self.deferred_build=None
        self.command=command;self.mode=mode;self.handlers=[];self.values={};self.loading=False
        self.auto_female=True;self.auto_knob=True;self.print_on_plate=True;self.target_reference=TargetReference()
        self.renderer=graphics.Renderer();self.preview_key=None;self.edit_role=None;self.preview_targets=None
        command.setDialogInitialSize(390,610)
        inputs=command.commandInputs
        inputs.addTextBoxCommandInput('build_version','','Printable Threads '+VERSION,1,True)
        if mode in ('apply','edit'):
            select=inputs.addSelectionInput('target','Cylinder / draft faces' if mode=='apply' else 'Printable thread body',
                                            'Select faces sharing a circular axis on one body' if mode=='apply' else 'Select one add-in-owned body')
            select.addSelectionFilter('Faces' if mode=='apply' else 'SolidBodies');select.setSelectionLimits(1,0 if mode=='apply' else 1)
            self.values['target']=select;self.tip(select,'target')
        if mode=='create':self.dropdown(inputs,'output','Output',['Matched pair','Screw','Female'])

        self.length(inputs,'root_diameter','Diameter',12)
        self.length(inputs,'pitch','Pitch',3)
        self.length(inputs,'thread_size','Section size',2)
        self.values['starts']=inputs.addIntegerSpinnerCommandInput('starts','Starts',1,4,1,1);self.tip(self.values['starts'],'starts')
        self.length(inputs,'length','Thread length',8 if mode=='fit' else 18)
        self.length(inputs,'radial_clearance','3D print tolerance',.2)
        if mode=='fit':self.values['radial_clearance'].tooltipDescription+=' Fit Test creates four nearby clearances for comparison; component names identify each sample.'
        self.values['derived']=inputs.addTextBoxCommandInput('derived','','',2,True)
        self.values['live_preview']=inputs.addBoolValueInput('live_preview','Solid Preview' if mode=='apply' else 'Live Preview',mode=='apply','',mode!='apply')
        self.tip(self.values['live_preview'],'live_preview')
        if mode=='apply':
            self.values['preview_selection']=inputs.addTextBoxCommandInput('preview_selection','','',1,True)
            self.values['preview_selection'].isVisible=False

        advanced=inputs.addGroupCommandInput('advanced','More Options');advanced.isExpanded=False
        advanced.tooltip='Optional controls';advanced.tooltipDescription='Handedness, fit, profile details, placement, knob, and female-part dimensions.'
        more=advanced.children
        self.values['swap_threads']=more.addBoolValueInput('swap_threads','Swap cut / join',True,'',False);self.tip(self.values['swap_threads'],'swap_threads')
        self.values['left_hand']=more.addBoolValueInput('left_hand','Left-hand',True,'',False);self.tip(self.values['left_hand'],'left_hand')
        self.values['phase']=more.addValueInput('phase','Start angle','deg',core.ValueInput.createByString('0 deg'));self.tip(self.values['phase'],'phase')
        self.dropdown(more,'profile_mode','Cross-section',['Circular / On Center','Balanced','Custom'])
        self.length(more,'width','Base width',1.5);self.length(more,'crest','Crest width',.5);self.length(more,'radius','Corner radius',.15)
        self.length(more,'entry','Entry taper',.6)
        self.dropdown(more,'fit_preset','Fit',['Standard FDM — 0.2 mm/side','Loose FDM — 0.5 mm/side','Custom'])
        self.length(more,'axial_clearance','Flank clearance',.15)
        self.length(more,'female_diameter','Female outside diameter',22);self.length(more,'engagement','Female thread length',9)
        self.values['blind']=more.addBoolValueInput('blind','Blind cap',True,'',False);self.tip(self.values['blind'],'blind')
        self.length(more,'floor','Floor thickness',2)
        self.dropdown(more,'knob','Knob',['Lobed','Cylinder','None'])
        self.length(more,'knob_diameter','Knob diameter',26);self.length(more,'knob_height','Knob height',6)
        self.values['lobes']=more.addIntegerSpinnerCommandInput('lobes','Knob lobes',3,12,1,6);self.tip(self.values['lobes'],'lobes')
        if mode=='apply':
            self.values['reverse']=more.addBoolValueInput('reverse','Reverse axis',True,'',False);self.tip(self.values['reverse'],'reverse')
        elif mode!='edit':
            for key in ('x','y','z'):self.length(more,key,key.upper()+' position',0)
        self.values['status']=inputs.addTextBoxCommandInput('status','','',3,True)

        for event,callback in [(command.inputChanged,self.changed),(command.validateInputs,self.validate),
                               (command.executePreview,self.preview),(command.execute,self.execute),(command.destroy,self.destroy)]:
            events.add(event,callback,self.handlers)
        self.restore_preferences()
        if mode=='apply':self.values['live_preview'].value=False
        self.update_visibility();self.update_status()

    def restore_preferences(self):
        saved=preferences.load(self.mode)
        if not saved:return
        try:
            spec=Spec.from_json(saved['recipe'])
            if self.mode!='edit' and 'cut_screw' not in json.loads(saved['recipe'])['spec']:
                spec=replace(spec,cut_screw=True,print_on_plate=True)
            if self.mode!='edit' and 'section' not in json.loads(saved['recipe'])['spec']:
                spec=spec.with_circular_section(2*spec.height)
            self.load(spec)
            self.loading=True
            if 'output' in self.values:self.select_name('output',spec.output)
            for key in ('live_preview','reverse'):
                if key in self.values and type(saved.get(key)) is bool:self.values[key].value=saved[key]
            for key in ('x','y','z'):
                value=saved.get(key)
                if key in self.values and isinstance(value,(int,float)) and math.isfinite(value):
                    self.values[key].expression=f'{value:g} mm'
            self.auto_female=saved.get('auto_female',False) is True
            self.auto_knob=saved.get('auto_knob',False) is True
        except (ValueError,KeyError,TypeError,AttributeError):pass
        finally:self.loading=False

    def save_preferences(self):
        try:
            spec=self.read()
            state={'recipe':spec.to_json(),'auto_female':self.auto_female,'auto_knob':self.auto_knob}
            for key in ('live_preview','reverse'):
                if key in self.values:state[key]=self.values[key].value
            for key in ('x','y','z'):
                if key in self.values:state[key]=self.mm(key)
            preferences.save(self.mode,state)
        except ValueError:pass  # Keep the last valid values while an input is incomplete.
        except OSError as error:core.Application.get().log(f'Printable Threads settings could not be saved: {error}')

    def tip(self,input,key):
        short,long=TIPS[key];input.tooltip=short;input.tooltipDescription=long
    def length(self,inputs,key,label,value):
        item=inputs.addValueInput(key,label,'mm',core.ValueInput.createByString(f'{value} mm'))
        self.values[key]=item;self.tip(item,key)
    def dropdown(self,inputs,key,label,items):
        item=inputs.addDropDownCommandInput(key,label,core.DropDownStyles.TextListDropDownStyle)
        for i,name in enumerate(items):item.listItems.add(name,i==0)
        self.values[key]=item;self.tip(item,key)
    def selected_name(self,key):return self.values[key].selectedItem.name
    def select_name(self,key,name):
        for item in self.values[key].listItems:item.isSelected=item.name==name
    def mm(self,key):return self.values[key].value*10

    def read(self):
        data=asdict(Spec())
        data.update(cut_screw=not self.values['swap_threads'].value,print_on_plate=self.print_on_plate and self.mode!='apply',root_diameter=self.mm('root_diameter'),pitch=self.mm('pitch'),length=self.mm('length'),
                    starts=self.values['starts'].value,left_hand=self.values['left_hand'].value,
                    phase=math.degrees(self.values['phase'].value),entry=self.mm('entry'),
                    radial_clearance=self.mm('radial_clearance'),axial_clearance=self.mm('axial_clearance'),
                    female_diameter=self.mm('female_diameter'),engagement=self.mm('engagement'),
                    floor=self.mm('floor'),blind=self.values['blind'].value,
                    knob=self.selected_name('knob'),knob_diameter=self.mm('knob_diameter'),
                    knob_height=self.mm('knob_height'),lobes=self.values['lobes'].value)
        size=self.mm('thread_size');data['height']=size
        if self.selected_name('profile_mode')=='Circular / On Center':
            data.update(section='Circular',height=size/2,width=size,crest=size/2,radius=0)
        elif self.selected_name('profile_mode')=='Balanced':
            data.update(width=1.5*size,crest=.5*size,radius=.15*size)
        else:data.update(width=self.mm('width'),crest=self.mm('crest'),radius=self.mm('radius'))
        if 'output' in self.values:data['output']=self.selected_name('output')
        if self.mode in ('create','apply') and data.get('section')=='Circular':data['axial_clearance']=0
        if self.mode=='apply':data.update(knob='None',entry=0,output='Screw')
        if self.mode=='fit':data.update(engagement=data['length'],blind=False,output='Matched pair',entry=min(data['entry'],data['length']/4))
        return Spec(**data).validate()

    def expressions(self):
        keys=('root_diameter','pitch','thread_size','length','width','crest','radius','entry','radial_clearance',
              'axial_clearance','female_diameter','engagement','floor','knob_diameter','knob_height')
        return {key:self.values[key].expression for key in keys}

    def load(self,spec):
        self.loading=True
        try:
            for key in ('root_diameter','pitch','length','width','crest','radius','entry','radial_clearance',
                        'axial_clearance','female_diameter','engagement','floor','knob_diameter','knob_height'):
                self.values[key].expression=f'{getattr(spec,key):.12g} mm'
            self.values['thread_size'].expression=f'{spec.thread_size:.12g} mm'
            self.print_on_plate=spec.print_on_plate
            self.values['swap_threads'].value=not spec.cut_screw
            for key in ('starts','lobes','blind','left_hand'):self.values[key].value=getattr(spec,key)
            self.values['phase'].expression=f'{spec.phase:.12g} deg'
            self.select_name('knob',spec.knob);self.select_name('profile_mode','Circular / On Center' if spec.section=='Circular' else 'Balanced' if spec.balanced_profile else 'Custom')
            self.select_name('fit_preset','Standard FDM — 0.2 mm/side' if math.isclose(spec.radial_clearance,.2) else
                             'Loose FDM — 0.5 mm/side' if math.isclose(spec.radial_clearance,.5) else 'Custom')
            self.auto_female=False;self.auto_knob=False
        finally:self.loading=False

    def update_auto_dimensions(self):
        """Keep secondary diameters useful while the four main inputs are edited."""
        major=self.mm('root_diameter')+(0 if not self.values['swap_threads'].value else 1 if self.selected_name('profile_mode')=='Circular / On Center' else 2)*self.mm('thread_size')
        self.loading=True
        try:
            if self.auto_female:self.values['female_diameter'].expression=f'{major+8:g} mm'
            if self.auto_knob:self.values['knob_diameter'].expression=f'{major+12:g} mm'
        finally:self.loading=False

    def update_visibility(self):
        custom=self.selected_name('profile_mode')=='Custom'
        for key in ('width','crest','radius'):self.values[key].isVisible=custom
        output=self.selected_name('output') if 'output' in self.values else None
        female=self.mode=='fit' or output in ('Female','Matched pair') or self.edit_role=='Female' or self.mode=='apply'
        screw=output in ('Screw','Matched pair') or self.edit_role=='Screw' or self.mode=='fit'
        for key in ('female_diameter','engagement','blind','floor','fit_preset','axial_clearance'):
            self.values[key].isVisible=female and self.mode not in ('fit','apply')
        if self.mode=='apply':
            self.values['radial_clearance'].isVisible=True;self.values['axial_clearance'].isVisible=True;self.values['fit_preset'].isVisible=True
        for key in ('knob','knob_diameter','knob_height','lobes'):self.values[key].isVisible=screw and self.mode!='apply'
        lobed=self.selected_name('knob')=='Lobed';has_knob=self.selected_name('knob')!='None'
        self.values['lobes'].isVisible=self.values['lobes'].isVisible and lobed
        for key in ('knob_diameter','knob_height'):self.values[key].isVisible=self.values[key].isVisible and has_knob
        self.values['floor'].isVisible=self.values['floor'].isVisible and self.values['blind'].value
        self.values['root_diameter'].isEnabled=self.mode!='apply'
        if self.mode=='fit':
            for key in ('female_diameter','engagement','blind','floor','fit_preset','axial_clearance'):self.values[key].isVisible=False
        self.values['radial_clearance'].isVisible=True
        if self.mode in ('create','apply'):self.values['axial_clearance'].isVisible=self.selected_name('profile_mode')!='Circular / On Center'

    def current_target(self):
        return self.preview_targets if self.preview_targets is not None else self.target_reference.capture(self.values['target'])

    def toggle_solid_preview(self):
        select=self.values['target']
        self.loading=True
        try:
            if self.values['live_preview'].value:
                if self.preview_targets is not None:return
                targets=self.target_reference.capture(select)
                if targets is None:self.values['live_preview'].value=False;return
                self.preview_targets=targets
                count=len(selection.selected_faces(targets))
                self.values['preview_selection'].text=f'{count} face(s) selected — turn Solid Preview off to change selection.'
                self.values['preview_selection'].isVisible=True
                select.setSelectionLimits(0,0);select.clearSelection();select.isVisible=False
            else:
                self.renderer.clear();select.isVisible=True;select.setSelectionLimits(1,0)
                targets=self.preview_targets;self.preview_targets=None
                if targets:
                    for face in selection.selected_faces(targets):
                        if face.isValid:select.addSelection(face)
                self.target_reference.capture(select)
                self.values['preview_selection'].isVisible=False
        finally:self.loading=False

    def changed(self,args):
        if self.loading:return
        key=args.input.id;self.preview_key=None
        if key=='live_preview' and self.mode=='apply':self.toggle_solid_preview()
        if key=='target' and self.preview_targets is not None:return
        if key=='target':self.target_reference.capture(self.values['target'])
        try:
            if key=='female_diameter':self.auto_female=False
            elif key=='knob_diameter':self.auto_knob=False
            elif key in ('root_diameter','thread_size','profile_mode','swap_threads'):self.update_auto_dimensions()
            if key=='fit_preset':
                name=self.selected_name(key)
                if name!='Custom':
                    self.loading=True;self.values['radial_clearance'].expression=('0.5' if name.startswith('Loose') else '0.2')+' mm';self.loading=False
            elif key=='radial_clearance':
                self.loading=True;self.select_name('fit_preset','Custom');self.loading=False
            if key in ('target','reverse') and self.current_target() is not None:
                target=self.current_target()
                if self.mode=='edit':
                    _,_,record,_=ownership.editable(design(),target);self.edit_role=record['role']
                    self.load(Spec.from_json(json.dumps(record['recipe'])))
                else:
                    _,_,diameter,length,_=selection.cylinder_frame(target,self.values['reverse'].value)
                    self.loading=True;self.values['root_diameter'].expression=f'{diameter} mm'
                    if key=='target':self.values['length'].expression=f'{length} mm'
                    self.loading=False
            self.update_visibility();self.update_status()
            self.save_preferences()
        except Exception as error:
            self.loading=False;self.renderer.clear();self.values['status'].text=str(error)

    def update_status(self):
        try:
            s=self.read()
            if self.mode=='create' and s.section=='Circular':native.validate_clearance(s,s.output!='Screw')
            self.values['derived'].text=(f'Outside Ø {s.major_diameter:g} mm  •  {s.turns:.3g} revolutions\n'
                                         f'Lead {s.lead:g} mm/rev  •  {s.clearance_label}')
            self.values['status'].text=('Solid Preview: shaded result; native normal-clearance finishing and edge chamfers may differ slightly. Turn preview off to change faces.' if self.mode=='apply' and self.values['live_preview'].value else 'Circular: native Coil, uniform nut clearance and print-edge chamfer. Edit PT parameters in Modify → Change Parameters.' if self.mode in ('create','apply') and s.section=='Circular' else 'Balanced / Custom: original legacy construction and fit allowances; native offset conversion is unfinished.' if self.mode in ('create','apply') else 'Ready — preview is approximate; OK creates the exact solid.')
            return True
        except Exception as error:
            self.values['derived'].text='';self.values['status'].text=str(error);return False

    def validate(self,args):
        valid=self.update_status()
        if self.mode in ('apply','edit'):
            valid=valid and (self.current_target() is not None if self.mode=='apply' else self.values['target'].selectionCount==1)
            if valid:
                try:
                    target=self.current_target()
                    if self.mode=='edit':ownership.editable(design(),target)
                    else:
                        _,_,_,length,internal=selection.cylinder_frame(target,self.values['reverse'].value)
                        selection.validate_draft(target,self.read())
                        if self.read().section=='Circular':native.validate_clearance(self.read(),internal)
                        if self.read().length>length+1e-5:raise ValueError('Thread length exceeds the selected cylindrical face.')
                except Exception as error:self.values['status'].text=str(error);valid=False
        args.areInputsValid=valid

    def placement(self,offset=0):
        matrix=b.M()
        if self.mode not in ('apply','edit'):
            # Local thread Z points along +Y, away from Fusion's ZX print plate.
            matrix.setToRotation(-math.pi/2,b.V(1,0,0),b.P(0,0,0))
            matrix.translation=b.V(self.values['x'].value+offset/10,self.values['y'].value,self.values['z'].value)
        return matrix

    def draw_screw(self,spec,matrix):
        shown=mesh.screw(spec)
        if spec.print_on_plate and spec.knob!='None':shown=mesh.moved(shown,z=spec.knob_height)
        self.renderer.draw(shown,matrix,(45,155,255),.58,'Screw preview')
    def draw_female(self,spec,matrix):
        if spec.cut_screw:
            shown=mesh.radial_surface(replace(spec,length=spec.engagement,knob='None'),outer=spec.female_diameter/2,normal_clearance=spec.radial_clearance) if self.mode=='create' and spec.section=='Circular' else mesh.radial_surface(spec.nut_rib(),outer=spec.female_diameter/2)
            if spec.blind:
                shown=mesh.merge(shown,mesh.cylinder(spec.female_diameter/2,-spec.floor,0))
                if spec.print_on_plate:shown=mesh.moved(shown,z=spec.floor)
            self.renderer.draw(shown,matrix,(255,125,35),.58,'Joined nut rib preview');return
        shift=spec.floor if spec.print_on_plate and spec.blind else 0
        self.renderer.draw(mesh.cylinder(spec.female_diameter/2,shift-spec.floor if spec.blind else 0,shift+spec.engagement),matrix,(135,145,160),.25,'Female blank preview')
        self.renderer.draw(mesh.moved(mesh.helix(replace(spec,length=spec.engagement),normal_clearance=spec.radial_clearance) if self.mode=='create' and spec.section=='Circular' else mesh.helix(spec.nut_rib() if spec.cut_screw else spec.cutter()),z=shift),matrix,(255,125,35),.72,'Female groove preview')

    def render_preview(self):
        if not self.values['live_preview'].value:self.renderer.clear();return
        try:
            spec=self.read();target_token=''
            if self.mode in ('apply','edit'):
                target=self.current_target()
                if target is None:self.renderer.clear();return
                target_token=tuple(f.entityToken for f in selection.selected_faces(target))
            position=tuple(self.values[k].value for k in ('x','y','z')) if self.mode not in ('apply','edit') else ()
            key=(spec,self.mode,target_token,position,self.values.get('reverse').value if 'reverse' in self.values else False,self.edit_role)
            if key==self.preview_key:return
            self.preview_key=key
            if self.mode=='apply':
                face,frame,_,_,internal=selection.cylinder_frame(target,self.values['reverse'].value)
                candidate=selection.preview_body(design(False,True),target,spec,self.values['reverse'].value)
                self.renderer.begin(face.body.parentComponent)
                self.renderer.draw_body(candidate,face.body,'Applied thread solid preview')
            elif self.mode=='edit':
                native=target.nativeObject or target;self.renderer.begin(native.parentComponent)
                if self.edit_role=='Female':self.draw_female(spec,b.M())
                else:self.draw_screw(spec,b.M())
            else:
                root=design(False,self.mode=='create').rootComponent;self.renderer.begin(root)
                if self.mode=='fit':
                    self.draw_screw(spec,self.placement())
                    for i,clearance in enumerate(fit_clearances(spec.radial_clearance)):
                        self.draw_female(replace(spec,radial_clearance=clearance),self.placement((i+1)*(spec.female_diameter+4)))
                else:
                    if spec.output!='Female':self.draw_screw(spec,self.placement())
                    if spec.output!='Screw':
                        offset=(max(spec.knob_diameter,spec.major_diameter)+spec.female_diameter)/2+5 if spec.output=='Matched pair' else 0
                        self.draw_female(spec,self.placement(offset))
            self.renderer.finish()
        except Exception as error:
            self.renderer.clear();self.preview_key=locals().get('key')
            self.values['status'].text=f'Preview unavailable: {error}. OK still creates the exact solid.'
            core.Application.get().log(traceback.format_exc())

    def bodies(self,spec):
        root=design().rootComponent;result=[]
        if self.mode=='fit':
            result.append(('Screw',b.screw(root,spec),self.placement()))
            for i,clearance in enumerate(fit_clearances(spec.radial_clearance)):
                sample=replace(spec,radial_clearance=clearance);sample.validate();body=b.female(root,sample)
                radius=(sample.female_diameter+sample.major_diameter+2*clearance)/4
                for j in range(i+1):
                    angle=2*math.pi*j/12
                    b.cut(body,b.cylinder(.4,sample.engagement-.5,sample.engagement+.1,radius*math.cos(angle),radius*math.sin(angle)))
                result.append((f'{i+1} dots — {clearance:g} mm per side',body,self.placement((i+1)*(spec.female_diameter+4))))
            return result
        if spec.output!='Female':result.append(('Screw',b.screw(root,spec),self.placement()))
        if spec.output!='Screw':
            offset=(max(spec.knob_diameter,spec.major_diameter)+spec.female_diameter)/2+5 if spec.output=='Matched pair' else 0
            result.append(('Female',b.female(root,spec),self.placement(offset)))
        return result

    def preview(self,args):self.render_preview();args.isValidResult=False

    def execute(self,args):
        try:
            # Promotion to Hybrid can clear SelectionCommandInput. Capture first.
            if self.mode in ('apply','edit'):self.target_reference.before_execute(self.values['target'])
            self.renderer.clear()
            spec=self.read();d=design(allow_existing_part=self.mode in ('apply','create'))
            if self.mode in ('apply','edit'):target=self.target_reference.resolve(d)
            if self.mode=='edit':ownership.regenerate(d,target,spec,self.expressions())
            elif self.mode in ('apply','create'):
                expressions=self.expressions();mode=self.mode
                reference=self.target_reference;reverse=self.values['reverse'].value if mode=='apply' else False
                base=self.placement();doc=core.Application.get().activeDocument
                def placement(offset=0):
                    matrix=base.copy();translation=matrix.translation
                    translation.x+=offset/10;matrix.translation=translation;return matrix
                def build():
                    if not doc.isValid:raise ValueError('The thread document was closed before construction.')
                    doc.activate()
                    if spec.section=='Circular':
                        if mode=='apply':native.apply(d,reference.resolve(d),spec,reverse,expressions)
                        else:native.create(d,spec,placement,expressions)
                    else:
                        start=d.timeline.markerPosition
                        if mode=='apply':selection.apply(d,reference.resolve(d),spec,reverse)
                        else:
                            bodies=[];root=d.rootComponent
                            if spec.output!='Female':bodies.append(('Screw',b.screw(root,spec),placement()))
                            if spec.output!='Screw':
                                offset=(max(spec.knob_diameter,spec.major_diameter)+spec.female_diameter)/2+5 if spec.output=='Matched pair' else 0
                                bodies.append(('Female',b.female(root,spec),placement(offset)))
                            made=ownership.commit(root,spec,bodies,expressions)
                        end=d.timeline.markerPosition-1
                        if end>start:
                            group=d.timeline.timelineGroups.add(start,end);group.name='Printable Threads — legacy '+mode;group.isCollapsed=True
                        if mode=='create':
                            for occ in made:
                                attribute=occ.component.attributes.itemByName(ownership.GROUP,'recipe');record=json.loads(attribute.value)
                                record['timeline_count']=d.timeline.count;attribute.value=json.dumps(record)
                    core.Application.get().activeViewport.fit()
                # Fusion archive import is prohibited inside command events.
                # Capture values now and build on the next main-thread custom event.
                self.deferred_build=build
            else:
                made=ownership.commit(d.rootComponent,spec,self.bodies(spec),self.expressions())
                if self.mode=='fit':
                    for occurrence in made:
                        attribute=occurrence.component.attributes.itemByName(ownership.GROUP,'recipe')
                        if attribute:attribute.deleteMe()
            core.Application.get().activeViewport.fit()
            self.save_preferences()
        except Exception as error:
            args.executeFailed=True;args.executeFailedMessage=str(error);core.Application.get().log(traceback.format_exc())

    def destroy(self,args):
        self.renderer.clear();events.clear(self.handlers)
        if self in sessions:sessions.remove(self)
        if self.deferred_build:
            pending.append(self.deferred_build);self.deferred_build=None
            core.Application.get().fireCustomEvent(NATIVE_EVENT)
