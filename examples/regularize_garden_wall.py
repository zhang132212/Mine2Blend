"""One consistent nine-block pier rhythm around the garden enclosure."""
from pathlib import Path
import json
import bpy
from bl_ext.user_default.mcblock_mine2blend.editor import blender_ui as ui,formats
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/jiangnan-garden'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'听荷园-48x48-围墙对称版.blend'))
ui.activate_scene(bpy.context.scene);grid=next(iter(ui.SERVICE.grids.values()))
registry=ui.SERVICE.registry;changes={};cache={}
def put(x,y,z,state):
    if state not in cache:cache[state]=registry.resolve('minecraft:'+state)
    changes[(x,y,z)]=cache[state]
piers=list(range(1,47,9));report={}
for side in ('west','east','north','south'):
    def position(t,y):
        return (1 if side=='west' else 46,y,t) if side in ('west','east') else (t,y,1 if side=='north' else 46)
    def write(t,y,s):put(*position(t,y),s)
    # Replace the entire enclosure strip to remove every old extra mullion.
    for t in range(1,47):
        if side=='south' and 20<=t<=27:continue
        for y in range(2,7):
            write(t,y,'stone_bricks' if y==2 else 'white_concrete' if y<5 else 'deepslate_tile_slab' if y==5 else 'air')
    for t in piers:
        write(t,2,'chiseled_stone_bricks')
        for y in (3,4):write(t,y,'polished_andesite')
        write(t,5,'deepslate_tiles');write(t,6,'deepslate_tile_slab')
    windows=[]
    for start in piers[:-1]:
        if side=='south' and start==19:continue
        # Eight clear blocks per bay; a four-block window is exactly centered.
        for t in range(start+3,start+7):
            for y in (3,4):write(t,y,'dark_oak_fence')
            write(t,2,'polished_andesite')
        windows.append([start+3,start+6])
    report[side]={'pier_centers':piers,'spacing':9,'window_intervals':windows}
grid.components['enclosure_details']={'bounds':[[1,2,1],[46,6,46]],'type':'enclosure','description':'统一九格柱距、八格净墙段、居中四格木格漏窗；南侧中央保留园门'}
result=ui.SERVICE.commit(grid,changes.items(),grid.revision,True)
# Assert actual pier locations, not only the intended pattern.
for side in report:
    actual=[]
    for t in range(1,47):
        p=(1 if side=='west' else 46,3,t) if side in ('west','east') else (t,3,1 if side=='north' else 46)
        if grid.blocks.get(p) and grid.blocks[p].block_id=='minecraft:polished_andesite':actual.append(t)
    assert actual==piers,(side,actual)
    assert all(b-a==9 for a,b in zip(actual,actual[1:]))
while grid.dirty:stats=ui.refresh(grid,bpy.context.scene)
assert not stats['missing_models'],stats
ui.persist(bpy.context.scene,force=True)
name='听荷园-48x48-统一柱距版'
formats.export_litematic(grid,OUT/(name+'.litematic'))
assert formats.import_litematic(OUT/(name+'.litematic')).blocks==grid.blocks
(OUT/'围墙柱距检查.json').write_text(json.dumps({'walls':report,'transaction':result,'blocks':len(grid.blocks)},ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'blockgrid-统一柱距版.json').write_text(json.dumps(grid.to_dict(),ensure_ascii=False),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(name+'.blend')))
print('UNIFORM_WALL_SPACING_OK',result)
