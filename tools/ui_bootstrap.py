"""Launch a dedicated QA scene without replacing the user's existing Blender window."""
from pathlib import Path
import sys,importlib.util,math
import bpy
from mathutils import Vector,Quaternion
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'.venv/Lib/site-packages'))
spec=importlib.util.spec_from_file_location('mcblock_mine2blend',root/'__init__.py',submodule_search_locations=[str(root)])
addon=importlib.util.module_from_spec(spec);sys.modules[spec.name]=addon;spec.loader.exec_module(addon);addon.register()
from mcblock_mine2blend.editor.blender_ui import execute,SERVICE
for obj in list(bpy.data.objects):bpy.data.objects.remove(obj,do_unlink=True)
g=execute('create_grid',{'name':'Editor QA'})
execute('fill_region',{'grid_id':g['grid_id'],'expected_revision':0,'minimum':[-4,0,-4],'maximum':[12,0,12],'state':'minecraft:stone_bricks'})
execute('fill_region',{'grid_id':g['grid_id'],'expected_revision':1,'minimum':[0,1,0],'maximum':[7,1,0],'state':'minecraft:oak_fence'})
s=bpy.context.scene.m2b_editor;s.state='minecraft:oak_stairs';s.minimum=(0,1,2);s.maximum=(5,1,2)
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        space=area.spaces.active;space.show_region_ui=True;space.shading.type='MATERIAL'
        space.region_3d.view_location=Vector((4,-4,1));space.region_3d.view_distance=26
bpy.ops.wm.save_as_mainfile(filepath=str(root/'test-output/Editor-QA-0.7.blend'))
from mcblock_mine2blend.editor import bridge
bridge.start()
