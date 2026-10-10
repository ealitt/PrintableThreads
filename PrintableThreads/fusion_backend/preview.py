"""Near-realtime Custom Graphics renderer for command feedback."""
import adsk.core as core
import adsk.fusion as fusion

class Renderer:
    def __init__(self):self.group=None
    def clear(self):
        if self.group and self.group.isValid:self.group.deleteMe()
        self.group=None
    def begin(self,component):
        self.clear();self.group=component.customGraphicsGroups.add();self.group.name='Printable Threads live preview'
        return self
    def draw(self,mesh,matrix=None,color=(45,155,255),opacity=.55,name='Printable Threads preview'):
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
    def finish(self):core.Application.get().activeViewport.refresh()
