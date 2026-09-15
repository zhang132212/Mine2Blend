import unittest
from editor.grid import BlockGrid
from editor.registry import Registry
from editor.service import EditorService
from editor.connections import reconcile
from editor.transforms import state, coordinate

class ConnectivityTests(unittest.TestCase):
    def setUp(self): self.r=Registry();self.g=BlockGrid()
    def put(self,rows): self.g.apply(reconcile(self.g,[(p,self.r.resolve(s) if s else None) for p,s in rows]))
    def props(self,p): return dict(self.g.blocks[p].properties)
    def test_fence_and_undo(self):
        self.put([((0,0,0),'minecraft:oak_fence'),((1,0,0),'minecraft:oak_fence')])
        self.assertEqual(self.props((0,0,0))['east'],'true')
        self.put([((1,0,0),None)])
        self.assertEqual(self.props((0,0,0))['east'],'false')
        self.g.undo();self.assertEqual(self.props((0,0,0))['east'],'true')
    def test_stairs(self):
        self.put([((0,0,0),'minecraft:oak_stairs[facing=north]'),((0,0,-1),'minecraft:oak_stairs[facing=west]')])
        self.assertEqual(self.props((0,0,0))['shape'],'outer_left')
        self.put([((0,0,-1),None),((0,0,1),'minecraft:oak_stairs[facing=east]')])
        self.assertEqual(self.props((0,0,0))['shape'],'inner_right')
    def test_registry_models_drive_connections(self):
        self.put([((0,0,0),'minecraft:oak_fence'),((1,0,0),'minecraft:iron_block')])
        self.assertEqual(self.props((0,0,0))['east'],'true')
        self.put([((1,0,0),'minecraft:glass')]);self.assertEqual(self.props((0,0,0))['east'],'true')
        self.put([((0,0,0),'minecraft:glass_pane')]);self.assertEqual(self.props((0,0,0))['east'],'true')
    def test_bed_pair(self):
        s=EditorService();gid=s.execute('create_grid',{})['grid_id']
        args={'grid_id':gid,'expected_revision':0,'position':[0,0,0],'state':'minecraft:red_bed','placement':{'look':'east'}}
        self.assertEqual(s.execute('place_block',args)['changed'],2)
        self.assertEqual(dict(s.grids[gid].blocks[(1,0,0)].properties)['part'],'head')
        self.assertEqual(s.execute('place_block',{'grid_id':gid,'expected_revision':1,'position':[1,0,0],'state':'minecraft:air'})['changed'],2)
    def test_wall_collision_above_and_post(self):
        self.put([((0,0,0),'minecraft:cobblestone_wall'),((0,0,-1),'minecraft:stone'),((0,0,1),'minecraft:stone')])
        self.assertEqual((self.props((0,0,0))['north'],self.props((0,0,0))['up']),('low','false'))
        self.put([((0,1,0),'minecraft:stone_slab[type=bottom]')])
        self.assertEqual((self.props((0,0,0))['north'],self.props((0,0,0))['south'],self.props((0,0,0))['up']),('tall','tall','false'))
        self.put([((0,1,0),'minecraft:stone_slab[type=top]')])
        self.assertEqual(self.props((0,0,0))['north'],'low')
        self.put([((1,0,0),'minecraft:stone')])
        self.assertEqual(self.props((0,0,0))['up'],'true')
    def test_rails(self):
        self.put([((0,0,0),'minecraft:rail'),((0,0,-1),'minecraft:rail'),((1,0,0),'minecraft:rail')])
        self.assertEqual(self.props((0,0,0))['shape'],'north_east')
    def test_wire_glass_climb_and_conductor(self):
        self.put([((0,0,0),'minecraft:redstone_wire'),((1,0,0),'minecraft:glass'),((1,1,0),'minecraft:redstone_wire')])
        self.assertEqual(self.props((0,0,0))['east'],'up')
        self.put([((0,1,0),'minecraft:stone'),((0,0,-1),'minecraft:redstone_wire')])
        self.assertEqual(self.props((0,0,0))['east'],'none')
        self.put([((0,1,0),'minecraft:glass')])
        self.assertEqual(self.props((0,0,0))['east'],'up')
    def test_door_pair(self):
        s=EditorService();g=s.execute('create_grid',{})
        out=s.execute('place_block',{'grid_id':g['grid_id'],'expected_revision':0,'position':[0,0,0],'state':'minecraft:oak_door','placement':{'look':'east'}})
        self.assertEqual(out['changed'],2)
        out=s.execute('place_block',{'grid_id':g['grid_id'],'expected_revision':1,'position':[0,1,0],'state':'minecraft:air'})
        self.assertEqual(out['changed'],2)
    def test_transform_inverse(self):
        for name in self.r.blocks:
            b=self.r.resolve('minecraft:'+name)
            self.assertEqual(state(state(b,turns=1),turns=3),b,name)
            self.assertEqual(state(state(b,mirror='x'),mirror='x'),b,name)
            self.r.resolve(state(b,turns=1,mirror='z').state)
        self.assertEqual(coordinate((2,3,4),turns=1),(-4,3,2))
    def test_slab_merge_and_double_door(self):
        s=EditorService();g=s.execute('create_grid',{});gid=g['grid_id']
        def put(p,state,context={}):
            return s.execute('place_block',{'grid_id':gid,'expected_revision':s.grids[gid].revision,'position':p,'state':state,'placement':context})
        put([0,0,0],'minecraft:stone_slab');put([0,0,0],'minecraft:stone_slab')
        self.assertEqual(dict(s.grids[gid].blocks[(0,0,0)].properties)['type'],'double')
        put([3,0,0],'minecraft:oak_door');put([4,0,0],'minecraft:oak_door')
        self.assertNotEqual(dict(s.grids[gid].blocks[(3,0,0)].properties)['hinge'],dict(s.grids[gid].blocks[(4,0,0)].properties)['hinge'])
    def test_connection_keys_and_hinge(self):
        b=self.r.resolve('minecraft:oak_fence[north=true]')
        self.assertEqual(dict(state(b,1).properties)['east'],'true')
        b=self.r.resolve('minecraft:oak_door[hinge=left]')
        self.assertEqual(dict(state(b,mirror='x').properties)['hinge'],'right')
