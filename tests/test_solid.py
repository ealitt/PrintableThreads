import unittest
from types import SimpleNamespace
from PrintableThreads.model.solid import validate_applied

def solid(regions=1,volume=1):
    return SimpleNamespace(isSolid=True,volume=volume,lumps=SimpleNamespace(count=regions))

class AppliedSolidTests(unittest.TestCase):
    def test_interrupted_cut_can_split_into_solids(self):
        result=solid(3)
        self.assertIs(validate_applied(result,1,False),result)
    def test_existing_multiple_regions_are_preserved(self):
        self.assertIsNotNone(validate_applied(solid(2),2,True))
    def test_join_rejects_detached_rib(self):
        with self.assertRaisesRegex(ValueError,'fragments'):
            validate_applied(solid(2),1,True)
    def test_empty_and_surface_results_are_rejected(self):
        surface=solid();surface.isSolid=False
        for result in (None,solid(0),solid(volume=0),surface):
            with self.subTest(result=result),self.assertRaisesRegex(ValueError,'closed solid'):
                validate_applied(result,1,False)
