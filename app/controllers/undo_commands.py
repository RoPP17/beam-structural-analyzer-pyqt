"""
undo_commands.py - QUndoCommand implementations for undo/redo support.
"""

from PyQt6.QtGui import QUndoCommand
from app.core.beam_model import BeamModel
from app.core.supports import Support
from app.core.loads import Load

class AddSupportCommand(QUndoCommand):
    def __init__(self, beam: BeamModel, support: Support):
        super().__init__(f"Agregar apoyo {support.name}")
        self.beam = beam
        self.support = support
        
    def redo(self):
        self.beam.add_support(self.support)
        
    def undo(self):
        self.beam.remove_support(self.support)

class RemoveSupportCommand(QUndoCommand):
    def __init__(self, beam: BeamModel, support: Support):
        super().__init__(f"Eliminar apoyo {support.name}")
        self.beam = beam
        self.support = support
        
    def redo(self):
        self.beam.remove_support(self.support)
        
    def undo(self):
        self.beam.add_support(self.support)

class AddLoadCommand(QUndoCommand):
    def __init__(self, beam: BeamModel, load: Load):
        super().__init__("Agregar carga")
        self.beam = beam
        self.load = load
        
    def redo(self):
        self.beam.add_load(self.load)
        
    def undo(self):
        self.beam.remove_load(self.load)

class RemoveLoadCommand(QUndoCommand):
    def __init__(self, beam: BeamModel, load: Load):
        super().__init__("Eliminar carga")
        self.beam = beam
        self.load = load
        
    def redo(self):
        self.beam.remove_load(self.load)
        
    def undo(self):
        self.beam.add_load(self.load)

class ModifyPropertyCommand(QUndoCommand):
    def __init__(self, obj: object, prop_name: str, old_val: float, new_val: float, callback=None):
        super().__init__(f"Modificar {prop_name}")
        self.obj = obj
        self.prop_name = prop_name
        self.old_val = old_val
        self.new_val = new_val
        self.callback = callback
        
    def redo(self):
        setattr(self.obj, self.prop_name, self.new_val)
        if self.callback:
            self.callback()
            
    def undo(self):
        setattr(self.obj, self.prop_name, self.old_val)
        if self.callback:
            self.callback()

class SetBeamLengthCommand(QUndoCommand):
    def __init__(self, beam: BeamModel, old_len: float, new_len: float):
        super().__init__(f"Cambiar longitud a {new_len} m")
        self.beam = beam
        self.old_len = old_len
        self.new_len = new_len
        
    def redo(self):
        self.beam.length = self.new_len
        
    def undo(self):
        self.beam.length = self.old_len
