import unittest
from editor.ctm import Rule,CTM,INDEX,BASES,texture_id,properties
from editor.grid import BlockRecord,DIRECTIONS

class CTMTests(unittest.TestCase):
    def setUp(self):self.stone=BlockRecord.parse('minecraft:stone')
    def rule(self,method,extra=''):
        return Rule.parse('minecraft:optifine/ctm/test/rule.properties',f'matchBlocks=stone\nmethod={method}\ntiles=0-46\n'+extra)
    def test_47_topologies(self):self.assertEqual(set(INDEX),set(range(47)))
    def test_ctm_isolated_and_surrounded(self):
        rule=self.rule('ctm')
        get=lambda p:self.stone
        self.assertTrue(rule.select((0,0,0),self.stone,'block/stone','north',get,lambda b,f:'block/stone')[0].endswith('/26'))
        self.assertTrue(rule.select((0,0,0),self.stone,'block/stone','north',lambda p:None,lambda b,f:'block/stone')[0].endswith('/0'))
    def test_horizontal_faces(self):
        rule=self.rule('horizontal')
        for face,basis in BASES.items():
            left=DIRECTIONS[basis[0]]
            tile=rule.select((0,0,0),self.stone,'block/stone',face,lambda p:self.stone if p==left else None,lambda b,f:'block/stone')
            self.assertTrue(tile[0].endswith('/2'),(face,tile))
    def test_biome_faces_and_states(self):
        r=self.rule('fixed','faces=top\nbiomes=!minecraft:desert')
        self.assertFalse(r.matches(self.stone,'block/stone','north'))
        self.assertFalse(r.matches(self.stone,'block/stone','up','minecraft:desert'))
        self.assertTrue(r.matches(self.stone,'block/stone','up'))
    def test_repeat_negative_coordinates(self):
        r=self.rule('repeat','width=3\nheight=2')
        tile=r.select((-1,0,-1),self.stone,'block/stone','up',lambda p:None,lambda b,f:'')
        self.assertTrue(tile[0].endswith('/5'))
    def test_overlay(self):
        r=self.rule('overlay','connectBlocks=dirt')
        dirt=BlockRecord.parse('minecraft:dirt')
        tile=r.select((0,0,0),self.stone,'block/stone','north',lambda p:dirt if p==(1,0,0) else None,lambda b,f:'block/'+b.block_id.split(':')[1])
        self.assertTrue(tile[0].endswith('/9'))
    def test_priority(self):
        a=self.rule('fixed','weight=1');b=self.rule('fixed','weight=10')
        self.assertIs(CTM([a,b]).rules[0],b)
    def test_metadata_undo(self):
        from editor.grid import BlockGrid
        g=BlockGrid();m=g.metadata();m['view']['slice_min']=3
        g.apply([],0,m);self.assertEqual(g.view['slice_min'],3)
        g.undo();self.assertIsNone(g.view['slice_min'])
