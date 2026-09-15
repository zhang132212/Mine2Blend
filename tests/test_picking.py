import unittest
from editor.grid import BlockGrid
from editor.registry import Registry
from editor.render import ModelLibrary
from editor.picking import raycast

class PickingTests(unittest.TestCase):
    def test_partial_block_and_negative_coordinates(self):
        g=BlockGrid();r=Registry();lib=ModelLibrary()
        g._set((-2,0,0),r.resolve('minecraft:stone_slab[type=bottom]'))
        result=raycast(g,lib,(-1.5,4,.5),(0,-1,0))
        self.assertEqual(result['position'],(-2,0,0));self.assertAlmostEqual(result['location'][1],.5)
        self.assertIsNone(raycast(g,lib,(-4,.75,.5),(1,0,0)))
        g.view['hidden_layers']=[0];self.assertIsNone(raycast(g,lib,(-1.5,4,.5),(0,-1,0)))
