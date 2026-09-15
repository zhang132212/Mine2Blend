"""Blender integration. Persistent JSON is stored in the scene; meshes are derived."""
import json
import math
import time,uuid,copy
import bpy
from bpy.props import StringProperty, IntVectorProperty, PointerProperty,IntProperty,BoolProperty,EnumProperty,CollectionProperty
from bpy.app.handlers import persistent
from .service import EditorService
from .grid import BlockGrid, blender_to_mc
from .render import ModelLibrary, rebuild

SERVICE = EditorService()
LIBRARY = None
LIBRARIES = {}
SCENE_GRIDS={}
RENDER_QUEUE={}
LAST_AUTOSAVE=0
STATE_ENUMS={}
UPDATING_STATE=False
REQUEST_CACHE={}
UNDO_GRIDS={}
RECOVERY_PENDING={}
SCENE_IDENTITIES={}

def redraw_view(self,context):
    if context and context.screen:
        for area in context.screen.areas:
            if area.type=='VIEW_3D':area.tag_redraw()

def state_items(self,context):
    key=(self.block_id,self.key)
    if key not in STATE_ENUMS:
        values=SERVICE.registry.blocks[self.block_id.removeprefix('minecraft:')][0].get(self.key,[])
        STATE_ENUMS[key]=[(v,v,'') for v in values]
    return STATE_ENUMS[key]

def state_field_update(self,context):
    if UPDATING_STATE or context is None:return
    s=context.scene.m2b_editor
    try:
        b=SERVICE.registry.resolve(s.state);props=dict(b.properties);props[self.key]=self.value
        from .grid import BlockRecord
        s.state=BlockRecord(b.block_id,tuple(sorted(props.items()))).state
    except ValueError:pass

def state_update(self,context):
    global UPDATING_STATE
    if UPDATING_STATE:return
    try:b=SERVICE.registry.resolve(self.state)
    except ValueError:return
    UPDATING_STATE=True
    try:
        self.state_fields.clear()
        for key,value in b.properties:
            field=self.state_fields.add();field.block_id=b.block_id;field.key=key;field.value=value
    finally:UPDATING_STATE=False

class M2BStateField(bpy.types.PropertyGroup):
    key:StringProperty()
    block_id:StringProperty()
    value:EnumProperty(items=state_items,update=state_field_update)

def current(context):
    activate_scene(context.scene)
    grid_id = context.scene.m2b_editor.grid_id
    if grid_id not in SERVICE.grids:
        raise ValueError("Create or import a grid first")
    return SERVICE.grids[grid_id]

def persist(scene,force=False):
    from . import persistence
    grids=SCENE_GRIDS.get(scene.as_pointer(),{})
    if force:
        persistence.PENDING.pop(scene.as_pointer(),None)
        scene['m2b_editor_data']=persistence.encode(list(grids.values()))
        persistence.SAVED[scene.as_pointer()]=persistence.signature(list(grids.values()))
    else:persistence.schedule(scene.as_pointer(),list(grids.values()))

def activate_scene(scene):
    scene_id(scene)
    key=scene.as_pointer()
    if key not in SCENE_GRIDS:
        grids={}
        for data in json.loads(scene.get('m2b_editor_data','[]')):
            grid=BlockGrid.from_dict(data);grids[grid.id]=grid
        SCENE_GRIDS[key]=grids
    SERVICE.grids=SCENE_GRIDS[key]

def refresh(grid, scene):
    global LIBRARY
    key=tuple(grid.resource_packs)
    if key not in LIBRARIES:
        from .resource_loader import load
        library=ModelLibrary()
        for path in grid.resource_packs:load(library,path)
        LIBRARIES[key]=library
    LIBRARY=LIBRARIES[key]
    result = rebuild(grid, LIBRARY,max_chunks=8)
    if grid.dirty:RENDER_QUEUE[(scene.as_pointer(),grid.id)]=LIBRARY
    persist(scene)
    return result

def execute(command, arguments):
    arguments=dict(arguments)
    target=arguments.pop('scene_id',None);request_id=arguments.pop('request_id',None)
    if command=='list_scenes':return [{'scene_id':scene_id(s),'name':s.name} for s in bpy.data.scenes]
    scene=next((s for s in bpy.data.scenes if scene_id(s)==target),None) if target else bpy.context.scene
    if scene is None:raise ValueError('Scene ID does not exist')
    signature=json.dumps([scene_id(scene),command,arguments],sort_keys=True)
    if request_id in REQUEST_CACHE:
        previous,result=REQUEST_CACHE[request_id]
        if previous!=signature:raise ValueError('Idempotency key was already used for different arguments')
        return copy.deepcopy(result)
    with bpy.context.temp_override(scene=scene):result=_execute(command,arguments)
    if request_id:
        REQUEST_CACHE[request_id]=(signature,copy.deepcopy(result))
        if len(REQUEST_CACHE)>512:REQUEST_CACHE.pop(next(iter(REQUEST_CACHE)))
    return result

def _execute(command, arguments):
    """Call this from blender-mcp execute_blender_code, on Blender's main thread."""
    activate_scene(bpy.context.scene)
    if command=='start_io_job':
        from . import jobs
        grid=SERVICE.grids.get(arguments.get('grid_id'))
        if arguments['command'].startswith('export') and grid is None:raise ValueError('Choose a grid')
        return jobs.start(arguments['command'],arguments['path'],bpy.context.scene.as_pointer(),grid)
    if command=='get_job_status':
        from .jobs import JOBS
        return JOBS[arguments['job_id']].summary()
    if command=='cancel_job':
        from .jobs import cancel
        return cancel(arguments['job_id'])
    if command=='save_recovery':
        from .recovery import save
        return {'path':save(list(SERVICE.grids.values()),recovery_folder(),scene_id(bpy.context.scene))}
    if command=='recover_snapshot':
        from .recovery import load
        imported=load(arguments['path']);ids=[]
        for grid in imported:
            grid.id=uuid.uuid4().hex;grid.name+=' (Recovered)';SERVICE.grids[grid.id]=grid;ids.append(grid.id)
            refresh(grid,bpy.context.scene)
        if ids:bpy.context.scene.m2b_editor.grid_id=ids[0]
        persist(bpy.context.scene)
        return {'grid_ids':ids}
    if command == "render_preview":
        grid=SERVICE.grids[arguments['grid_id']]
        result=refresh(grid,bpy.context.scene)
        if arguments.get('path'):
            from .preview import render
            rebuild(grid,LIBRARY)
            result.update(render(grid,arguments['path'],arguments.get('size',1024)))
        return result
    if command=='load_resource_pack':
        from .resource_loader import load
        grid=SERVICE.grids[arguments['grid_id']]
        if arguments.get('expected_revision')!=grid.revision:raise ValueError('Revision conflict')
        paths=list(grid.resource_packs)
        path=bpy.path.abspath(arguments['path'])
        if path not in paths:paths.append(path)
        library=ModelLibrary();reports=[load(library,p) for p in paths]
        metadata=grid.metadata();metadata['resource_packs']=paths
        result=grid.apply([],grid.revision,metadata)
        LIBRARIES[tuple(paths)]=library;grid.dirty.update(grid.chunks)
        result.update(resource_packs=reports,preview=refresh(grid,bpy.context.scene))
        return result
    result = SERVICE.execute(command, arguments)
    grid_id = arguments.get("grid_id") or (result.get("grid_id") if isinstance(result, dict) else None)
    if grid_id:
        bpy.context.scene.m2b_editor.grid_id = grid_id
        grid = SERVICE.grids[grid_id]
        if grid.dirty:
            try:
                refresh(grid, bpy.context.scene)
            except Exception as exc:
                # Data is already committed; report the derived-preview failure without
                # implying that the block transaction was rolled back.
                if isinstance(result, dict):
                    result["preview_warning"] = str(exc)
                print("Mine2Blend preview rebuild failed:", exc)
    if command not in ('list_blocks','list_grids','get_summary','get_block','query_region','get_components','validate_orientations','validate_support','export_litematic','export_schem'):
        persist(bpy.context.scene)
    return result

@persistent
def load_post(_):
    if getattr(bpy.context, "scene", None) is None:
        return
    SCENE_GRIDS.clear()
    SCENE_IDENTITIES.clear()
    RENDER_QUEUE.clear()
    REQUEST_CACHE.clear()
    from . import persistence
    persistence.clear()
    scene = bpy.context.scene
    try:
        for saved_scene in bpy.data.scenes:activate_scene(saved_scene)
        activate_scene(scene)
        if SERVICE.grids and scene.m2b_editor.grid_id not in SERVICE.grids:
            scene.m2b_editor.grid_id = next(iter(SERVICE.grids))
    except Exception as exc:
        print("Mine2Blend Editor restore failed:", exc)

@persistent
def save_pre(_):
    for scene in bpy.data.scenes:
        if scene.as_pointer() in SCENE_GRIDS:persist(scene,force=True)

@persistent
def native_undo_pre(_):
    # Block transactions have their own history. Blender's global undo can
    # restore an older asynchronous JSON snapshot and replace scene pointers.
    UNDO_GRIDS.clear()
    for scene in bpy.data.scenes:
        grids=SCENE_GRIDS.get(scene.as_pointer())
        if grids is not None:UNDO_GRIDS[scene_id(scene)]=grids

@persistent
def native_undo_post(_):
    from . import persistence
    persistence.clear();SCENE_GRIDS.clear();RENDER_QUEUE.clear()
    for scene in bpy.data.scenes:
        grids=UNDO_GRIDS.get(scene_id(scene))
        if grids is None:continue
        SCENE_GRIDS[scene.as_pointer()]=grids
        for grid in grids.values():
            grid.dirty.update(grid.chunks)
            with bpy.context.temp_override(scene=scene):refresh(grid,scene)
        persist(scene)
    UNDO_GRIDS.clear()
    activate_scene(bpy.context.scene)

class M2BEditorSettings(bpy.types.PropertyGroup):
    grid_id: StringProperty(name="Active Grid")
    state: StringProperty(name="Block State", default="minecraft:stone",update=state_update)
    state_fields:CollectionProperty(type=M2BStateField)
    minimum: IntVectorProperty(name="From (MC XYZ)", size=3,update=redraw_view)
    maximum: IntVectorProperty(name="To (inclusive)", size=3, default=(7, 0, 7),update=redraw_view)
    path: StringProperty(name="Schematic File", subtype="FILE_PATH", default="//building.litematic")
    search: StringProperty(name="Search Blocks")
    status: StringProperty(name="Status")
    replace_state:StringProperty(name="Replace",default="minecraft:stone")
    offset:IntVectorProperty(name="Offset",size=3,default=(8,0,0))
    pivot:IntVectorProperty(name="Pivot",size=3)
    turns:IntProperty(name="Quarter turns",default=1,min=0,max=3)
    copies:IntProperty(name="Array count",default=3,min=1,max=1000)
    move:BoolProperty(name="Move source",default=True)
    slice_min:IntProperty(name="Lowest Y",default=0)
    slice_max:IntProperty(name="Highest Y",default=8)
    resource_path:StringProperty(name="Resource pack",subtype="FILE_PATH")
    component_name:StringProperty(name="Component",default="Wall")
    clipboard:StringProperty()
    auto_orient:BoolProperty(name="Orient from view",default=True)
    job_id:StringProperty()
    autosave:BoolProperty(name='Auto recovery (60s)',default=True)
    recovery_path:StringProperty(name='Recovery file',subtype='FILE_PATH')
    show_selection:BoolProperty(name='Selection outline',default=True,update=redraw_view)
    hotbar:StringProperty(default=json.dumps(['minecraft:'+b for b in ('stone','oak_planks','glass','oak_stairs','stone_slab','oak_door','oak_fence','lantern','stone_bricks')]))
    hotbar_slot:IntProperty(name='Shortcut slot',default=1,min=1,max=9)
    region_name:StringProperty(name='Export region',default='Main')

class M2B_OT_command(bpy.types.Operator):
    bl_idname = "m2b_editor.command"
    bl_label = "Minecraft Editor Command"
    action: StringProperty()
    value: StringProperty()

    def execute(self, context):
        settings = context.scene.m2b_editor
        try:
            args = {}
            if self.action in ('hotbar_use','hotbar_save'):
                slots=json.loads(settings.hotbar)
                if self.action=='hotbar_use':settings.state=slots[int(self.value)]
                else:slots[settings.hotbar_slot-1]=settings.state;settings.hotbar=json.dumps(slots)
                return {'FINISHED'}
            if self.action == "select_block":
                settings.state = self.value
                return {"FINISHED"}
            if self.action == "select_grid":
                settings.grid_id = self.value
                return {"FINISHED"}
            if self.action not in ("create_grid", "import_litematic", "import_schem", "start_bridge", "stop_bridge"):
                grid = current(context)
                args = {"grid_id": grid.id, "expected_revision": grid.revision}
            if self.action == "fill_region":
                args.update(minimum=list(settings.minimum), maximum=list(settings.maximum), state=settings.state)
            elif self.action == "place_block":
                args.update(position=list(settings.minimum), state=settings.state)
            elif self.action=='replace_blocks':
                args.update(minimum=list(settings.minimum),maximum=list(settings.maximum),state=settings.state,replace=settings.replace_state)
            elif self.action in ('rotate','mirror_x','mirror_z','array','translate'):
                args.update(minimum=list(settings.minimum),maximum=list(settings.maximum),pivot=list(settings.pivot),move=settings.move)
                args['turns']=settings.turns if self.action=='rotate' else 0
                if self.action.startswith('mirror'):args['mirror']=self.action[-1]
                if self.action in ('array','translate'):args['offset']=list(settings.offset)
                if self.action=='array':args.update(copies=settings.copies,move=False)
                self.action='transform_region'
            elif self.action=='copy_selection':
                from .clipboard import capture
                settings.clipboard=json.dumps(capture(grid,list(settings.minimum),list(settings.maximum)))
                settings.status='Copied selection'
                return {'FINISHED'}
            elif self.action=='paste_selection':
                data=json.loads(settings.clipboard or '{}')
                if isinstance(data,list):
                    args['blocks']=[{'position':[r[i]+settings.minimum[i] for i in range(3)],'state':r[3],**({'nbt':r[4]} if r[4] else {})} for r in data]
                    self.action='apply_blocks'
                else:args.update(clipboard=data,origin=list(settings.minimum))
            elif self.action in ('slice','show_all','isolate','xray','hide_layer','mesh_preview','instance_preview'):
                if self.action=='slice':view={'slice_min':settings.slice_min,'slice_max':settings.slice_max}
                elif self.action=='isolate':view={'isolate':[list(settings.minimum),list(settings.maximum)]}
                elif self.action=='xray':view={'xray':not grid.view['xray']}
                elif self.action=='hide_layer':view={'hidden_layers':sorted(set(grid.view['hidden_layers'])^{settings.minimum[1]})}
                elif self.action in ('mesh_preview','instance_preview'):view={'renderer':'instances' if self.action=='instance_preview' else 'mesh'}
                else:view={'slice_min':None,'slice_max':None,'isolate':None,'hidden_layers':[],'xray':False}
                args['view']=view;self.action='set_view'
            elif self.action=='load_resource_pack':args['path']=bpy.path.abspath(settings.resource_path)
            elif self.action=='define_component':args.update(name=settings.component_name,minimum=list(settings.minimum),maximum=list(settings.maximum))
            elif self.action=='fit_export_region':args['name']=settings.region_name
            elif self.action=='region_from_selection':
                regions=[{'name':r.name,'origin':list(r.origin),'size':list(r.size)} for r in grid.regions if r.name!=settings.region_name]
                regions.append({'name':settings.region_name,'origin':list(settings.minimum),'size':[b-a+1 for a,b in zip(settings.minimum,settings.maximum)]})
                args['regions']=regions;self.action='set_regions'
            elif self.action in ("import_litematic", "export_litematic", "import_schem", "export_schem"):
                args["path"] = bpy.path.abspath(settings.path)
                settings.job_id=execute('start_io_job',{'command':self.action,**args})['job_id']
                settings.status='Background file job started'
                return {'FINISHED'}
            elif self.action=='cancel_job':
                args={'job_id':settings.job_id}
            elif self.action=='recover_snapshot':args={'path':bpy.path.abspath(settings.recovery_path)}
            elif self.action in ("start_bridge", "stop_bridge"):
                from . import bridge
                result = bridge.start() if self.action == "start_bridge" else bridge.stop()
                settings.status = str(result)
                return {"FINISHED"}
            result = execute(self.action, args)
            settings.status = json.dumps(result, ensure_ascii=False)[:220]
        except Exception as exc:
            settings.status = str(exc)
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        return {"FINISHED"}

class M2B_OT_brush(bpy.types.Operator):
    bl_idname = "m2b_editor.brush"
    bl_label = "Block Brush"
    bl_description = "LMB place, Shift+LMB delete, Alt+LMB pick; Esc finish"

    def invoke(self, context, event):
        try:
            current(context)
        except ValueError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        context.window_manager.modal_handler_add(self)
        context.area.header_text_set("Minecraft: LMB place | Shift delete | Alt pick | Esc finish")
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        numbers=('ONE','TWO','THREE','FOUR','FIVE','SIX','SEVEN','EIGHT','NINE')
        if event.type in numbers and event.value=='PRESS':
            context.scene.m2b_editor.state=json.loads(context.scene.m2b_editor.hotbar)[numbers.index(event.type)]
            return {'RUNNING_MODAL'}
        if event.type == "ESC":
            context.area.header_text_set(None)
            return {"FINISHED"}
        if event.type != "LEFTMOUSE" or event.value != "PRESS":
            return {"PASS_THROUGH"}
        from bpy_extras import view3d_utils
        region=next(r for r in context.area.regions if r.type=='WINDOW')
        rv3d=context.space_data.region_3d
        if not rv3d:
            return {"PASS_THROUGH"}
        xy = (event.mouse_x-region.x,event.mouse_y-region.y)
        if not 0<=xy[0]<region.width or not 0<=xy[1]<region.height:return {'PASS_THROUGH'}
        origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, xy)
        direction = view3d_utils.region_2d_to_vector_3d(region, rv3d, xy)
        settings = context.scene.m2b_editor
        grid = current(context)
        if grid.view.get('renderer')=='instances':
            from .picking import raycast
            from .grid import mc_to_blender
            result=raycast(grid,LIBRARIES[tuple(grid.resource_packs)],blender_to_mc(origin),blender_to_mc(direction))
            if not result:return {'RUNNING_MODAL'}
            p=result['position'];location=mc_to_blender(result['location']);normal=mc_to_blender(result['normal'])
        else:
            hit, location, normal, face, obj, matrix = context.scene.ray_cast(context.evaluated_depsgraph_get(), origin, direction)
            if not hit or not obj.get('m2b_grid_id'):return {'RUNNING_MODAL'}
            settings.grid_id=obj['m2b_grid_id'];grid=current(context)
            p = tuple(obj.data.attributes["mc_"+axis].data[face].value for axis in "xyz")
        if event.alt:
            settings.state = grid.blocks[p].state
            settings.minimum = p
            return {"RUNNING_MODAL"}
        if not event.shift:
            n = blender_to_mc(normal)
            axis = max(range(3), key=lambda i: abs(n[i]))
            existing=grid.blocks[p]
            selected=SERVICE.registry.resolve(settings.state)
            slab_type=dict(existing.properties).get('type')
            merge_slab=selected.block_id==existing.block_id and existing.block_id.endswith('_slab') and axis==1 and ((slab_type=='bottom' and n[1]>0) or (slab_type=='top' and n[1]<0))
            if not merge_slab:p = tuple(p[i] + ((1 if n[i] > 0 else -1) if i == axis else 0) for i in range(3))
        try:
            args={"grid_id":grid.id,"expected_revision":grid.revision,"position":list(p),"state":"minecraft:air" if event.shift else settings.state}
            if not event.shift and settings.auto_orient:
                n=blender_to_mc(normal);look=blender_to_mc(direction)
                from .grid import DIRECTIONS
                clicked=max(DIRECTIONS,key=lambda d:sum(DIRECTIONS[d][i]*n[i] for i in range(3)))
                facing=max(('north','east','south','west'),key=lambda d:sum(DIRECTIONS[d][i]*look[i] for i in range(3)))
                hit=blender_to_mc(location)
                args['placement']={'clicked_face':clicked,'look':facing,**{'hit_'+a:hit[i]-math.floor(hit[i]) for i,a in enumerate('xyz')}}
            execute("place_block",args)
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
        return {"RUNNING_MODAL"}

class M2B_PT_editor(bpy.types.Panel):
    bl_label = "Minecraft Block Editor • 0.7.0 alpha"
    bl_idname = "M2B_PT_editor"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MC Editor"

    def draw(self, context):
        activate_scene(context.scene)
        layout = self.layout
        s = context.scene.m2b_editor
        def button(where, text, action, value=""):
            op = where.operator("m2b_editor.command", text=text)
            op.action, op.value = action, value
        button(layout, "New Building", "create_grid")
        for g in SERVICE.grids.values():
            button(layout, ("● " if s.grid_id == g.id else "") + g.name + f" ({len(g.blocks)})", "select_grid", g.id)
        layout.prop(s, "search")
        if s.search:
            for item in SERVICE.registry.search(s.search, limit=8)["items"]:
                button(layout, item["id"].removeprefix("minecraft:"), "select_block", item["id"])
        layout.prop(s, "state")
        for field in s.state_fields:layout.prop(field,'value',text=field.key)
        slots=json.loads(s.hotbar)
        for start in (0,3,6):
            row=layout.row(align=True)
            for i in range(start,start+3):button(row,str(i+1)+' '+slots[i].split(':')[-1].split('[')[0].replace('_',' '),'hotbar_use',str(i))
        row=layout.row(align=True);row.prop(s,'hotbar_slot');button(row,'Store','hotbar_save')
        layout.prop(s, "minimum")
        layout.prop(s, "maximum")
        row = layout.row(align=True)
        button(row, "Place", "place_block")
        button(row, "Fill", "fill_region")
        layout.operator("m2b_editor.brush", text="Brush: Place / Delete / Pick")
        layout.prop(s,'auto_orient')
        layout.operator('m2b_editor.box_select')
        layout.prop(s,'show_selection')
        layout.label(text='Size: '+ ' × '.join(str(max(0,b-a+1)) for a,b in zip(s.minimum,s.maximum)))
        row = layout.row(align=True)
        button(row, "Undo Blocks", "undo")
        button(row, "Redo Blocks", "redo")
        layout.prop(s, "path")
        row = layout.row(align=True)
        button(row, "Import Litematic", "import_litematic")
        button(row, "Export Litematic", "export_litematic")
        row = layout.row(align=True)
        button(row, "Import Schem", "import_schem")
        button(row, "Export Schem", "export_schem")
        row = layout.row(align=True)
        button(row, "Start MCP Bridge", "start_bridge")
        button(row, "Stop", "stop_bridge")
        version = LIBRARY.resource_version if LIBRARY else "pending"
        layout.label(text="26.2 states / Preview: " + version, icon="INFO")
        if s.status:
            layout.label(text=s.status[:65])
        if s.job_id:
            from .jobs import JOBS
            job=JOBS.get(s.job_id)
            if job:layout.label(text='File job: '+job.status)
            button(layout,'Cancel file job','cancel_job')

class M2B_OT_box_select(bpy.types.Operator):
    bl_idname='m2b_editor.box_select'
    bl_label='Box Select Blocks'
    start=None
    def invoke(self,context,event):
        try:current(context)
        except ValueError:return {'CANCELLED'}
        self.start=None;context.window_manager.modal_handler_add(self)
        context.area.header_text_set('Drag a rectangle to select blocks; Esc cancel')
        return {'RUNNING_MODAL'}
    def modal(self,context,event):
        if event.type=='ESC':context.area.header_text_set(None);return {'CANCELLED'}
        if event.type=='LEFTMOUSE' and event.value=='PRESS':self.start=(event.mouse_x,event.mouse_y);return {'RUNNING_MODAL'}
        if event.type=='LEFTMOUSE' and event.value=='RELEASE' and self.start:
            from bpy_extras.view3d_utils import location_3d_to_region_2d
            from mathutils import Vector
            from .grid import mc_to_blender
            region=next(r for r in context.area.regions if r.type=='WINDOW');rv=context.space_data.region_3d
            x0,x1=sorted((self.start[0]-region.x,event.mouse_x-region.x));y0,y1=sorted((self.start[1]-region.y,event.mouse_y-region.y))
            selected=[]
            for p in current(context).blocks:
                q=location_3d_to_region_2d(region,rv,Vector(mc_to_blender(tuple(v+0.5 for v in p))))
                if q is not None and x0<=q.x<=x1 and y0<=q.y<=y1:selected.append(p)
            if selected:
                s=context.scene.m2b_editor;s.minimum=tuple(min(p[i] for p in selected) for i in range(3));s.maximum=tuple(max(p[i] for p in selected) for i in range(3))
                s.status=f'Selected bounds of {len(selected)} blocks'
            context.area.header_text_set(None);return {'FINISHED'}
        return {'PASS_THROUGH'}

class M2B_PT_tools(bpy.types.Panel):
    bl_label='Selection / Transform / Sections'
    bl_idname='M2B_PT_tools'
    bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='MC Editor'
    def draw(self,context):
        activate_scene(context.scene)
        l=self.layout;s=context.scene.m2b_editor
        def buttons(items):
            row=l.row(align=True)
            for text,action in items:row.operator('m2b_editor.command',text=text).action=action
        l.prop(s,'replace_state');buttons([('Replace','replace_blocks')])
        buttons([('Copy','copy_selection'),('Paste at From','paste_selection')])
        l.prop(s,'pivot');l.prop(s,'offset');l.prop(s,'turns');l.prop(s,'move')
        buttons([('Rotate','rotate'),('Mirror X','mirror_x'),('Mirror Z','mirror_z')])
        l.prop(s,'copies');buttons([('Array','array'),('Translate','translate')])
        l.separator();l.prop(s,'slice_min');l.prop(s,'slice_max')
        buttons([('Section','slice'),('All','show_all')]);buttons([('Isolate','isolate'),('X-Ray','xray'),('Layer','hide_layer')])
        l.prop(s,'component_name');buttons([('Name component','define_component')])
        l.prop(s,'region_name');buttons([('Region from Selection','region_from_selection'),('Fit All','fit_export_region')])
        if s.grid_id in SERVICE.grids:
            grid=SERVICE.grids[s.grid_id]
            lo,hi=s.minimum,s.maximum
            size=tuple(hi[i]-lo[i]+1 for i in range(3))
            l.label(text=f'Selection: {size[0]} × {size[1]} × {size[2]}')
            l.label(text=f'Blocks: {len(grid.blocks):,} / Revision: {grid.revision}')
        l.prop(s,'resource_path');buttons([('Load Resource Pack','load_resource_pack')])
        buttons([('Mesh Preview','mesh_preview'),('Instance Preview','instance_preview')])
        buttons([('Recalculate Connections','recalculate_connections')])
        l.prop(s,'autosave');buttons([('Save Recovery Now','save_recovery')])
        l.prop(s,'recovery_path');buttons([('Recover as New Grids','recover_snapshot')])

CLASSES = (M2BStateField,M2BEditorSettings, M2B_OT_command, M2B_OT_brush,M2B_OT_box_select, M2B_PT_editor,M2B_PT_tools)
def deferred_restore():
    load_post(None)
    return None

def recovery_folder():
    return bpy.utils.user_resource('DATAFILES',path='Mine2Blend/recovery',create=True)

def scene_id(scene):
    if 'm2b_scene_id' not in scene:scene['m2b_scene_id']=uuid.uuid4().hex
    identity=scene['m2b_scene_id'];key=scene.as_pointer()
    owner=SCENE_IDENTITIES.get(identity)
    if owner is not None and owner!=key:
        source=next((s for s in bpy.data.scenes if s.as_pointer()==owner),None)
        if source is not None:
            # Blender scene copies share custom properties and often collections.
            # Snapshot live data, then give the copy independent grid/render IDs.
            payload=[g.to_dict() for g in SCENE_GRIDS[owner].values()] if owner in SCENE_GRIDS else json.loads(scene.get('m2b_editor_data','[]'))
            previous=scene.m2b_editor.grid_id;grids={};selected=''
            for data in payload:
                grid=BlockGrid.from_dict(data);old=grid.id;grid.id=uuid.uuid4().hex
                grids[grid.id]=grid;grid.dirty.update(grid.chunks)
                if old==previous:selected=grid.id
            scene['m2b_scene_id']=uuid.uuid4().hex;identity=scene['m2b_scene_id']
            SCENE_GRIDS[key]=grids;scene.m2b_editor.grid_id=selected or next(iter(grids),'')
            for collection in list(scene.collection.children):
                if collection.name.startswith('M2B Grid '):scene.collection.children.unlink(collection)
            with bpy.context.temp_override(scene=scene):
                for grid in grids.values():refresh(grid,scene)
            persist(scene,force=True)
    SCENE_IDENTITIES[identity]=key
    return scene['m2b_scene_id']

def background_tick():
    global LAST_AUTOSAVE
    from . import jobs,recovery
    scenes={s.as_pointer():s for s in bpy.data.scenes}
    from . import persistence
    for key in list(persistence.PENDING):
        value=persistence.collect(key)
        if value is not None and key in scenes:
            scenes[key]['m2b_editor_data']=value
            persist(scenes[key])
    for key,future in list(RECOVERY_PENDING.items()):
        if not future.done():continue
        RECOVERY_PENDING.pop(key)
        try:future.result()
        except Exception as exc:
            from .logging_utils import configure
            configure().exception('Automatic recovery snapshot failed')
            if key in scenes:scenes[key].m2b_editor.status='Recovery error: '+str(exc)
    for job in list(jobs.JOBS.values()):
        if job.status=='ready' and not job.applied:
            owner=scenes.get(job.owner)
            if owner is None:job.status='failed';job.error='Target scene was removed';continue
            grid=job.result;SCENE_GRIDS.setdefault(job.owner,{})[grid.id]=grid
            owner.m2b_editor.grid_id=grid.id
            try:
                # Rebuild uses current scene collection linking; link explicitly to owner below.
                if owner==bpy.context.scene:refresh(grid,owner)
                else:
                    grid.dirty.update(grid.chunks);persist(owner)
                job.result={'grid_id':grid.id,'block_count':len(grid.blocks)};job.applied=True;job.status='completed'
            except Exception as exc:
                persist(owner)
                job.result={'grid_id':grid.id,'block_count':len(grid.blocks),'preview_warning':str(exc)}
                job.applied=True;job.status='completed'
    for key,library in list(RENDER_QUEUE.items()):
        owner=scenes.get(key[0]);grid=SCENE_GRIDS.get(key[0],{}).get(key[1])
        if owner is None or grid is None:RENDER_QUEUE.pop(key,None);continue
        if owner!=bpy.context.scene:continue
        try:rebuild(grid,library,max_chunks=2)
        except Exception as exc:owner.m2b_editor.status='Preview error: '+str(exc);RENDER_QUEUE.pop(key,None)
        if not grid.dirty:RENDER_QUEUE.pop(key,None)
        break
    active=bpy.context.scene
    for grid in SCENE_GRIDS.get(active.as_pointer(),{}).values():
        if grid.dirty and (active.as_pointer(),grid.id) not in RENDER_QUEUE:
            try:refresh(grid,active)
            except Exception as exc:active.m2b_editor.status=str(exc)
            break
    now=time.monotonic()
    if now-LAST_AUTOSAVE>60:
        LAST_AUTOSAVE=now
        for scene in bpy.data.scenes:
            grids=SCENE_GRIDS.get(scene.as_pointer(),{})
            if grids and scene.m2b_editor.autosave and scene.as_pointer() not in RECOVERY_PENDING:
                snapshots=persistence.snapshots(list(grids.values()))
                RECOVERY_PENDING[scene.as_pointer()]=jobs.POOL.submit(recovery.save,snapshots,recovery_folder(),scene_id(scene))
    return 0.1

def register():
    from .logging_utils import configure
    configure().info('Editor registered')
    from . import overlay
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.m2b_editor = PointerProperty(type=M2BEditorSettings)
    overlay.register()
    bpy.app.handlers.load_post.append(load_post)
    bpy.app.handlers.save_pre.append(save_pre)
    bpy.app.handlers.undo_pre.append(native_undo_pre)
    bpy.app.handlers.redo_pre.append(native_undo_pre)
    bpy.app.handlers.undo_post.append(native_undo_post)
    bpy.app.handlers.redo_post.append(native_undo_post)
    bpy.app.timers.register(background_tick,first_interval=1,persistent=True)
    if getattr(bpy.context, "scene", None) is None:
        bpy.app.timers.register(deferred_restore, first_interval=0.1)
    else:
        load_post(None)

def unregister():
    from . import bridge
    from . import overlay
    overlay.unregister()
    from . import persistence
    persistence.stop()
    bridge.stop()
    if bpy.app.timers.is_registered(background_tick):bpy.app.timers.unregister(background_tick)
    if bpy.app.timers.is_registered(deferred_restore):
        bpy.app.timers.unregister(deferred_restore)
    for handlers, fn in ((bpy.app.handlers.load_post, load_post), (bpy.app.handlers.save_pre, save_pre),
                         (bpy.app.handlers.undo_pre, native_undo_pre), (bpy.app.handlers.redo_pre, native_undo_pre),
                         (bpy.app.handlers.undo_post, native_undo_post), (bpy.app.handlers.redo_post, native_undo_post)):
        if fn in handlers:
            handlers.remove(fn)
    del bpy.types.Scene.m2b_editor
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
