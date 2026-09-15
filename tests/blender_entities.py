from pathlib import Path
import sys,importlib.util,json
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.venv/Lib/site-packages'))
spec=importlib.util.spec_from_file_location('mcblock_mine2blend',ROOT/'__init__.py',submodule_search_locations=[str(ROOT)])
addon=importlib.util.module_from_spec(spec);sys.modules[spec.name]=addon;spec.loader.exec_module(addon);addon.register()
from mcblock_mine2blend.editor import blender_ui as ui
from mcblock_mine2blend.editor.grid import Region
g=ui.execute('create_grid',{'name':'Entities'})
ui.execute('fill_region',{'grid_id':g['grid_id'],'expected_revision':0,'minimum':[0,0,0],'maximum':[8,0,4],'state':'minecraft:stone_bricks'})
grid=ui.SERVICE.grids[g['grid_id']]
grid.regions=[Region('Main',(0,0,0),(9,5,5),[f'{{id:"minecraft:{name}",Pos:[{x}.5d,1d,2.5d],Rotation:[30f,0f]}}' for x,name in ((1,'armor_stand'),(4,'pig'),(7,'copper_golem'))])]
grid.regions[0].entities.append('{id:"example:unknown_entity",Pos:[7.5d,1d,4.5d]}')
result=ui.refresh(grid,bpy.context.scene)
assert result['entity_placeholders']==['example:unknown_entity'],result
assert result['entity_chunks']==1
out=ROOT/'test-output';out.mkdir(exist_ok=True)
ui.execute('export_litematic',{'grid_id':grid.id,'path':str(out/'entities.litematic')})
ui.execute('render_preview',{'grid_id':grid.id,'path':str(out/'entities-preview.png'),'size':512})
assert sum(len(r.entities) for r in grid.regions)==4
print('BLENDER_ENTITIES_OK',json.dumps(result));addon.unregister()
