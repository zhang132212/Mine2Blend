import unittest
from editor.ctm import Rule,CTM,INDEX,BASES,texture_id,properties
from editor.grid import BlockRecord,DIRECTIONS

class CTMTests(unittest.TestCase):
    def setUp(self):self.stone=BlockRecord.parse('minecraft:stone')
    def rule(self,method,extra=''):
        return Rule.parse('minecraft:optifine/ctm/test/rule.properties',f'matchBlocks=stone\nmethod={method}\ntiles=0-46\n'+extra)
    def test_47_topologies(self):self.assertEqual(set(INDEX),set(range(47)))
    def test_java_properties_and_limits(self):
        data=properties('matchBlocks stone\nfaces = top \\\n sides\nlabel\\ key:hello\\u0020world')
        self.assertEqual(data['matchBlocks'],'stone');self.assertEqual(data['faces'],'top sides')
        self.assertEqual(data['label key'],'hello world')
        with self.assertRaises(ValueError):Rule.parse('test.properties','method=ctm\ntiles=0-999999999')
    def test_ctm_isolated_and_surrounded(self):
        rule=self.rule('ctm')
        get=lambda p:self.stone
        self.assertTrue(rule.select((0,0,0),self.stone,'block/stone','north',get,lambda b,f,p=None:'block/stone')[0].endswith('/26'))
        self.assertTrue(rule.select((0,0,0),self.stone,'block/stone','north',lambda p:None,lambda b,f,p=None:'block/stone')[0].endswith('/0'))
    def test_horizontal_faces(self):
        rule=self.rule('horizontal')
        for face,basis in BASES.items():
            left=DIRECTIONS[basis[0]]
            tile=rule.select((0,0,0),self.stone,'block/stone',face,lambda p:self.stone if p==left else None,lambda b,f,p=None:'block/stone')
            self.assertTrue(tile[0].endswith('/2'),(face,tile))
    def test_biome_faces_and_states(self):
        r=self.rule('fixed','faces=top\nbiomes=!minecraft:desert')
        self.assertFalse(r.matches(self.stone,'block/stone','north'))
        self.assertFalse(r.matches(self.stone,'block/stone','up','minecraft:desert'))
        self.assertTrue(r.matches(self.stone,'block/stone','up'))
    def test_repeat_negative_coordinates(self):
        r=self.rule('repeat','width=3\nheight=2')
        tile=r.select((-1,0,-1),self.stone,'block/stone','up',lambda p:None,lambda b,f,p=None:'')
        self.assertTrue(tile[0].endswith('/5'))
    def test_overlay(self):
        r=self.rule('overlay','connectBlocks=dirt')
        dirt=BlockRecord.parse('minecraft:dirt')
        tile=r.select((0,0,0),self.stone,'block/stone','north',lambda p:dirt if p==(1,0,0) else None,lambda b,f,p=None:'block/'+b.block_id.split(':')[1])
        self.assertTrue(tile[0].endswith('/9'))
    def test_priority(self):
        a=self.rule('fixed','weight=1');b=self.rule('fixed','weight=10')
        self.assertIs(CTM([a,b]).rules[0],b)
    def test_rotated_uv_changes_local_left(self):
        from editor.ctm import uv_basis
        from editor.render import face_vertices
        quad=face_vertices((0,0,0),(1,1,1))['north']
        uv=[(0,16),(16,16),(16,0),(0,0)]
        self.assertEqual(uv_basis(quad,uv),[DIRECTIONS[n] for n in BASES['north']])
        rotated=uv[1:]+uv[:1]
        self.assertEqual(uv_basis(quad,rotated)[0],DIRECTIONS['up'])
    def test_overlay_after_base_rule(self):
        base=self.rule('fixed','weight=10')
        overlay=self.rule('overlay_fixed')
        texture,layers=CTM([base,overlay]).select((0,0,0),self.stone,'block/stone','north',lambda p:None,lambda b,f,p=None:'')
        self.assertEqual(len(layers),1)
    def test_metadata_undo(self):
        from editor.grid import BlockGrid
        g=BlockGrid();m=g.metadata();m['view']['slice_min']=3
        g.apply([],0,m);self.assertEqual(g.view['slice_min'],3)
        g.undo();self.assertIsNone(g.view['slice_min'])

