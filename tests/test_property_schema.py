import unittest
from editor.registry import Registry,matches

class PropertySchemaTests(unittest.TestCase):
    def test_typed_properties(self):
        r=Registry()
        stairs=next(v for v in r.search('oak_stairs')['items'] if v['id']=='minecraft:oak_stairs')
        self.assertEqual(stairs['property_schema']['waterlogged']['type'],'boolean')
        self.assertEqual(stairs['property_schema']['facing']['enum'],stairs['properties']['facing'])
        wire=r.search('redstone_wire')['items'][0]
        self.assertEqual(wire['property_schema']['power']['enum'],list(range(16)))
        self.assertTrue(matches({'AND':[{'lit':True},{'OR':[{'facing':'east'},{'facing':'north'}]}]},{'lit':'true','facing':'north'}))
