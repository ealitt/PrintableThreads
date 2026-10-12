"""Near-realtime Custom Graphics renderer for command feedback."""
import adsk.core as core
import adsk.fusion as fusion

class Renderer:
    def __init__(self):self.group=None;self.hidden=None;self.was_visible=False
    def clear(self):
        if self.group and self.group.isValid:self.group.deleteMe()
        self.group=None
        if self.hidden and self.hidden.isValid:self.hidden.isLightBulbOn=self.was_visible
        self.hidden=None
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
    def draw_body(self,body,target=None,name='Solid preview'):
        calculator=body.meshManager.createMeshCalculator()
        calculator.setQuality(fusion.TriangleMeshQualityOptions.HighQualityTriangleMesh)
        mesh=calculator.calculate()
        coordinates=fusion.CustomGraphicsCoordinates.create(mesh.nodeCoordinatesAsDouble)
        graphic=self.group.addMesh(coordinates,mesh.nodeIndices,mesh.normalVectorsAsDouble,mesh.nodeIndices)
        graphic.name=name;graphic.depthPriority=0
        graphic.color=fusion.CustomGraphicsBasicMaterialColorEffect.create(core.Color.create(175,180,190,255),core.Color.create(70,70,75,255),core.Color.create(235,235,240,255),core.Color.create(0,0,0,255),32,1)
        graphic.setOpacity(1,True)
        for edge in body.edges:
            ok,start,end=edge.evaluator.getParameterExtents()
            if not ok:continue
            ok,points=edge.evaluator.getStrokes(start,end,.001)
            if not ok or len(points)<2:continue
            coordinates=fusion.CustomGraphicsCoordinates.create([v for p in points for v in (p.x,p.y,p.z)])
            line=self.group.addLines(coordinates,list(range(len(points))),True)
            line.color=fusion.CustomGraphicsSolidColorEffect.create(core.Color.create(45,45,50,255))
            line.weight=1.25;line.depthPriority=0
        if target:
            self.hidden=target;self.was_visible=target.isLightBulbOn;target.isLightBulbOn=False
        return graphic
    def finish(self):core.Application.get().activeViewport.refresh()
