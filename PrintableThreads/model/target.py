"""Retain a command target across Fusion preview / design-intent transitions."""
class TargetReference:
    def __init__(self):self.entity=None;self.token=None;self.executing=False

    def capture(self,selection_input):
        if self.executing:return self.entity
        if selection_input.selectionCount!=1:
            self.entity=None;self.token=None
            return None
        self.entity=selection_input.selection(0).entity
        self.token=self.entity.entityToken
        return self.entity

    def before_execute(self,selection_input):
        if selection_input.selectionCount==1:self.capture(selection_input)
        if self.entity is None:raise ValueError('Select a cylindrical face or printable thread body before clicking OK.')
        self.executing=True
        return self.entity

    def resolve(self,design):
        if self.entity is not None and self.entity.isValid:return self.entity
        found=design.findEntityByToken(self.token) if self.token else []
        if len(found)!=1:raise ValueError('The selected geometry changed. Reopen the tool and select the face again.')
        self.entity=found[0]
        return self.entity
