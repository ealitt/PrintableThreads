import tempfile
import unittest
from pathlib import Path
from PrintableThreads.model import preferences
from PrintableThreads.model.spec import Spec

class PreferencesTests(unittest.TestCase):
    def test_modes_survive_multiple_saves(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'settings.json'
            create={'recipe':Spec(root_diameter=16).to_json(),'live_preview':False}
            preferences.save('create',create,path)
            preferences.save('apply',{'recipe':Spec(pitch=4).to_json()},path)
            self.assertEqual(preferences.load('create',path),create)
            self.assertEqual(Spec.from_json(preferences.load('apply',path)['recipe']).pitch,4)
    def test_missing_or_damaged_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'settings.json'
            self.assertEqual(preferences.load('create',path),{})
            path.write_text('invalid json')
            self.assertEqual(preferences.load('create',path),{})
            preferences.save('create',{'recipe':Spec().to_json()},path)
            self.assertEqual(Spec.from_json(preferences.load('create',path)['recipe']).radial_clearance,.2)
