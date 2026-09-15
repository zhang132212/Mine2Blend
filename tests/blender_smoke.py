"""Actual Blender headless smoke + sample artifact. Run with --python-exit-code 1."""
from pathlib import Path
import sys
import json
import importlib.util
import math
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".venv/Lib/site-packages"))
spec = importlib.util.spec_from_file_location("mcblock_mine2blend", ROOT / "__init__.py", submodule_search_locations=[str(ROOT)])
addon = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = addon
spec.loader.exec_module(addon)
addon.register()
from mcblock_mine2blend.editor.blender_ui import execute, SERVICE, refresh
from mcblock_mine2blend.editor.grid import BlockRecord

for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
g = execute("create_grid", {"name":"26.2 Courtyard Demo"})
gid = g["grid_id"]
def fill(lo,hi,state):
    return execute("fill_region", {"grid_id":gid,"expected_revision":SERVICE.grids[gid].revision,
                                  "minimum":lo,"maximum":hi,"state":state})
fill([0,0,0],[18,0,14],"minecraft:stone_bricks")
for x in (1,17):
    for z in (1,13):
        fill([x,1,z],[x,6,z],"minecraft:oak_log")
for z in (1,13):
    fill([2,1,z],[16,3,z],"minecraft:cinnabar")
fill([1,1,2],[1,3,12],"minecraft:stone_bricks")
fill([17,1,2],[17,3,12],"minecraft:stone_bricks")
fill([8,1,1],[10,3,1],"minecraft:air")
fill([3,2,13],[6,3,13],"minecraft:glass")
fill([12,2,13],[15,3,13],"minecraft:glass")
for x in range(0,10):
    fill([x,7+x//2,0],[x,7+x//2,14],"minecraft:dark_oak_planks")
    fill([18-x,7+x//2,0],[18-x,7+x//2,14],"minecraft:dark_oak_planks")
grid = SERVICE.grids[gid]
stats = refresh(grid,bpy.context.scene)
assert stats["objects"] <= 4, stats
assert len(grid.blocks) > 500
out = ROOT / "test-output"
out.mkdir(exist_ok=True)
execute("export_litematic",{"grid_id":gid,"path":str(out/"courtyard-26.2.litematic")})

bpy.ops.object.camera_add(location=(30,25,24))
camera=bpy.context.object
from mathutils import Vector
camera.rotation_euler=(Vector((9,-7,5))-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.type='ORTHO'; camera.data.ortho_scale=33
bpy.context.scene.camera=camera
bpy.ops.object.light_add(type='SUN', location=(10,8,20))
bpy.context.object.rotation_euler=(math.radians(25),math.radians(-25),math.radians(25))
bpy.context.object.data.energy=3
scene=bpy.context.scene
scene.world.color=(0.3,0.3,0.3)
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(0.5,0.55,0.65,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=0.8
scene.render.engine='CYCLES'
scene.cycles.samples=12
scene.render.resolution_x=960; scene.render.resolution_y=720; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.filepath=str(out/'courtyard-preview.png')
bpy.ops.wm.save_as_mainfile(filepath=str(out/'courtyard.blend'))
bpy.ops.render.render(write_still=True)
bpy.ops.wm.open_mainfile(filepath=str(out/'courtyard.blend'))
assert gid in SERVICE.grids
assert len(SERVICE.grids[gid].blocks)==len(grid.blocks)
report={"blender":bpy.app.version_string,"blocks":len(grid.blocks),"render":stats,"persistence":"passed"}
(out/'blender-smoke.json').write_text(json.dumps(report,indent=2))
print('BLENDER_SMOKE_OK',json.dumps(report))
addon.unregister()
