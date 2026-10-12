"""Near-realtime Custom Graphics renderer for command feedback."""
import adsk.core as core
import adsk.fusion as fusion

class Renderer:
    def __init__(self):self.group=None;self.hidden=[]
    def clear(self):
        if self.group and self.group.isValid:self.group.deleteMe()
        self.group=None
        for target,visible in self.hidden:
            if target.isValid:target.isLightBulbOn=visible
        self.hidden=[]
    def begin(self,component):
        self.clear();self.group=component.customGraphicsGroups.add();self.group.name='Printable Threads live preview'
        return self
    def draw(self,mesh,matrix=None,color=(175,180,190),opacity=1,name='Printable Threads preview'):
        coords,indices=mesh
        if not coords or not indices:return None
        points=fusion.CustomGraphicsCoordinates.create([v/10 for v in coords])
        graphic=self.group.addMesh(points,indices,[],[]);graphic.name=name
        graphic.color=fusion.CustomGraphicsSolidColorEffect.create(core.Color.create(*color,255))
        graphic.setOpacity(opacity,True)
        if matrix:graphic.transform=matrix
        try:graphic.depthPriority=5
        except Exception:pass
        return graphic
    def prepare_body(self,body):
        calculator=body.meshManager.createMeshCalculator()
        calculator.setQuality(fusion.TriangleMeshQualityOptions.NormalQualityTriangleMesh)
        calculator.surfaceTolerance=.002
        mesh=calculator.calculate()
        edge_coordinates=[];edge_indices=[]
        for edge in body.edges:
            ok,start,end=edge.evaluator.getParameterExtents()
            if not ok:continue
            ok,points=edge.evaluator.getStrokes(start,end,.001)
            if not ok or len(points)<2:continue
            offset=len(edge_coordinates)//3
            edge_coordinates.extend(v for p in points for v in (p.x,p.y,p.z))
            for i in range(len(points)-1):edge_indices.extend((offset+i,offset+i+1))
        return (mesh.nodeCoordinatesAsDouble,mesh.nodeIndices,mesh.normalVectorsAsDouble,edge_coordinates,edge_indices)
    def draw_body(self,body,target=None,name='Solid preview'):
        return self.draw_prepared(self.prepare_body(body),target,name)
    def draw_prepared(self,data,target=None,name='Solid preview'):
        nodes,indices,normals,edge_coordinates,edge_indices=data
        coordinates=fusion.CustomGraphicsCoordinates.create(nodes)
        graphic=self.group.addMesh(coordinates,indices,normals,indices)
        graphic.name=name;graphic.depthPriority=0
        graphic.color=fusion.CustomGraphicsBasicMaterialColorEffect.create(core.Color.create(175,180,190,255),core.Color.create(70,70,75,255),core.Color.create(235,235,240,255),core.Color.create(0,0,0,255),32,1)
        graphic.setOpacity(1,True)
        if edge_indices:
            coordinates=fusion.CustomGraphicsCoordinates.create(edge_coordinates)
            line=self.group.addLines(coordinates,edge_indices,False)
            line.color=fusion.CustomGraphicsSolidColorEffect.create(core.Color.create(45,45,50,255))
            line.weight=1.25;line.depthPriority=0
        if target:
            native=target.nativeObject or target
            if not any(item==native for item,_ in self.hidden):
                self.hidden.append((native,native.isLightBulbOn));native.isLightBulbOn=False
        return graphic
    def finish(self):core.Application.get().activeViewport.refresh()
