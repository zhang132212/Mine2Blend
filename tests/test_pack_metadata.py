import unittest
from editor.pack_metadata import resolve,bounds

class PackMetadataTests(unittest.TestCase):
    def test_minor_ranges_and_overlay_precedence(self):
        meta={'pack':{'min_format':[88,0],'max_format':88},'overlays':{'entries':[
            {'directory':'old','min_format':84,'max_format':84},
            {'directory':'current','min_format':88,'max_format':[88,1]},
            {'directory':'last','min_format':88,'max_format':88}]}}
        names=['assets/minecraft/models/block/stone.json','old/assets/minecraft/models/block/stone.json','current/assets/minecraft/models/block/stone.json','last/assets/minecraft/models/block/stone.json']
        selected,layers,warnings=resolve(names,meta)
        self.assertEqual(selected[names[0]],names[-1]);self.assertEqual(layers,['current','last']);self.assertFalse(warnings)
        self.assertEqual(bounds(meta['pack'])[1],(88,2**31-1))
    def test_invalid_and_legacy(self):
        self.assertEqual(bounds({'supported_formats':[16,88]}),((16,0),(88,2**31-1)))
        with self.assertRaises(ValueError):bounds({'min_format':88})
        with self.assertRaises(ValueError):resolve([],{'pack':{'pack_format':88},'overlays':{'entries':[{'directory':'../outside','formats':88}]}})
