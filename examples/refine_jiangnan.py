"""Refine the saved garden through its BlockGrid, retaining all other content."""
from pathlib import Path
import sys,json,math
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/jiangnan-garden'
from bl_ext.user_default.mcblock_mine2blend.editor import blender_ui as ui,formats
bpy.ops.wm.open_mainfile(filepath=str(OUT/'听荷园-48x48.blend'))
ui.activate_scene(bpy.context.scene)
grid=next(iter(ui.SERVICE.grids.values()));original=dict(grid.blocks)
r=ui.SERVICE.registry;changes={};cache={}
def put(x,y,z,s):
    if s not in cache:cache[s]=r.resolve('minecraft:'+s)
    changes[(x,y,z)]=cache[s]
def fill(x,y,z,xx,yy,zz,s):
    for a in range(x,xx+1):
        for b in range(y,yy+1):
            for c in range(z,zz+1):put(a,b,c,s)
# Follow the exact underside of the existing pitched roofs.
for x1,x2,z1,z2,plaster in ((4,18,4,12,True),(29,42,4,12,True),(35,43,23,33,False)):
    for x in (x1,x2):
        for z in range(z1,z2+1):
            underside=8+min(z-(z1-1),(z2+1)-z)-1
            fill(x,8,z,x,underside,z,'white_concrete' if plaster else 'dark_oak_planks')
            put(x,underside,z,'dark_oak_log[axis=z]')
        center=(z1+z2)//2
        top=8+min(center-z1+1,z2+1-center)-1
        fill(x,8,center,x,top,center,'dark_oak_log[axis=y]')
    grid.components['study' if x1==4 else 'guest_house' if x1==29 else 'tea_pavilion']['description']+='；封闭山墙与沿坡木质收边'
# Close corridor roof end triangles above the lintels; keep the walkway open.
for x in (7,32):
    for z in range(15,18):
        top=6+min(z-14,18-z)-1
        fill(x,6,z,x,top,z,'dark_oak_planks')
# Continuous grey base courses and small coping piers segment the white wall.
for z in (1,46):
    for x in range(1,47):
        if z==46 and 20<=x<=27:continue
        put(x,2,z,'stone_bricks')
for x in (1,46):fill(x,2,2,x,2,45,'stone_bricks')
for z in (1,46):
    for x in (1,12,18,29,35,46):
        put(x,2,z,'chiseled_stone_bricks')
        fill(x,3,z,x,4,z,'polished_andesite')
        put(x,5,z,'deepslate_tiles');put(x,6,z,'deepslate_tile_slab')
for x in (1,46):
    for z in (8,16,25,32,39):
        put(x,2,z,'chiseled_stone_bricks');fill(x,3,z,x,4,z,'polished_andesite')
        put(x,5,z,'deepslate_tiles');put(x,6,z,'deepslate_tile_slab')
# Framed south-wall lattice panels; stone mullions punctuate the long facade.
for start in (5,13,30,38):
    for x in range(start,start+5):
        for y in (3,4):put(x,y,46,'dark_oak_fence')
        put(x,2,46,'polished_andesite');put(x,5,46,'polished_deepslate_slab')
    for x in (start-1,start+5):fill(x,3,46,x,4,46,'polished_andesite')
# Grey sills and narrow lintels frame existing side-wall pierced windows.
for x in (1,46):
    for z in (10,19,34,41):
        fill(x,2,z,x,2,z+2,'polished_andesite')
        fill(x,5,z,x,5,z+2,'polished_deepslate_slab')
        for zz in (z-1,z+3):fill(x,3,zz,x,4,zz,'polished_andesite')
grid.components['enclosure_details']={'bounds':[[1,2,1],[46,6,46]],'type':'enclosure','description':'灰砖墙脚、分段墙柱、压顶、石框木格漏窗；保留南园门'}
result=ui.SERVICE.commit(grid,changes.items(),grid.revision,True)
while grid.dirty:stats=ui.refresh(grid,bpy.context.scene)
assert not stats['missing_models'],stats
ui.persist(bpy.context.scene,force=True)
formats.export_litematic(grid,OUT/'听荷园-48x48-修订版.litematic')
assert formats.import_litematic(OUT/'听荷园-48x48-修订版.litematic').blocks==grid.blocks
(OUT/'blockgrid-修订版.json').write_text(json.dumps(grid.to_dict(),ensure_ascii=False),encoding='utf-8')
(OUT/'修订记录.json').write_text(json.dumps({'changes':result,'blocks':len(grid.blocks),'bounds':grid.bounds,'components':grid.components},ensure_ascii=False,indent=2),encoding='utf-8')
scene=bpy.context.scene;camera=scene.camera
scene.cycles.samples=16;scene.render.resolution_x=1400;scene.render.resolution_y=1250
camera.location=(-30,-82,67);camera.rotation_euler=(Vector((23,-24,4))-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=72
scene.render.filepath=str(OUT/'听荷园-修订版总览.png')
# Set an immediately useful free viewport in the reopened file.
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            space=area.spaces.active;space.shading.type='MATERIAL';space.show_region_ui=True
            space.region_3d.view_location=Vector((23,-24,5));space.region_3d.view_distance=69
            space.region_3d.view_rotation=camera.rotation_euler.to_quaternion()
            space.region_3d.view_perspective='ORTHO'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'听荷园-48x48-修订版.blend'))
bpy.ops.render.render(write_still=True)
print('GARDEN_REFINED_OK',len(grid.blocks),result)
