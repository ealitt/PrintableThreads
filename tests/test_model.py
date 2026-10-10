import unittest
import math
import json
from dataclasses import replace
from PrintableThreads.model.spec import Spec,mm_to_cm,phase_at_z,start_phases,fit_clearances
from PrintableThreads.geometry.profile import rounded_trapezoid
from PrintableThreads.geometry import preview

class RecipeTests(unittest.TestCase):
    def test_nominal(self):
        s=Spec().validate()
        self.assertEqual(s.major_diameter,14);self.assertEqual(s.lead,3);self.assertEqual(s.turns,6)
    def test_three_start(self):
        s=replace(Spec(),starts=3,pitch=2,length=12,width=1.3).validate()
        self.assertEqual(s.lead,6);self.assertEqual(s.turns,2)
        self.assertAlmostEqual(start_phases(3)[2],4*math.pi/3)
    def test_units(self):self.assertEqual(mm_to_cm(12),1.2)
    def test_fractional_turns(self):self.assertEqual(replace(Spec(),length=1.5).turns,.5)
    def test_overshoot_phase(self):
        for lead in (2,3,6,8):
            a=phase_at_z(-2*lead,lead,37)
            self.assertAlmostEqual(math.cos(a),math.cos(math.radians(37)))
    def test_handedness(self):
        self.assertAlmostEqual(phase_at_z(1,4),math.pi/2)
        self.assertAlmostEqual(phase_at_z(1,4,left=True),-math.pi/2)
    def test_cutter_clearance(self):
        s=Spec();c=s.cutter()
        self.assertEqual(c.root_diameter,12.4);self.assertEqual(c.width,1.8)
        self.assertEqual(c.crest,.8);self.assertEqual(c.lead,s.lead)
        self.assertEqual(c.length,s.engagement);self.assertEqual(c.knob,'None')
    def test_half_mm_label(self):
        self.assertEqual(replace(Spec(),radial_clearance=.5).clearance_label,'0.5 mm/side (+1 mm diameter)')
    def test_fit_clearances(self):
        self.assertEqual(fit_clearances(.2),(.1,.2,.3,.45))
        for value in (0,.05,.2,.8,1):
            samples=fit_clearances(value)
            self.assertEqual(len(set(samples)),4)
            self.assertGreaterEqual(min(samples),0);self.assertLessEqual(max(samples),1)
    def test_roundtrip(self):self.assertEqual(Spec.from_json(Spec().to_json()),Spec())
    def test_future_schema_rejected(self):
        data=json.loads(Spec().to_json());data['schema']=2
        with self.assertRaises(ValueError):Spec.from_json(json.dumps(data))
    def test_invalid_recipes(self):
        for values in ({'width':2.8},{'starts':0},{'starts':1.5},{'pitch':0},{'length':float('nan')},
                       {'female_diameter':14},{'blind':True,'floor':.2},{'radius':1},{'radial_clearance':-.1},
                       {'entry':5},{'knob_height':0},{'height':0},{'crest':0},{'length':200}):
            with self.subTest(values=values),self.assertRaises(ValueError):replace(Spec(),**values).validate()
    def test_profile_closed(self):
        segments=rounded_trapezoid(6,1,1.5,.5,.15)
        for i,segment in enumerate(segments):self.assertEqual(segment[-1],segments[(i+1)%len(segments)][1])
    def test_profile_envelope(self):
        for s in rounded_trapezoid(6,1,1.5,.5,.15):
            for r,z in s[1:]:
                self.assertGreaterEqual(r,5.92-1e-9);self.assertLessEqual(r,7+1e-9);self.assertLessEqual(abs(z),.75+1e-9)
    def test_sharp_profile(self):
        self.assertTrue(all(s[0]=='line' for s in rounded_trapezoid(6,1,1.5,.5,0)))
    def test_profile_radius_rejection(self):
        with self.assertRaises(ValueError):rounded_trapezoid(6,1,1.5,.1,.5)
    def test_independent_female_length(self):
        s=replace(Spec(),length=2,engagement=12)
        self.assertEqual(s.cutter().length,12)
    def test_balanced_thread_size(self):
        s=Spec().with_thread_size(1.2)
        for actual,expected in zip((s.height,s.width,s.crest,s.radius),(1.2,1.8,.6,.18)):
            self.assertAlmostEqual(actual,expected)
        self.assertTrue(s.balanced_profile)
        self.assertFalse(replace(s,width=1.7).balanced_profile)
    def test_circular_coil_size(self):
        s=Spec().with_circular_section(2).validate()
        self.assertEqual(s.thread_size,2)
        self.assertEqual(s.height,1)
        self.assertEqual(s.major_diameter,14)
        coords,_=preview.helix(s)
        radii=[math.hypot(coords[i],coords[i+1]) for i in range(0,len(coords),3)]
        self.assertAlmostEqual(min(radii),5)
        self.assertAlmostEqual(max(radii),7)
        self.assertEqual(Spec.from_json(s.to_json()),s)
        with self.assertRaises(ValueError):s.with_circular_section(3).validate()
    def test_legacy_recipe_keeps_profile(self):
        data=json.loads(Spec().to_json());del data['spec']['section']
        s=Spec.from_json(json.dumps(data))
        self.assertEqual(s.section,'Trapezoid');self.assertEqual(s.thread_size,1)
    def test_reversed_clearance_and_mesh(self):
        s=replace(Spec().with_circular_section(2),cut_screw=True).validate()
        self.assertEqual(s.major_diameter,12)
        rib=s.nut_rib()
        self.assertAlmostEqual(rib.root_diameter,12.4)
        self.assertAlmostEqual(rib.width,1.7)
        self.assertAlmostEqual(preview.inward_radius(s,0,3),5)
        self.assertGreater(preview.inward_radius(rib,0,3),preview.inward_radius(s,0,3))
        for mesh in (preview.screw(s),preview.radial_surface(rib,outer=11)):
            coords,indices=mesh
            self.assertTrue(all(0<=i<len(coords)//3 for i in indices))
            self.assertTrue(all(math.isfinite(v) for v in coords))
        with self.assertRaises(ValueError):replace(s.with_circular_section(.5),axial_clearance=.3).validate()
    def test_preview_mesh_bounds(self):
        s=Spec();coords,triangles=preview.helix(s)
        self.assertGreater(len(triangles),100)
        radii=[math.hypot(coords[i],coords[i+1]) for i in range(0,len(coords),3)]
        heights=coords[2::3]
        self.assertAlmostEqual(min(radii),s.root_diameter/2)
        self.assertAlmostEqual(max(radii),s.major_diameter/2)
        self.assertGreaterEqual(min(heights),0);self.assertLessEqual(max(heights),s.length)

if __name__=='__main__':unittest.main()
