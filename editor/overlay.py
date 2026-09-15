"""Viewport-only selection outline; never participates in schematic export."""
from .grid import mc_to_blender
HANDLE=None

def draw():
    import bpy,gpu
    from gpu_extras.batch import batch_for_shader
    context=bpy.context
    if not context.scene or not hasattr(context.scene,'m2b_editor'):return
    s=context.scene.m2b_editor
    if not s.show_selection or not s.grid_id:return
    lo,hi=s.minimum,s.maximum
    if any(a>b for a,b in zip(lo,hi)):return
    vertices=[mc_to_blender((hi[0]+1 if i&1 else lo[0],hi[1]+1 if i&2 else lo[1],hi[2]+1 if i&4 else lo[2])) for i in range(8)]
    edges=[(i,i^mask) for i in range(8) for mask in (1,2,4) if not i&mask]
    shader=gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
    batch=batch_for_shader(shader,'LINES',{'pos':vertices},indices=edges)
    shader.bind();shader.uniform_float('viewportSize',gpu.state.viewport_get()[2:]);shader.uniform_float('lineWidth',2);shader.uniform_float('color',(1,.6,.05,1))
    batch.draw(shader)

def register():
    import bpy
    global HANDLE
    if HANDLE is None:HANDLE=bpy.types.SpaceView3D.draw_handler_add(draw,(),'WINDOW','POST_VIEW')

def unregister():
    import bpy
    global HANDLE
    if HANDLE is not None:bpy.types.SpaceView3D.draw_handler_remove(HANDLE,'WINDOW');HANDLE=None
