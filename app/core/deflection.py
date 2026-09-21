"""
deflection.py - Computes the approximate deflection curve.
"""

import numpy as np
from scipy.integrate import cumulative_trapezoid
from dataclasses import dataclass
from typing import Tuple
from app.core.beam_model import BeamModel
from app.core.supports import SupportType

@dataclass
class DeflectionResult:
    x_vals: np.ndarray
    y_vals: np.ndarray
    theta_vals: np.ndarray
    
    def get_max_deflection(self) -> Tuple[float, float]:
        """Returns (x, y_max) where y_max is the absolute maximum deflection."""
        idx = np.argmax(np.abs(self.y_vals))
        return float(self.x_vals[idx]), float(self.y_vals[idx])

class DeflectionSolver:
    """Calcula la curva elástica (deflexión) integrando numéricamente M(x)/(EI)."""
    
    def compute(self, beam: BeamModel, x_vals: np.ndarray, M_vals: np.ndarray) -> DeflectionResult:
        # EI = E * I (modulo de elasticidad * inercia)
        EI = beam.E * beam.I
        if EI == 0:
            EI = 1.0  # fallback to avoid division by zero
            
        M_over_EI = M_vals / EI
        
        # First integration: slope (theta)
        # theta = integral(M/EI dx) + C1
        # cumulative_trapezoid returns array of same size if initial=0
        theta_raw = cumulative_trapezoid(M_over_EI, x_vals, initial=0.0)
        
        # Second integration: deflection (y)
        # y = integral(theta dx) + C2
        y_raw = cumulative_trapezoid(theta_raw, x_vals, initial=0.0)
        
        # Apply boundary conditions to find C1 and C2
        # y(x) = y_raw(x) + C1*x + C2
        
        # Collect boundary conditions from supports
        # For pin/roller: y = 0
        # For fixed: y = 0, dy/dx = 0
        
        support_conditions = []
        for s in beam.supports:
            if s.support_type in (SupportType.PINNED, SupportType.ROLLER):
                support_conditions.append((s.position, 0.0))  # (x, y)
            elif s.support_type == SupportType.FIXED:
                # FIXED gives both y=0 and dy/dx=0
                # If we have a fixed support, we can directly find C1 and C2
                x_f = s.position
                # interpolate raw values at x_f
                idx = np.searchsorted(x_vals, x_f)
                if idx >= len(x_vals):
                    idx = len(x_vals) - 1
                
                # theta(x_f) = theta_raw(x_f) + C1 = 0 => C1 = -theta_raw(x_f)
                C1 = -theta_raw[idx]
                
                # y(x_f) = y_raw(x_f) + C1*x_f + C2 = 0 => C2 = -y_raw(x_f) - C1*x_f
                C2 = -y_raw[idx] - C1 * x_f
                
                theta_vals = theta_raw + C1
                y_vals = y_raw + C1 * x_vals + C2
                return DeflectionResult(x_vals, y_vals, theta_vals)

        # If no fixed support, we need at least two supports (pin/roller)
        if len(support_conditions) >= 2:
            x1, y1 = support_conditions[0]
            x2, y2 = support_conditions[1]
            
            # Find indices
            idx1 = min(np.searchsorted(x_vals, x1), len(x_vals) - 1)
            idx2 = min(np.searchsorted(x_vals, x2), len(x_vals) - 1)
            
            # System:
            # C1*x1 + C2 = -y_raw[idx1]
            # C1*x2 + C2 = -y_raw[idx2]
            
            A = np.array([[x1, 1], [x2, 1]])
            b = np.array([-y_raw[idx1], -y_raw[idx2]])
            
            try:
                C = np.linalg.solve(A, b)
                C1, C2 = C[0], C[1]
            except np.linalg.LinAlgError:
                C1, C2 = 0.0, 0.0
        else:
            # Fallback if unconstrained
            C1, C2 = 0.0, 0.0
            
        theta_vals = theta_raw + C1
        y_vals = y_raw + C1 * x_vals + C2
        
        return DeflectionResult(x_vals, y_vals, theta_vals)
