"""Visual QA of actual 26.2 entity geometry, including post-1.19 additions."""
from pathlib import Path
import sys,importlib.util,json
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.venv/Lib/site-packages'))
spec=importlib.util.spec_from_file_location('mcblock_mine2blend',ROOT/'__init__.py',submodule_search_locations=[str(ROOT)])
addon=importlib.util.module_from_spec(spec);sys.modules[spec.name]=addon;spec.loader.exec_module(addon);addon.register()
from mcblock_mine2blend.editor import blender_ui as ui
from mcblock_mine2blend.editor.grid import Region
names=['copper_golem','armadillo','breeze','creaking','nautilus','camel','sniffer','bogged','zombie_nautilus','happy_ghast','pig','cow','sheep','bat','vex']
g=ui.execute('create_grid',{'name':'26.2 Entity Gallery'})
ui.execute('fill_region',{'grid_id':g['grid_id'],'expected_revision':0,'minimum':[-1,0,-1],'maximum':[30,0,18],'state':'minecraft:stone_bricks'})
grid=ui.SERVICE.grids[g['grid_id']]
tags=[]
for i,name in enumerate(names):
    x,z=(i%5)*6+2,(i//5)*6+2;y=5 if name=='happy_ghast' else 2 if name in ('bat','vex') else 1
    tags.append(f'{{id:"minecraft:{name}",Pos:[{x}d,{y}d,{z}d],Rotation:[30f,0f]}}')
grid.regions=[Region('Main',(-1,0,-1),(32,12,20),[])]
# Convert the explicitly placed world positions to this region's local frame.
import nbtlib as n
for text in tags:
    tag=n.parse_nbt(text);tag['Pos'][0]=n.Double(float(tag['Pos'][0])+1);tag['Pos'][2]=n.Double(float(tag['Pos'][2])+1);grid.regions[0].entities.append(tag.snbt())
result=ui.refresh(grid,bpy.context.scene);assert not result['entity_placeholders'],result
out=ROOT/'test-output';ui.execute('render_preview',{'grid_id':grid.id,'path':str(out/'entity-gallery-26.2.png'),'size':1200})
bpy.ops.wm.save_as_mainfile(filepath=str(out/'entity-gallery-26.2.blend'))
print('ENTITY_GALLERY_26_2_OK',json.dumps(names));addon.unregister()
