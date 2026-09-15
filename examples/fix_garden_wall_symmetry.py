from pathlib import Path
import json
import bpy
from bl_ext.user_default.mcblock_mine2blend.editor import blender_ui as ui,formats
from bl_ext.user_default.mcblock_mine2blend.editor.transforms import state as transform_state
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/jiangnan-garden'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'听荷园-48x48-修订版.blend'))
ui.activate_scene(bpy.context.scene);grid=next(iter(ui.SERVICE.grids.values()))
# Mirror the existing right-hand facade about the entrance center x=23.5.
changes=[]
for x in range(1,24):
    for y in range(2,7):
        source=grid.blocks.get((47-x,y,46))
        changes.append(((x,y,46),transform_state(source,mirror='x') if source else None))
result=ui.SERVICE.commit(grid,changes,grid.revision,True)
for x in range(1,47):
    for y in range(2,7):
        a=grid.blocks.get((x,y,46));b=grid.blocks.get((47-x,y,46))
        assert a==(transform_state(b,mirror='x') if b else None),(x,y,a,b)
while grid.dirty:ui.refresh(grid,bpy.context.scene)
ui.persist(bpy.context.scene,force=True)
formats.export_litematic(grid,OUT/'听荷园-48x48-围墙对称版.litematic')
assert formats.import_litematic(OUT/'听荷园-48x48-围墙对称版.litematic').blocks==grid.blocks
(OUT/'blockgrid-围墙对称版.json').write_text(json.dumps(grid.to_dict(),ensure_ascii=False),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'听荷园-48x48-围墙对称版.blend'))
print('SOUTH_WALL_SYMMETRY_OK',result)
