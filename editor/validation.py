"""Static construction diagnostics. No ticks, power propagation or entity physics."""
from .grid import DIRECTIONS
from .connections import derive,opposite,add

def orientations(grid,registry):
    issues=[]
    for p,block in grid.blocks.items():
        try:canonical=registry.resolve(block.state)
        except ValueError as exc:
            issues.append({'position':p,'code':'invalid_state','message':str(exc)});continue
        props=dict(canonical.properties)
        derived=derive(p,canonical,grid.blocks.get)
        if derived.properties!=canonical.properties:
            issues.append({'position':p,'code':'stale_connection','message':'Neighbor connection differs from the static rules','suggested_state':derived.state})
        if block.block_id.endswith('_door'):
            delta=(0,1 if props['half']=='lower' else -1,0);other=grid.blocks.get(add(p,delta))
            expected={**props,'half':'upper' if props['half']=='lower' else 'lower'}
            if not other or other.block_id!=block.block_id or any(dict(other.properties).get(k)!=v for k,v in expected.items()):
                issues.append({'position':p,'code':'door_pair','message':'Missing or inconsistent other door half'})
        if block.block_id.endswith('_bed'):
            facing=props['facing'];d=DIRECTIONS[facing if props['part']=='foot' else opposite(facing)];other=grid.blocks.get(add(p,d))
            if not other or other.block_id!=block.block_id or dict(other.properties).get('facing')!=facing or dict(other.properties).get('part')==props['part']:
                issues.append({'position':p,'code':'bed_pair','message':'Missing or inconsistent bed half'})
    return {'revision':grid.revision,'issues':issues[:1000],'total':len(issues),'scope':'26.2 properties, static connections and door/bed pairs; no tick simulation'}

def support(grid,library):
    from .occlusion import covered
    issues=[]
    def full_top(block):return bool(block and covered((0,0,1,1),library.boundary(block.state,'up')))
    for p,b in grid.blocks.items():
        name=b.block_id.removeprefix('minecraft:');props=dict(b.properties);direction=None;rule=None
        if name in ('sand','red_sand','gravel','suspicious_sand','suspicious_gravel') or name.endswith('_concrete_powder'):
            direction='down';rule='gravity block'
        elif name.endswith('rail') or name in ('redstone_wire','repeater','comparator') or name.endswith('_door') and props.get('half')=='lower':
            direction='down';rule='floor-supported block'
        elif name in ('torch','soul_torch','redstone_torch') or name.endswith('_pressure_plate'):
            direction='down';rule='floor attachment'
        elif name in ('lantern','soul_lantern'):
            direction='up' if props.get('hanging')=='true' else 'down';rule='lantern attachment'
        elif name in ('ladder','wall_torch','soul_wall_torch','redstone_wall_torch') or name.endswith(('_wall_sign','_wall_banner','_wall_head','_wall_skull')):
            direction=opposite(props.get('facing','north'));rule='wall attachment'
        elif name.endswith('_button') or name=='lever':
            direction={'floor':'down','ceiling':'up'}.get(props.get('face'),opposite(props.get('facing','north')));rule='switch attachment'
        if direction:
            neighbor=grid.blocks.get(add(p,DIRECTIONS[direction]))
            if direction=='down':supported=full_top(neighbor)
            else:supported=bool(neighbor and covered((.375,.375,.625,.625),library.boundary(neighbor.state,opposite(direction))))
            if not supported:issues.append({'position':p,'code':'missing_support','message':rule+' lacks a supporting face','support_position':add(p,DIRECTIONS[direction])})
    return {'revision':grid.revision,'issues':issues[:1000],'total':len(issues),'scope':'Static attachment and gravity diagnostics based on model boundary faces; no game tick simulation'}
