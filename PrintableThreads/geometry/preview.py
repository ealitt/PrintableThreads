"""Fast analytical preview meshes. Coordinates are millimeters.

These meshes are display-only. Exact output continues to use the Fusion kernel.
"""
import math

def merge(*meshes):
    coordinates=[];triangles=[]
    for coords,indices in meshes:
        offset=len(coordinates)//3
        coordinates.extend(coords);triangles.extend(i+offset for i in indices)
    return coordinates,triangles

def moved(mesh,x=0,y=0,z=0):
    coords,indices=mesh;result=[]
    for i in range(0,len(coords),3):result.extend((coords[i]+x,coords[i+1]+y,coords[i+2]+z))
    return result,list(indices)

def cylinder(radius,z0,z1,sides=32,x=0,y=0):
    coords=[];indices=[]
    for z in (z0,z1):
        for i in range(sides):
            a=2*math.pi*i/sides;coords.extend((x+radius*math.cos(a),y+radius*math.sin(a),z))
    bottom=len(coords)//3;coords.extend((x,y,z0));top=len(coords)//3;coords.extend((x,y,z1))
    for i in range(sides):
        j=(i+1)%sides;a=i;b=j;c=sides+i;d=sides+j
        indices.extend((a,b,d,a,d,c,bottom,b,a,top,c,d))
    return coords,indices

def helix(spec,steps_per_turn=20,normal_clearance=0):
    """Closed trapezoidal helical tube for responsive visual feedback."""
    steps=max(12,min(900,int(math.ceil(spec.turns*steps_per_turn))))
    hand=-1 if spec.left_hand else 1
    phase=math.radians(spec.phase)
    profile=((spec.root_diameter/2,-spec.width/2),(spec.major_diameter/2,-spec.crest/2),
             (spec.major_diameter/2,spec.crest/2),(spec.root_diameter/2,spec.width/2))
    if spec.section=='Circular':
        profile=tuple((spec.root_diameter/2+spec.height*math.cos(i*math.pi/8),spec.width/2*math.sin(i*math.pi/8)) for i in range(16))
    coords=[];indices=[];ring=len(profile)
    for start in range(spec.starts):
        first=len(coords)//3;offset=2*math.pi*start/spec.starts
        for k in range(steps+1):
            center=spec.length*k/steps
            angle=phase+offset+hand*2*math.pi*center/spec.lead
            ca,sa=math.cos(angle),math.sin(angle)
            for radius,dz in profile:
                if normal_clearance and spec.section=='Circular':
                    nr=(radius-spec.root_diameter/2)/spec.height;nz=dz/spec.height
                    nt=-hand*spec.lead*nz/(2*math.pi*radius)
                    norm=math.sqrt(nr*nr+nt*nt+nz*nz)
                    rr=radius+normal_clearance*nr/norm;tt=normal_clearance*nt/norm
                    coords.extend((rr*ca-tt*sa,rr*sa+tt*ca,max(0,min(spec.length,center+dz+normal_clearance*nz/norm))))
                else:coords.extend((radius*ca,radius*sa,max(0,min(spec.length,center+dz))))
        for k in range(steps):
            a=first+k*ring;b=a+ring
            for side in range(ring):
                nxt=(side+1)%ring
                indices.extend((a+side,a+nxt,b+nxt,a+side,b+nxt,b+side))
        last=first+steps*ring
        for i in range(1,ring-1):
            indices.extend((first,first+i+1,first+i,last,last+i,last+i+1))
    return coords,indices

def knob(spec):
    if spec.knob=='None':return ([],[])
    if spec.knob=='Cylinder':return cylinder(spec.knob_diameter/2,-spec.knob_height,0)
    radius=spec.knob_diameter/2;lobe=radius*.25;centers=radius-lobe
    meshes=[cylinder(radius*.76,-spec.knob_height,0)]
    for i in range(spec.lobes):
        a=2*math.pi*i/spec.lobes
        meshes.append(cylinder(lobe,-spec.knob_height,0,20,centers*math.cos(a),centers*math.sin(a)))
    return merge(*meshes)

def screw(spec):
    return merge(radial_surface(spec),knob(spec)) if spec.cut_screw else merge(cylinder(spec.root_diameter/2,0,spec.length),helix(spec),knob(spec))


def inward_radius(spec,angle,z):
    """Approximate radial boundary of a cut groove / inward nut rib."""
    hand=-1 if spec.left_hand else 1
    center=hand*(angle-math.radians(spec.phase))*spec.lead/(2*math.pi)
    dz=abs((z-center+spec.pitch/2)%spec.pitch-spec.pitch/2)
    half=spec.width/2
    if dz>=half:return spec.root_diameter/2
    if spec.section=='Circular':depth=spec.height*math.sqrt(max(0,1-(dz/half)**2))
    else:depth=spec.height*min(1,(half-dz)/max(1e-9,(spec.width-spec.crest)/2))
    return spec.root_diameter/2-depth

def radial_surface(spec,outer=None,sides=48,normal_clearance=0):
    """Closed grooved cylinder, or annular nut with inward ribs."""
    steps=max(12,min(900,math.ceil(spec.length/spec.pitch*20)))
    coords=[];indices=[]
    for k in range(steps+1):
        z=spec.length*k/steps
        for i in range(sides):
            a=2*math.pi*i/sides;r=inward_radius(spec,a,z)
            if normal_clearance:
                # Offset the analytical bore/rib boundary along its surface normal.
                eps=1e-4
                rt=(inward_radius(spec,a+eps,z)-inward_radius(spec,a-eps,z))/(2*eps*r)
                rz=(inward_radius(spec,a,z+eps)-inward_radius(spec,a,z-eps))/(2*eps)
                norm=math.sqrt(1+rt*rt+rz*rz);rr=r+normal_clearance/norm;tt=-normal_clearance*rt/norm
                coords.extend((rr*math.cos(a)-tt*math.sin(a),rr*math.sin(a)+tt*math.cos(a),max(0,min(spec.length,z-normal_clearance*rz/norm))))
            else:coords.extend((r*math.cos(a),r*math.sin(a),z))
    for k in range(steps):
        for i in range(sides):
            j=(i+1)%sides;a=k*sides+i;b=k*sides+j;c=a+sides;d=b+sides
            indices.extend((a,b,d,a,d,c) if outer is None else (a,d,b,a,c,d))
    if outer is None:
        for z,k in ((0,0),(spec.length,steps)):
            center=len(coords)//3;coords.extend((0,0,z))
            for i in range(sides):
                a=k*sides+i;b=k*sides+(i+1)%sides
                indices.extend((center,b,a) if k==0 else (center,a,b))
    else:
        first=len(coords)//3
        for z in (0,spec.length):
            for i in range(sides):
                a=2*math.pi*i/sides;coords.extend((outer*math.cos(a),outer*math.sin(a),z))
        for i in range(sides):
            j=(i+1)%sides;a=first+i;b=first+j;c=a+sides;d=b+sides
            indices.extend((a,b,d,a,d,c,i,a,b,i,b,j,steps*sides+i,steps*sides+j,d,steps*sides+i,d,c))
    return coords,indices
