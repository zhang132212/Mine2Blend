import unittest
from editor.render import ModelLibrary

class WeightedTests(unittest.TestCase):
    def test_stable_weighted_selection(self):
        lib=ModelLibrary();lib.definitions['test_weighted']={'variants':{'':[{'model':'block/stone','weight':1},{'model':'block/glass','weight':3}]}}
        state='minecraft:test_weighted'
        choices=[lib.choice_key(state,(x,0,0))[0] for x in range(1000)]
        self.assertGreater(sum(choices),680);self.assertLess(sum(choices),820)
        self.assertEqual(lib.choice_key(state,(-8,12,4)),lib.choice_key(state,(-8,12,4)))
        self.assertNotEqual(lib.quads(state,(0,))[0][2],lib.quads(state,(1,))[0][2])
        self.assertFalse(lib.full_opaque(state))
