import unittest
from editor.fluids import quads
from editor.registry import Registry
from editor.render import ModelLibrary

class FluidTests(unittest.TestCase):
    def test_contiguous_water_and_above(self):
        r=Registry();water=r.resolve('minecraft:water');lib=ModelLibrary()
        blocks={(0,0,0):water,(1,0,0):water}
        faces=quads(water,(0,0,0),blocks.get,lib.opaque_cube)
        self.assertEqual(len(faces),5)
        self.assertTrue(all(0<=v[1]<1 for q in faces for v in q[0]))
        blocks[(0,1,0)]=water
        faces=quads(water,(0,0,0),blocks.get,lib.opaque_cube)
        self.assertEqual(len(faces),4)
        self.assertEqual(max(v[1] for q in faces for v in q[0]),1)
