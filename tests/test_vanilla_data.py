import json,unittest
from pathlib import Path
from editor.render import ModelLibrary
from editor.registry import Registry

class VanillaDataTests(unittest.TestCase):
    def test_all_26_2_states_have_physics(self):
        lib=ModelLibrary();r=Registry()
        self.assertIsNotNone(lib.physics)
        self.assertEqual(len(lib.physics['states']),32366)
        for name in r.blocks:self.assertIsNotNone(lib.physical(r.resolve('minecraft:'+name).state),name)
        glass=lib.physical('minecraft:glass')
        self.assertFalse(glass['can_occlude']);self.assertTrue(glass['sturdy']['up'][0])
        self.assertTrue(glass['connections']['east'][0])
    def test_current_entity_geometry_and_variants(self):
        data=json.loads((Path(__file__).resolve().parents[1]/'editor/data/resources/entity-models.json').read_text())
        self.assertFalse(data['legacy_geometry'])
        for name in ('copper_golem','armadillo','breeze','creaking','happy_ghast','nautilus'):
            self.assertIn('minecraft:'+name,data['vanilla_layers'])
        self.assertIn('baby',data['variants']['minecraft:armadillo'])
