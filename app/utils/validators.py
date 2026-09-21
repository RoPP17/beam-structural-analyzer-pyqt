"""
validators.py - System validators for structural modeling rules.
"""

from dataclasses import dataclass
from typing import List
from app.core.beam_model import BeamModel

@dataclass
class ValidationError:
    severity: str  # "ERROR" or "WARNING"
    message: str

class BeamValidator:
    """Validates the beam configuration before solving."""
    
    def validate_beam(self, beam: BeamModel) -> List[ValidationError]:
        errors = []
        
        # 1. Basic geometry
        if beam.length <= 0:
            errors.append(ValidationError("ERROR", "La longitud de la viga debe ser mayor que cero."))
            
        # 2. Minimum stability
        if not beam.supports:
            errors.append(ValidationError("ERROR", "La viga no tiene apoyos definidos."))
            
        # 3. Check determinacy
        unknowns = 0
        from app.core.supports import SupportType
        for s in beam.supports:
            if s.support_type == SupportType.PINNED:
                unknowns += 2
            elif s.support_type == SupportType.ROLLER:
                unknowns += 1
            elif s.support_type == SupportType.FIXED:
                unknowns += 3
                
        if unknowns < 3:
            errors.append(ValidationError("ERROR", f"El sistema es inestable (grados de libertad insuficientes, incógnitas: {unknowns})."))
        elif unknowns > 3:
            errors.append(ValidationError("ERROR", f"El sistema es hiperestático (incógnitas: {unknowns}). La versión actual solo resuelve vigas isostáticas."))
            
        # 4. Out of bounds
        for s in beam.supports:
            if s.position < 0 or s.position > beam.length:
                errors.append(ValidationError("ERROR", f"El apoyo '{s.name}' está fuera de los límites de la viga (x={s.position} m)."))
                
        for load in beam.loads:
            if hasattr(load, "position"):
                if load.position < 0 or load.position > beam.length:
                    errors.append(ValidationError("ERROR", f"Una carga puntual o momento está fuera de la viga (x={load.position} m)."))
            if hasattr(load, "start") and hasattr(load, "end"):
                if load.start < 0 or load.end > beam.length:
                    errors.append(ValidationError("ERROR", f"Una carga distribuida sale de los límites de la viga (x={load.start} a {load.end} m)."))
                    
        # Warnings
        if not beam.loads:
            errors.append(ValidationError("WARNING", "La viga no tiene cargas aplicadas. Las reacciones y diagramas serán nulos."))
            
        return errors
