import unittest
from editor.grid import BlockGrid,BlockRecord

class ChunkArrayTests(unittest.TestCase):
    def test_negative_coordinates_edit_and_undo(self):
        g=BlockGrid();stone=BlockRecord.parse('minecraft:stone')
        g.apply([((-1,-16,-17),stone)],0)
        palette,values=g.chunk_array((-1,-1,-2))
        self.assertEqual(palette[int(values[0,15,15])],stone)
        self.assertFalse(values.flags.writeable)
        self.assertIs(g.chunk_array((-1,-1,-2))[1],values)
        g.apply([((-1,-16,-17),None)],1)
        self.assertEqual(int(g.chunk_array((-1,-1,-2))[1].sum()),0)
        g.undo();self.assertEqual(int(g.chunk_array((-1,-1,-2))[1][0,15,15]),1)
