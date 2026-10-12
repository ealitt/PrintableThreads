import unittest
from types import SimpleNamespace
from PrintableThreads.model.target import TargetReference

class TargetTests(unittest.TestCase):
    def test_selection_cleared_by_promotion(self):
        entity=SimpleNamespace(isValid=True,entityToken='face-token')
        selection=SimpleNamespace(selectionCount=1,selection=lambda index:SimpleNamespace(entity=entity))
        target=TargetReference();target.before_execute(selection)
        selection.selectionCount=0
        target.capture(selection)  # Fusion inputChanged during promotion.
        selection.selection=lambda index:(_ for _ in ()).throw(RuntimeError('invalid argument index'))
        self.assertIs(target.resolve(None),entity)
        self.assertIs(target.before_execute(selection),entity)
    def test_invalidated_entity_resolves_token(self):
        old=SimpleNamespace(isValid=True,entityToken='face-token')
        target=TargetReference();target.capture(SimpleNamespace(selectionCount=1,selection=lambda _:SimpleNamespace(entity=old)))
        old.isValid=False
        new=SimpleNamespace(isValid=True)
        self.assertIs(target.resolve(SimpleNamespace(findEntityByToken=lambda token:[new] if token=='face-token' else [])),new)
    def test_multi_face_capture_and_promotion(self):
        faces=tuple(SimpleNamespace(isValid=True,entityToken=str(i)) for i in range(2))
        selection=SimpleNamespace(selectionCount=2,selection=lambda i:SimpleNamespace(entity=faces[i]))
        target=TargetReference();self.assertEqual(target.before_execute(selection),faces)
        selection.selectionCount=0;target.capture(selection)
        self.assertEqual(target.resolve(None),faces)
        faces[1].isValid=False
        replacement=SimpleNamespace(isValid=True)
        self.assertEqual(target.resolve(SimpleNamespace(findEntityByToken=lambda token:[replacement])),(faces[0],replacement))
    def test_explicit_deselection_forgets_target(self):
        target=TargetReference();target.entity=object();target.token='old'
        selection=SimpleNamespace(selectionCount=0)
        target.capture(selection)
        with self.assertRaises(ValueError):target.before_execute(selection)
