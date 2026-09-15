"""Integration test for main-thread job publication, scene isolation and preview cleanup."""
from pathlib import Path
import sys,importlib.util,time,json
import bpy
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.venv/Lib/site-packages'))
spec=importlib.util.spec_from_file_location('mcblock_mine2blend',ROOT/'__init__.py',submodule_search_locations=[str(ROOT)])
addon=importlib.util.module_from_spec(spec);sys.modules[spec.name]=addon;spec.loader.exec_module(addon);addon.register()
from mcblock_mine2blend.editor import blender_ui as ui
out=ROOT/'test-output';out.mkdir(exist_ok=True)
first=bpy.context.scene;first.m2b_editor.autosave=False
gid=ui.execute('create_grid',{'name':'Workflow'})['grid_id']
ui.execute('fill_region',{'grid_id':gid,'expected_revision':0,'minimum':[0,0,0],'maximum':[4,1,4],'state':'minecraft:stone_bricks'})
snapshot=ui.execute('save_recovery',{})
# A global Blender undo must never reload a stale background JSON snapshot.
first['m2b_editor_data']='[]'
ui.native_undo_pre(None);ui.native_undo_post(None)
assert len(ui.SERVICE.grids[gid].blocks)==50
job=ui.execute('start_io_job',{'command':'export_litematic','grid_id':gid,'path':str(out/'workflow.litematic')})
def wait(job,ready=False):
    deadline=time.monotonic()+30
    while time.monotonic()<deadline:
        ui.background_tick()
        state=ui.execute('get_job_status',{'job_id':job['job_id']})
        if state['status'] in ('completed','failed','cancelled'):break
        time.sleep(.02)
    assert state['status']=='completed',state
    return state
wait(job)
second=bpy.data.scenes.new('Isolated');bpy.context.window.scene=second;second.m2b_editor.autosave=False
ui.activate_scene(second);assert gid not in ui.SERVICE.grids
job=ui.execute('start_io_job',{'command':'import_litematic','path':str(out/'workflow.litematic')})
state=wait(job);imported=state['result']['grid_id']
assert len(ui.SERVICE.grids[imported].blocks)==50
bpy.context.window.scene=first;ui.activate_scene(first)
assert gid in ui.SERVICE.grids and imported not in ui.SERVICE.grids
target=ui.scene_id(second)
args={'scene_id':target,'name':'Agent scoped grid','request_id':'workflow-agent-create'}
agent_grid=ui.execute('create_grid',args)
assert ui.execute('create_grid',args)==agent_grid
assert bpy.context.scene==first
assert len(ui.execute('list_grids',{'scene_id':target}))==2
ui.activate_scene(first)
camera=first.camera;scenes=set(bpy.data.scenes);objects=set(bpy.data.objects)
result=ui.execute('render_preview',{'grid_id':gid,'path':str(out/'workflow-preview.png'),'size':128})
assert Path(result['path']).is_file()
assert first.camera==camera and set(bpy.data.scenes)==scenes and set(bpy.data.objects)==objects
recovered=ui.execute('recover_snapshot',snapshot)['grid_ids'][0]
assert recovered!=gid and len(ui.SERVICE.grids[recovered].blocks)==50
bpy.ops.wm.save_as_mainfile(filepath=str(out/'workflows.blend'))
bpy.ops.wm.open_mainfile(filepath=str(out/'workflows.blend'))
assert gid in ui.SERVICE.grids
bpy.context.window.scene=bpy.data.scenes['Isolated'];ui.activate_scene(bpy.context.scene)
assert imported in ui.SERVICE.grids and gid not in ui.SERVICE.grids
print('BLENDER_WORKFLOWS_OK',json.dumps(result));addon.unregister()
