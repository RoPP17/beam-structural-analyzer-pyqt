"""
critical_zones.py - Detects and interprets critical points in V(x) and M(x) diagrams.
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Dict
from app.core.beam_model import BeamModel

@dataclass
class CriticalZone:
    x_position: float
    zone_type: str
    value: float
    description: str

@dataclass
class CriticalZoneReport:
    critical_points: List[float]
    max_values: Dict[str, float]
    messages: List[str]
    zones: List[CriticalZone]

class CriticalZoneAnalyzer:
    """Encuentra puntos de cortante nulo, momentos máximos, etc."""
    
    def analyze(self, x_vals: np.ndarray, V_vals: np.ndarray, M_vals: np.ndarray, beam: BeamModel) -> CriticalZoneReport:
        zones = []
        messages = []
        max_values = {}
        critical_points = set()
        
        # Max/Min values
        idx_V_max = np.argmax(V_vals)
        idx_V_min = np.argmin(V_vals)
        idx_M_max = np.argmax(M_vals)
        idx_M_min = np.argmin(M_vals)
        
        max_values["V_max_pos"] = float(V_vals[idx_V_max])
        max_values["V_max_neg"] = float(V_vals[idx_V_min])
        max_values["V_abs_max"] = max(abs(max_values["V_max_pos"]), abs(max_values["V_max_neg"]))
        max_values["M_max_pos"] = float(M_vals[idx_M_max])
        max_values["M_max_neg"] = float(M_vals[idx_M_min])
        max_values["M_abs_max"] = max(abs(max_values["M_max_pos"]), abs(max_values["M_max_neg"]))
        
        # Find V=0 crossings (sign changes)
        sign_V = np.sign(V_vals)
        sign_changes_V = np.where(np.diff(sign_V) != 0)[0]
        
        for idx in sign_changes_V:
            # Interpolate to find exact x where V=0
            x1, x2 = x_vals[idx], x_vals[idx+1]
            V1, V2 = V_vals[idx], V_vals[idx+1]
            if V2 != V1:
                t = -V1 / (V2 - V1)
                x_zero = x1 + t * (x2 - x1)
                
                # Verify M at this point
                idx_closest = np.argmin(np.abs(x_vals - x_zero))
                M_at_zero = M_vals[idx_closest]
                
                critical_points.add(round(x_zero, 3))
                zones.append(CriticalZone(
                    x_position=x_zero,
                    zone_type="CORTANTE NULO",
                    value=M_at_zero,
                    description=f"Punto de cortante nulo. Momento local: {M_at_zero:.2f} kN·m."
                ))
        
        # Max Moment Zone
        zones.append(CriticalZone(
            x_position=x_vals[idx_M_max],
            zone_type="MOMENTO MÁX. POSITIVO",
            value=M_vals[idx_M_max],
            description=f"Esta sección presenta el mayor momento flector positivo (M = {M_vals[idx_M_max]:.2f} kN·m) y es la zona más crítica para diseño a flexión."
        ))
        critical_points.add(round(x_vals[idx_M_max], 3))
        
        if M_vals[idx_M_min] < 0:
            zones.append(CriticalZone(
                x_position=x_vals[idx_M_min],
                zone_type="MOMENTO MÁX. NEGATIVO",
                value=M_vals[idx_M_min],
                description=f"Mayor momento flector negativo (M = {M_vals[idx_M_min]:.2f} kN·m). Tensión en la fibra superior."
            ))
            critical_points.add(round(x_vals[idx_M_min], 3))
            
        # Max Shear Zone
        idx_abs_V_max = idx_V_max if abs(V_vals[idx_V_max]) >= abs(V_vals[idx_V_min]) else idx_V_min
        zones.append(CriticalZone(
            x_position=x_vals[idx_abs_V_max],
            zone_type="CORTANTE MÁXIMO",
            value=V_vals[idx_abs_V_max],
            description=f"El cortante máximo absoluto se encuentra en x = {x_vals[idx_abs_V_max]:.2f} m con V = {V_vals[idx_abs_V_max]:.2f} kN. Verificar capacidad a corte."
        ))
        critical_points.add(round(x_vals[idx_abs_V_max], 3))

        # Generate summary messages
        messages.append(f"El momento máximo absoluto es {max_values['M_abs_max']:.2f} kN·m.")
        messages.append(f"El cortante máximo absoluto es {max_values['V_abs_max']:.2f} kN.")
        if len(sign_changes_V) > 0:
            messages.append(f"Se encontraron {len(sign_changes_V)} puntos de inflexión de cortante (V=0).")
            
        zones.sort(key=lambda z: z.x_position)
        
        return CriticalZoneReport(
            critical_points=sorted(list(critical_points)),
            max_values=max_values,
            messages=messages,
            zones=zones
        )
