"""Versioned recipes. All stored lengths are millimeters, angles degrees."""
from dataclasses import dataclass, asdict, replace
import json
import math

SCHEMA = 1
BACKEND = 'guided-helix-1'

@dataclass(frozen=True)
class Spec:
    cut_screw: bool = False  # Legacy recipes retain joined screws.
    print_on_plate: bool = False
    section: str = 'Trapezoid'  # Missing in legacy recipes: preserve their geometry.
    root_diameter: float = 12.0
    height: float = 1.0
    pitch: float = 3.0
    starts: int = 1
    length: float = 18.0
    width: float = 1.5
    crest: float = 0.5
    radius: float = 0.15
    radial_clearance: float = 0.2
    axial_clearance: float = 0.15
    female_diameter: float = 22.0
    engagement: float = 9.0
    floor: float = 2.0
    blind: bool = False
    knob: str = 'Lobed'
    knob_diameter: float = 26.0
    knob_height: float = 6.0
    lobes: int = 6
    entry: float = 0.6
    left_hand: bool = False
    phase: float = 0.0
    output: str = 'Matched pair'

    @property
    def lead(self): return self.pitch * self.starts
    @property
    def major_diameter(self): return self.root_diameter if self.cut_screw else self.root_diameter + 2 * self.height
    @property
    def turns(self): return self.length / self.lead
    @property
    def thread_size(self): return 2*self.height if self.section=='Circular' else self.height
    @property
    def balanced_profile(self):
        """True when one thread-size value describes the rounded section."""
        return (math.isclose(self.width,1.5*self.height,abs_tol=1e-9) and
                math.isclose(self.crest,.5*self.height,abs_tol=1e-9) and
                math.isclose(self.radius,.15*self.height,abs_tol=1e-9))
    @property
    def clearance_label(self):
        return f'{self.radial_clearance:g} mm/side (+{2*self.radial_clearance:g} mm diameter)'

    def validate(self):
        for key, value in asdict(self).items():
            if isinstance(value, (int, float)) and not isinstance(value, bool) and not math.isfinite(value):
                raise ValueError(f'{key} must be finite.')
        if type(self.starts) is not int or not 1 <= self.starts <= 4:
            raise ValueError('Starts must be an integer from 1 to 4.')
        if not 4 <= self.root_diameter <= 100: raise ValueError('Root diameter must be 4–100 mm.')
        if not 0.8 <= self.pitch <= 12: raise ValueError('Pitch must be 0.8–12 mm.')
        if not 0.25 <= self.height <= min(4, self.root_diameter / 4): raise ValueError('Thread height is outside the supported range.')
        if type(self.cut_screw) is not bool or type(self.print_on_plate) is not bool: raise ValueError('Thread direction and print placement must be boolean.')
        if self.cut_screw and min(self.width,self.crest if self.section!='Circular' else self.width)<=2*self.axial_clearance:
            raise ValueError('Flank clearance is too large for the joined nut section.')
        if self.section not in ('Circular','Trapezoid'): raise ValueError('Unknown section shape.')
        if self.section=='Circular':
            if 2*self.height+2*self.axial_clearance >= self.pitch-.1:
                raise ValueError('Section diameter plus flank clearances must leave at least 0.1 mm between turns.')
        if self.section!='Circular' and not 0 < self.crest < self.width: raise ValueError('Crest width must be positive and smaller than base width.')
        if self.section!='Circular' and self.width + 2*self.axial_clearance >= self.pitch - 0.1:
            if self.balanced_profile:
                raise ValueError('Thread size is too large for this pitch. Reduce Thread size or increase Pitch.')
            raise ValueError('Base width plus both flank clearances must leave at least 0.1 mm of valley.')
        if self.section!='Circular' and not 0 <= self.radius <= min(self.crest*.45, self.height*.4):
            raise ValueError('Corner radius must be at most 45% of crest width and 40% of height.')
        if not 0 <= self.radial_clearance <= 1 or not 0 <= self.axial_clearance <= 0.5:
            raise ValueError('Clearance must be 0–1 mm radial and 0–0.5 mm axial.')
        if not .5 <= self.length <= 100 or not .5 <= self.engagement <= 100:
            raise ValueError('Length and engagement must be 0.5–100 mm.')
        if max(self.length, self.engagement) / self.lead > 40:
            raise ValueError('Limit each start to 40 revolutions; increase pitch or reduce length.')
        if self.output != 'Screw' and (self.female_diameter-self.major_diameter)/2-self.radial_clearance < 1:
            raise ValueError('Female wall must remain at least 1 mm thick.')
        if self.blind and self.floor < 1: raise ValueError('Blind cap floor must be at least 1 mm.')
        if self.knob not in ('None','Cylinder','Lobed'): raise ValueError('Unknown knob type.')
        if self.knob != 'None' and (self.knob_diameter < self.major_diameter + 2 or not .8 <= self.knob_height <= 30):
            raise ValueError('Knob must exceed major diameter by 2 mm; height must be 0.8–30 mm.')
        if type(self.lobes) is not int or not 3 <= self.lobes <= 12: raise ValueError('Lobes must be an integer from 3 to 12.')
        if not 0 <= self.entry < min(self.length, self.engagement)/2:
            raise ValueError('Entry chamfer must be less than half the shorter threaded interval.')
        if self.output not in ('Matched pair','Screw','Female'): raise ValueError('Unknown output type.')
        return self

    def nut_rib(self):
        """Move inward ribs outward and narrow their flanks for mating clearance."""
        return replace(self,root_diameter=self.root_diameter+2*self.radial_clearance,
                       width=self.width-2*self.axial_clearance,crest=self.crest-2*self.axial_clearance,
                       radius=min(self.radius,max(0,(self.crest-2*self.axial_clearance)*.4)),
                       length=self.engagement,knob='None',entry=0)

    def cutter(self, length=None):
        return replace(self, root_diameter=self.root_diameter+2*self.radial_clearance,
                       width=self.width+2*self.axial_clearance, crest=self.crest+2*self.axial_clearance,
                       length=self.engagement if length is None else length, knob='None',entry=0)

    def with_circular_section(self, diameter):
        """Coil Circular / On Center: diameter is the full circle size."""
        return replace(self,section='Circular',height=diameter/2,width=diameter,crest=diameter/2,radius=0)

    def with_thread_size(self, size):
        """Apply the balanced printable profile used by the simple UI."""
        return replace(self,height=size,width=1.5*size,crest=.5*size,radius=.15*size)

    def to_json(self):
        return json.dumps({'schema': SCHEMA,'backend': BACKEND,'units':'mm','spec':asdict(self)},sort_keys=True)

    @classmethod
    def from_json(cls, value):
        data=json.loads(value)
        if data.get('schema') != SCHEMA or data.get('units') != 'mm':
            raise ValueError('Unsupported recipe schema or units.')
        return cls(**data['spec']).validate()

def mm_to_cm(value): return value / 10.0

def fit_clearances(tolerance):
    """Four distinct samples near the requested per-side tolerance, within 0–1 mm."""
    start=max(0,min(.65,tolerance-.1))
    return tuple(round(start+offset,6) for offset in (0,.1,.2,.35))

def phase_at_z(z, lead, phase=0, left=False):
    return math.radians(phase) + (-1 if left else 1)*2*math.pi*z/lead

def start_phases(starts, phase=0):
    return [math.radians(phase)+2*math.pi*i/starts for i in range(starts)]
