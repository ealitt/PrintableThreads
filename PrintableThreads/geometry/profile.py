"""Tangent circular fillets for a convex radial–axial polygon, in mm."""
import math

def rounded_trapezoid(root, height, width, crest, radius, overlap=.08):
    vertices=[(root-overlap,-width/2),(root+height,-crest/2),
              (root+height,crest/2),(root-overlap,width/2)]
    corners=[]
    for i,p in enumerate(vertices):
        a,b=vertices[i-1],vertices[(i+1)%4]
        la,lb=math.dist(p,a),math.dist(p,b)
        u=((a[0]-p[0])/la,(a[1]-p[1])/la)
        v=((b[0]-p[0])/lb,(b[1]-p[1])/lb)
        angle=math.acos(max(-1,min(1,u[0]*v[0]+u[1]*v[1])))
        # Root fillets are deliberately smaller, entirely within overlap.
        rad=min(radius,overlap/3) if i in (0,3) else radius
        distance=rad/math.tan(angle/2)
        if distance >= min(la,lb)*.49: raise ValueError('Profile corner radii overlap.')
        before=(p[0]+u[0]*distance,p[1]+u[1]*distance)
        after=(p[0]+v[0]*distance,p[1]+v[1]*distance)
        bis=(u[0]+v[0],u[1]+v[1]); norm=math.hypot(*bis)
        bis=(bis[0]/norm,bis[1]/norm)
        center=(p[0]+bis[0]*rad/math.sin(angle/2),p[1]+bis[1]*rad/math.sin(angle/2))
        mid=(center[0]-bis[0]*rad,center[1]-bis[1]*rad)
        corners.append((before,mid,after))
    segments=[]
    for i,(a,m,b) in enumerate(corners):
        if math.dist(a,b)>1e-10: segments.append(('arc',a,m,b))
        segments.append(('line',b,corners[(i+1)%4][0]))
    return segments
