import unittest
from editor.grid import BlockGrid
from editor.registry import Registry
from editor.render import ModelLibrary
from editor.validation import orientations,support

class ValidationTests(unittest.TestCase):
    def test_pairs_and_support(self):
        r=Registry();g=BlockGrid()
        g._set((0,1,0),r.resolve('minecraft:oak_door[half=lower]'))
        self.assertTrue(any(i['code']=='door_pair' for i in orientations(g,r)['issues']))
        self.assertEqual(support(g,ModelLibrary())['total'],1)
        g._set((0,0,0),r.resolve('minecraft:stone_bricks'))
        g._set((0,2,0),r.resolve('minecraft:oak_door[half=upper]'))
        self.assertEqual(orientations(g,r)['total'],0);self.assertEqual(support(g,ModelLibrary())['total'],0)
