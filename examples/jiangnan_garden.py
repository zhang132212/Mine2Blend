"""48x48 offline garden built through Mine2Blend's transactional BlockGrid."""
from pathlib import Path
import sys, importlib.util, math, json, random
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/jiangnan-garden';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'.venv/Lib/site-packages'))
spec=importlib.util.spec_from_file_location('mcblock_mine2blend',ROOT/'__init__.py',submodule_search_locations=[str(ROOT)])
addon=importlib.util.module_from_spec(spec);sys.modules[spec.name]=addon;spec.loader.exec_module(addon);addon.register()
from mcblock_mine2blend.editor import blender_ui as ui
from mcblock_mine2blend.editor import formats
for obj in list(bpy.data.objects):bpy.data.objects.remove(obj,do_unlink=True)
g=ui.execute('create_grid',{'name':'听荷园 · Jiangnan Garden'})
grid=ui.SERVICE.grids[g['grid_id']];r=ui.SERVICE.registry
blocks={};cache={};rng=random.Random(48)
def put(x,y,z,s):
    assert 0<=x<48 and 0<=z<48,(x,y,z)
    if s not in cache:cache[s]=r.resolve('minecraft:'+s)
    blocks[(x,y,z)]=cache[s]
def fill(x1,y1,z1,x2,y2,z2,s):
    for x in range(x1,x2+1):
        for y in range(y1,y2+1):
            for z in range(z1,z2+1):put(x,y,z,s)
def component(name,lo,hi,kind,description):
    grid.components[name]={'bounds':[lo,hi],'type':kind,'description':description}
def lantern(x,y,z):
    put(x,y+1,z,'iron_chain[axis=y]');put(x,y,z,'lantern[hanging=true]')
def pillar(x,z,top=7):
    put(x,2,z,'chiseled_stone_bricks');fill(x,3,z,x,top,z,'dark_oak_log[axis=y]')
def roof(x1,x2,z1,z2,y):
    # Grey tiled double-pitch roof, ridge runs east-west; raised corner tips.
    mid=(z1+z2)//2
    for z in range(z1,z2+1):
        h=y+min(z-z1,z2-z)
        facing='south' if z<=mid else 'north'
        for x in range(x1,x2+1):
            put(x,h,z,'deepslate_tile_stairs[facing='+facing+']')
            if x in (x1,x2):put(x,h+1,z,'deepslate_tile_slab[type=bottom]')
    fill(x1,y+min(mid-z1,z2-mid)+1,mid,x2,y+min(mid-z1,z2-mid)+1,mid,'polished_blackstone_brick_slab')
    for x in (x1,x2):
        for z in (z1,z2):put(x,y+1,z,'deepslate_tile_stairs[facing='+('east' if x==x1 else 'west')+']')
def house(name,x1,x2,z1,z2):
    fill(x1,2,z1,x2,2,z2,'smooth_stone')
    fill(x1+1,2,z1+1,x2-1,2,z2-1,'spruce_planks')
    for z in (z1,z2):fill(x1,3,z,x2,6,z,'white_concrete')
    for x in (x1,x2):fill(x,3,z1,x,6,z2,'white_concrete')
    for z in (z1,z2):
        for x in (x1,(x1+x2)//2,x2):pillar(x,z)
        fill(x1,7,z,x2,7,z,'dark_oak_log[axis=x]')
    for x in (x1,x2):fill(x,7,z1,x,7,z2,'dark_oak_log[axis=z]')
    # Recessed lattice windows: solid sill and lintel, fence mullions.
    for x in (x1+2,x2-4):
        for z in (z1,z2):
            fill(x,4,z,x+2,5,z,'dark_oak_fence')
            fill(x,3,z,x+2,3,z,'dark_oak_trapdoor[facing=south,half=top]')
    for x in (x1,x2):fill(x,4,z1+3,x,5,z2-3,'dark_oak_fence')
    door=(x1+x2)//2
    fill(door-1,3,z2,door+1,5,z2,'air')
    fill(door-1,2,z2+1,door+1,2,z2+1,'stone_brick_stairs[facing=north]')
    # Bracket arms supporting the extended eaves.
    for x in (x1,x2):
        for z in (z1,z2):
            put(x-1,7,z,'dark_oak_stairs[facing=east,half=top]')
            put(x+1,7,z,'dark_oak_stairs[facing=west,half=top]')
            put(x,7,z+(-1 if z==z1 else 1),'dark_oak_stairs[facing='+('south' if z==z1 else 'north')+',half=top]')
    roof(x1-1,x2+1,z1-1,z2+1,8)
    for x in (door-2,door+2):lantern(x,5,z2+1)
    component(name,[x1-1,2,z1-1],[x2+1,15,z2+1],'building','白墙黛瓦、木构窗棂、挑檐斗拱')

# Foundation and landscaped ground; all coordinates are local schematic MC XYZ.
fill(0,0,0,47,0,47,'stone')
fill(0,1,0,47,1,47,'grass_block')
for x in range(48):
    for z in range(48):
        if x in (0,47) or z in (0,47):put(x,1,z,'stone_bricks')
# Low white enclosure with tiled cap; broad opening on the south.
for z in (1,46):
    fill(1,2,z,46,4,z,'white_concrete');fill(1,5,z,46,5,z,'deepslate_tile_slab')
for x in (1,46):
    fill(x,2,2,x,4,45,'white_concrete');fill(x,5,2,x,5,45,'deepslate_tile_slab')
fill(21,2,46,26,5,46,'air')
for x in (20,27):fill(x,2,45,x,6,46,'dark_oak_log')
roof(19,28,44,47,7)
for x in (21,26):lantern(x,5,45)
# Perforated garden wall windows.
for z in (10,19,34,41):
    for x in (1,46):fill(x,3,z,x,4,z+2,'dark_oak_fence')

# Paths form a loop linking all buildings and bridge landings.
def path(x1,z1,x2,z2):
    for x in range(x1,x2+1):
        for z in range(z1,z2+1):put(x,2,z,'andesite' if (x+z)%5==0 else 'stone_bricks')
path(21,39,26,47);path(8,38,39,41);path(8,14,33,17);path(8,17,11,39);path(38,15,41,39)
path(11,27,36,31);path(20,11,27,17)

# Irregular lotus pool, stone shore and deep water rather than a blue floor.
pool=set()
for x in range(14,37):
    for z in range(19,38):
        if ((x-25)/11.5)**2+((z-28)/9.2)**2<1 and not (x<19 and z<24):pool.add((x,z))
for x,z in pool:
    put(x,0,z,'clay');put(x,1,z,'water[level=0]');put(x,2,z,'air')
for x,z in pool:
    for dx,dz in ((1,0),(-1,0),(0,1),(0,-1)):
        if (x+dx,z+dz) not in pool:put(x+dx,2,z+dz,'mossy_stone_brick_slab')
for x,z in sorted(pool):
    if z not in range(27,32) and rng.random()<.10:put(x,2,z,'lily_pad')
for x,z in ((20,23),(29,21),(30,34),(21,35)):
    put(x,1,z,'moss_block');put(x,2,z,'pink_petals[flower_amount=4]')
component('lotus_pool',[13,0,18],[37,3,38],'landscape','曲岸荷池，睡莲与花岛；水体深一格')

house('study',4,18,4,12)
house('guest_house',29,42,4,12)
# Study: book wall, writing desk, low stools and plants.
fill(5,3,5,5,5,10,'bookshelf');fill(6,3,5,11,5,5,'bookshelf')
fill(10,3,8,14,3,8,'spruce_slab[type=top]')
put(11,4,8,'lectern[facing=south,has_book=false]');put(14,4,8,'potted_bamboo')
for x in (10,13):put(x,3,10,'dark_oak_stairs[facing=north]')
fill(7,3,7,7,3,9,'red_carpet')
lantern(15,5,6)
component('study_furniture',[5,3,5],[17,6,11],'interior','书墙、书案、讲台书托、坐凳、盆竹与灯笼')
# Guest suites separated by wooden screens.
fill(35,3,5,35,5,9,'dark_oak_fence')
for x in (31,38):
    put(x,3,6,'white_bed[facing=north,part=foot]');put(x,3,5,'white_bed[facing=north,part=head]')
    put(x+2,3,5,'barrel[facing=up]');put(x+2,4,5,'lantern')
    fill(x,3,8,x+2,3,9,'brown_carpet')
    put(x+2,3,10,'spruce_slab[type=top]');put(x+2,4,10,'potted_fern')
component('guest_furniture',[30,3,5],[41,6,11],'interior','双客房：床铺、行李柜、屏风、案几与灯')

# Open waterside tea pavilion, with benches and a stone Go table.
fill(35,2,23,43,2,33,'stone_bricks');fill(36,2,24,42,2,32,'spruce_planks')
for x in (35,43):
    for z in (23,33):pillar(x,z,7)
for z in (23,33):fill(35,7,z,43,7,z,'dark_oak_log[axis=x]')
for x in (35,43):fill(x,7,23,x,7,33,'dark_oak_log[axis=z]')
roof(34,44,22,34,8)
for z in (24,32):fill(37,3,z,41,3,z,'dark_oak_stairs[facing='+('south' if z==24 else 'north')+']')
for x in (35,43):
    for z in (24,25,31,32):put(x,3,z,'dark_oak_fence')
for x in (38,40):
    for z in (27,29):put(x,3,z,'dark_oak_fence')
for x in range(38,41):
    for z in range(27,30):put(x,4,z,'smooth_quartz_slab[type=top]' if (x+z)%2 else 'polished_blackstone_slab[type=top]')
for x,z in ((37,28),(41,28)):put(x,3,z,'dark_oak_slab')
put(42,3,26,'barrel');put(42,4,26,'flower_pot')
for z in (25,31):lantern(36,5,z)
component('tea_pavilion',[34,2,22],[44,16,34],'building','临水敞亭、棋桌、茶案、靠背坐凳')

# Covered bent corridor around west and north pool shores.
def corridor_x(x1,x2,z):
    fill(x1,2,z-1,x2,2,z+1,'smooth_stone')
    for x in range(x1,x2+1,4):
        for zz in (z-1,z+1):pillar(x,zz,5)
        lantern(x,4,z)
        fill(x,6,z,x,7,z,'iron_chain[axis=y]')
    for zz in (z-1,z+1):fill(x1,5,zz,x2,5,zz,'dark_oak_log[axis=x]')
    roof(x1,x2,z-2,z+2,6)
def corridor_z(x,z1,z2):
    fill(x-1,2,z1,x+1,2,z2,'smooth_stone')
    for z in range(z1,z2+1,4):
        for xx in (x-1,x+1):pillar(xx,z,5)
        lantern(x,4,z)
        fill(x,6,z,x,7,z,'iron_chain[axis=y]')
    for xx in (x-1,x+1):fill(xx,5,z1,xx,5,z2,'dark_oak_log[axis=z]')
    for xx in range(x-2,x+3):
        y=6+2-abs(xx-x)
        fill(xx,y,z1,xx,y,z2,'deepslate_tile_stairs[facing='+('east' if xx<=x else 'west')+']')
corridor_x(7,32,16);corridor_z(7,18,35);corridor_x(7,13,35)
component('winding_corridor',[5,2,14],[32,9,37],'circulation','折转曲廊，廊柱与悬灯，连接书斋与园路')

# Gently arched stone bridge; deck rises by half-block steps, rail piers.
for x in range(13,36):
    rise=min(x-13,35-x)//3
    rise=min(rise,2)
    for z in range(28,31):put(x,2+rise,z,'stone_brick_slab[type=top]')
    if x in (16,19,29,32):
        for z in range(28,31):put(x,2+rise,z,'stone_brick_stairs[facing='+('east' if x<25 else 'west')+']')
    for z in (27,31):
        put(x,2+rise,z,'stone_bricks')
        put(x,3+rise,z,'stone_brick_wall')
    if x in (14,19,25,30,34):
        for z in (27,31):put(x,4+rise,z,'chiseled_stone_bricks');put(x,5+rise,z,'stone_brick_slab')
component('stone_bridge',[13,2,27],[35,7,31],'circulation','三格宽拱桥，石栏与栏柱，横跨荷池抵茶亭')

# Garden stones, bamboo groves, pines and small flower borders.
for cx,cz in ((14,21),(33,36),(17,38),(4,32)):
    for dx,dz,h in ((0,0,4),(1,0,2),(0,1,3),(-1,1,1),(1,1,1)):
        fill(cx+dx,2,cz+dz,cx+dx,1+h,cz+dz,'mossy_cobblestone' if (dx+dz)%2 else 'andesite')
def pine(x,z,height=6):
    fill(x,2,z,x,2+height,z,'spruce_log')
    for y,rad in ((height,3),(height+2,2),(height+3,1)):
        for dx in range(-rad,rad+1):
            for dz in range(-rad,rad+1):
                if abs(dx)+abs(dz)<=rad+1 and (dx or dz):put(x+dx,y,z+dz,'spruce_leaves[persistent=true]')
    put(x,height+4,z,'spruce_leaves[persistent=true]')
pine(7,42,6);pine(40,41,7);pine(23,7,6)
for x,z in ((3,17),(4,19),(3,22),(4,24),(43,16),(44,18),(43,20),(30,42),(32,43)):
    for y in range(2,6+(x+z)%3):put(x,y,z,'bamboo[leaves='+('large' if y>=4 else 'none')+']')
for x in range(13,20):
    put(x,2,42,'moss_block');put(x,3,42,'azalea' if x%3==0 else 'poppy')
for x,z in ((12,19),(12,36),(36,38),(29,40),(18,43)):
    put(x,2,z,'stone_bricks');put(x,3,z,'stone_brick_wall');put(x,4,z,'lantern')
component('garden_details',[2,2,15],[45,12,44],'landscape','叠石、松竹、花境、石灯及院墙漏窗')
component('entry_gate',[19,2,44],[28,10,47],'building','南侧园门，挑檐双灯')

# Publish one atomic plugin transaction; neighbor models are derived by the editor.
ui.SERVICE.commit(grid,blocks.items(),grid.revision,True)
grid.view['renderer']='instances'
bpy.context.scene.m2b_editor.grid_id=grid.id
bpy.context.scene.m2b_editor.autosave=False
while grid.dirty:stats=ui.refresh(grid,bpy.context.scene)
ui.persist(bpy.context.scene,force=True)
formats.export_litematic(grid,OUT/'听荷园-48x48.litematic')
loaded=formats.import_litematic(OUT/'听荷园-48x48.litematic')
assert loaded.blocks==grid.blocks,'Export roundtrip mismatch'
assert grid.bounds[0][0]==0 and grid.bounds[1][0]==47 and grid.bounds[1][2]==47
assert not stats['missing_models'],stats
(OUT/'blockgrid.json').write_text(json.dumps(grid.to_dict(),ensure_ascii=False),encoding='utf-8')
(OUT/'materials.json').write_text(json.dumps(grid.summary(),ensure_ascii=False,indent=2),encoding='utf-8')

scene=bpy.context.scene
world=scene.world;world.use_nodes=True
world.node_tree.nodes['Background'].inputs['Color'].default_value=(0.63,0.72,0.79,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.65
bpy.ops.object.light_add(type='SUN',location=(5,15,60));sun=bpy.context.object
sun.rotation_euler=(math.radians(25),math.radians(-20),math.radians(-25));sun.data.energy=2.6;sun.data.angle=.12
bpy.ops.object.camera_add();camera=bpy.context.object;scene.camera=camera
camera.data.type='ORTHO';camera.data.lens=45;camera.data.clip_end=1000
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.resolution_x=1600;scene.render.resolution_y=1400;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
def view(location,target,scale,file):
    camera.location=location;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=scale
    scene.render.filepath=str(OUT/file);bpy.ops.render.render(write_still=True)
# View from south-west; south is positive MC Z, hence negative Blender Y.
view((-30,-82,67),(23,-24,4),72,'听荷园-总览.png')
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        area.spaces.active.region_3d.view_perspective='CAMERA';area.spaces.active.shading.type='MATERIAL';area.spaces.active.show_region_ui=True
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'听荷园-48x48.blend'))
view((13,-53,27),(26,-26,4),40,'听荷园-荷池茶亭.png')
# Interior cutaway is preview only; never remove blocks from the source/export.
grid.view['slice_max']=5;grid.dirty.update(grid.chunks)
while grid.dirty:ui.refresh(grid,bpy.context.scene)
scene.render.resolution_x=1500;scene.render.resolution_y=900
view((23,-37,48),(23,-8,2),44,'听荷园-室内剖视.png')
print('JIANGNAN_GARDEN_OK',json.dumps({'blocks':len(grid.blocks),'bounds':grid.bounds,'components':list(grid.components),'output':str(OUT)},ensure_ascii=False))
addon.unregister()
