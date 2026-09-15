"""Render the default special block gallery using real 26.2 textures."""
from pathlib import Path
import sys,importlib.util,json
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.venv/Lib/site-packages'))
spec=importlib.util.spec_from_file_location('mcblock_mine2blend',ROOT/'__init__.py',submodule_search_locations=[str(ROOT)])
addon=importlib.util.module_from_spec(spec);sys.modules[spec.name]=addon;spec.loader.exec_module(addon);addon.register()
from mcblock_mine2blend.editor import blender_ui as ui
from mcblock_mine2blend.editor.render import ModelLibrary
g=ui.execute('create_grid',{'name':'26.2 Special Models'})
names=sorted(ModelLibrary().special)
rows=[{'position':[(i%12)*3,1,(i//12)*3],'state':'minecraft:'+name} for i,name in enumerate(names)]
ui.execute('apply_blocks',{'grid_id':g['grid_id'],'expected_revision':0,'auto_connect':False,'blocks':rows})
ui.execute('fill_region',{'grid_id':g['grid_id'],'expected_revision':1,'minimum':[-1,0,-1],'maximum':[35,0,38],'state':'minecraft:stone_bricks'})
out=ROOT/'test-output'
result=ui.execute('render_preview',{'grid_id':g['grid_id'],'path':str(out/'special-gallery.png'),'size':1200})
assert not result['missing_models'],result
bpy.ops.wm.save_as_mainfile(filepath=str(out/'special-gallery.blend'))
print('SPECIAL_GALLERY_OK',len(names));addon.unregister()
