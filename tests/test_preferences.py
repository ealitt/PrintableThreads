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
            restored=preferences.load('create',path)
            self.assertEqual(Spec.from_json(restored['recipe']).pitch,4)
            self.assertEqual(restored['live_preview'],False)
            self.assertEqual(Spec.from_json(restored['recipe']).knob_diameter,26)
            self.assertEqual(Spec.from_json(preferences.load('apply',path)['recipe']).pitch,4)
    def test_missing_or_damaged_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'settings.json'
            self.assertEqual(preferences.load('create',path),{})
            path.write_text('invalid json')
            self.assertEqual(preferences.load('create',path),{})
            preferences.save('create',{'recipe':Spec().to_json()},path)
            self.assertEqual(Spec.from_json(preferences.load('create',path)['recipe']).radial_clearance,.2)

class SharedThreadMemoryTests(unittest.TestCase):
    def test_apply_memory_keeps_custom_head(self):
        from dataclasses import replace
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'settings.json'
            head=replace(Spec(),knob_diameter=31,knob_height=7,knob='Cylinder')
            preferences.save('create',{'recipe':head.to_json(),'auto_knob':False,'auto_knob_height':False},path)
            applied=replace(Spec().with_circular_section(2),root_diameter=4,pitch=4,length=3.65,output='Screw',knob='None',entry=0)
            preferences.save('apply',{'recipe':applied.to_json()},path)
            saved=preferences.load('create',path);result=Spec.from_json(saved['recipe'])
            self.assertEqual((result.root_diameter,result.pitch,result.length,result.section),(4,4,3.65,'Circular'))
            self.assertEqual((result.knob,result.knob_diameter,result.knob_height),('Cylinder',31,7))
            self.assertFalse(saved['auto_knob'])
            preferences.save('create',{'recipe':replace(result,pitch=5).to_json()},path)
            self.assertEqual(Spec.from_json(preferences.load('apply',path)['recipe']).pitch,5)

    def test_proportional_knob(self):
        from PrintableThreads.model.spec import default_knob_dimensions
        self.assertEqual(default_knob_dimensions(4),(6.4,2))
        for diameter in (4,12,30,100):
            width,height=default_knob_dimensions(diameter)
            self.assertGreaterEqual(width,diameter+2)
            self.assertTrue(2<=height<=12)
