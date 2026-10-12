"""Retain all command targets across Fusion preview / intent transitions."""
class TargetReference:
    def __init__(self):self.entity=None;self.token=None;self.executing=False

    def capture(self,selection_input):
        if self.executing:return self.entity
        entities=[selection_input.selection(i).entity for i in range(selection_input.selectionCount)]
        self.entity=(entities[0] if len(entities)==1 else tuple(entities)) if entities else None
        self.token=tuple(e.entityToken for e in entities) if len(entities)>1 else entities[0].entityToken if entities else None
        return self.entity

    def before_execute(self,selection_input):
        if selection_input.selectionCount:self.capture(selection_input)
        if self.entity is None:raise ValueError('Select cylindrical faces or a printable thread body before clicking OK.')
        self.executing=True
        return self.entity

    def resolve(self,design):
        entities=self.entity if isinstance(self.entity,tuple) else (self.entity,)
        tokens=self.token if isinstance(self.token,tuple) else (self.token,)
        resolved=[]
        for entity,token in zip(entities,tokens):
            if entity is not None and entity.isValid:resolved.append(entity);continue
            found=design.findEntityByToken(token) if token else []
            if len(found)!=1:raise ValueError('The selected geometry changed. Reopen the tool and select the faces again.')
            resolved.append(found[0])
        self.entity=tuple(resolved) if len(resolved)>1 else resolved[0]
        return self.entity
