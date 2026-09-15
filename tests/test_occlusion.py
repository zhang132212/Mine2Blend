import unittest
from editor.render import ModelLibrary,face_vertices
from editor.registry import Registry
from editor.occlusion import covered

class OcclusionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.lib=ModelLibrary();cls.registry=Registry()
    def test_union_and_hole(self):
        self.assertTrue(covered((0,0,1,1),((0,0,.5,1),(.5,0,1,1))))
        self.assertFalse(covered((0,0,1,1),((0,0,.4,1),(.5,0,1,1))))
    def test_real_shapes_and_alpha(self):
        stone=self.registry.resolve('minecraft:stone_bricks')
        glass=self.registry.resolve('minecraft:glass')
        slab=self.registry.resolve('minecraft:stone_slab[type=bottom]')
        self.assertTrue(self.lib.opaque_cube(stone))
        self.assertFalse(self.lib.opaque_cube(glass))
        self.assertFalse(self.lib.opaque_cube(slab))
        full=face_vertices((0,0,0),(1,1,1))['east']
        half=face_vertices((0,0,0),(1,.5,1))['east']
        self.assertTrue(self.lib.occluded(stone,stone,full,(1,0,0)))
        self.assertFalse(self.lib.occluded(stone,slab,full,(1,0,0)))
        self.assertTrue(self.lib.occluded(slab,slab,half,(1,0,0)))
        self.assertTrue(self.lib.occluded(glass,glass,full,(1,0,0)))
        self.assertFalse(self.lib.occluded(stone,glass,full,(1,0,0)))
