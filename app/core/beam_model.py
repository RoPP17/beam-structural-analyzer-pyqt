"""
beam_model.py - Data model for the structural beam.
"""

from typing import List, Optional
from PyQt6.QtCore import QObject, pyqtSignal

from app.core.supports import Support
from app.core.loads import Load
from app.core.units import UnitSystem

class BeamModel(QObject):
    """
    Modelo de datos para la viga.
    Contiene la longitud, los apoyos, cargas y propiedades de material (E, I).
    """
    
    model_changed = pyqtSignal()
    solved_changed = pyqtSignal()
    
    def __init__(self, length: float = 10.0):
        super().__init__()
        self._length: float = length
        self._supports: List[Support] = []
        self._loads: List[Load] = []
        
        self.E: float = 200e9  # Modulo de elasticidad (Pa) - Acero por defecto
        self.I: float = 1.2e-4 # Momento de inercia (m^4)
        
        self.unit_system = UnitSystem()
        self.is_solved: bool = False
        
    @property
    def length(self) -> float:
        return self._length
        
    @length.setter
    def length(self, value: float):
        if value > 0:
            self._length = value
            self.is_solved = False
            self.model_changed.emit()
            
    @property
    def supports(self) -> List[Support]:
        return self._supports
        
    @property
    def loads(self) -> List[Load]:
        return self._loads
        
    def add_support(self, support: Support):
        """Agrega un apoyo a la viga."""
        self._supports.append(support)
        self.is_solved = False
        self.model_changed.emit()
        
    def remove_support(self, support: Support):
        """Elimina un apoyo de la viga."""
        if support in self._supports:
            self._supports.remove(support)
            self.is_solved = False
            self.model_changed.emit()
            
    def add_load(self, load: Load):
        """Agrega una carga a la viga."""
        self._loads.append(load)
        self.is_solved = False
        self.model_changed.emit()
        
    def remove_load(self, load: Load):
        """Elimina una carga de la viga."""
        if load in self._loads:
            self._loads.remove(load)
            self.is_solved = False
            self.model_changed.emit()
            
    def clear(self):
        """Elimina todos los apoyos y cargas."""
        self._supports.clear()
        self._loads.clear()
        self.is_solved = False
        self.model_changed.emit()
        
    def get_critical_points(self) -> List[float]:
        """
        Retorna las posiciones x donde hay cambios significativos 
        (apoyos, inicio/fin de cargas, etc.)
        """
        points = {0.0, self._length}
        for s in self._supports:
            points.add(s.position)
        for load in self._loads:
            if hasattr(load, "start") and hasattr(load, "end"):
                points.add(load.start)
                points.add(load.end)
            elif hasattr(load, "position"):
                points.add(load.position)
                
        return sorted(list(points))

    def validate(self) -> List[str]:
        """Validaciones básicas. Retorna lista de errores si los hay."""
        errors = []
        if self._length <= 0:
            errors.append("La longitud de la viga debe ser mayor que cero.")
        
        for s in self._supports:
            if not (0 <= s.position <= self._length):
                errors.append(f"El apoyo {s.name} está fuera de los límites de la viga.")
                
        for load in self._loads:
            if hasattr(load, "position"):
                if not (0 <= load.position <= self._length):
                    errors.append(f"Una carga está fuera de los límites de la viga.")
            elif hasattr(load, "start") and hasattr(load, "end"):
                if load.start < 0 or load.end > self._length:
                    errors.append(f"Una carga distribuida está fuera de los límites.")
                if load.start >= load.end:
                    errors.append(f"Carga distribuida inválida (inicio >= fin).")
                    
        return errors

    def to_dict(self) -> dict:
        """Serializa el modelo a un diccionario."""
        return {
            "length": self._length,
            "E": self.E,
            "I": self.I,
            "supports": [s.to_dict() for s in self._supports],
            "loads": [load.to_dict() for load in self._loads]
        }
        
    def from_dict(self, data: dict):
        """Carga el modelo desde un diccionario."""
        self._length = data.get("length", 10.0)
        self.E = data.get("E", 200e9)
        self.I = data.get("I", 1.2e-4)
        
        self._supports.clear()
        for s_data in data.get("supports", []):
            support = Support.from_dict(s_data)
            if support:
                self._supports.append(support)
                
        self._loads.clear()
        from app.core.loads import Load
        for l_data in data.get("loads", []):
            # Implementamos en load un factory o lo mapeamos aquí
            # Por simplicidad asumo que Load tiene algo que lo cargue,
            # lo completaré después
            pass
            
        self.is_solved = False
        self.model_changed.emit()
