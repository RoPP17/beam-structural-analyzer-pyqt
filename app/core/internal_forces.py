"""
internal_forces.py - Computation of Shear V(x) and Bending Moment M(x) diagrams.
"""

import numpy as np
from dataclasses import dataclass
from typing import Tuple
from app.core.beam_model import BeamModel
from app.core.supports import SupportType

@dataclass
class InternalForcesResult:
    x_vals: np.ndarray
    V_vals: np.ndarray
    M_vals: np.ndarray
    
    def get_values_at(self, x: float) -> Tuple[float, float]:
        """Returns (V, M) interpolated at specific x."""
        if x <= self.x_vals[0]:
            return self.V_vals[0], self.M_vals[0]
        if x >= self.x_vals[-1]:
            return self.V_vals[-1], self.M_vals[-1]
            
        # find closest index
        idx = np.searchsorted(self.x_vals, x)
        
        # linear interpolation
        x1, x2 = self.x_vals[idx-1], self.x_vals[idx]
        V1, V2 = self.V_vals[idx-1], self.V_vals[idx]
        M1, M2 = self.M_vals[idx-1], self.M_vals[idx]
        
        dx = x2 - x1
        if dx == 0:
            return V2, M2
            
        t = (x - x1) / dx
        V = V1 + t * (V2 - V1)
        M = M1 + t * (M2 - M1)
        return V, M

class InternalForcesSolver:
    """Calcula V(x) y M(x) numéricamente usando el método de las secciones."""
    
    def compute(self, beam: BeamModel, n_points: int = 2000) -> InternalForcesResult:
        x_vals = np.linspace(0, beam.length, n_points)
        V_vals = np.zeros(n_points)
        M_vals = np.zeros(n_points)
        
        # Add critical points to x_vals to ensure sharp jumps are captured
        critical_points = beam.get_critical_points()
        
        # Merge linspace with critical points and sort
        combined_x = np.sort(np.unique(np.concatenate([x_vals, critical_points])))
        
        # To handle discontinuities cleanly, slightly offset critical points (left and right limits)
        epsilon = 1e-6
        enhanced_x = []
        for x in combined_x:
            if x in critical_points:
                enhanced_x.extend([max(0, x - epsilon), x, min(beam.length, x + epsilon)])
            else:
                enhanced_x.append(x)
                
        final_x = np.sort(np.unique(np.array(enhanced_x)))
        n_final = len(final_x)
        
        V_final = np.zeros(n_final)
        M_final = np.zeros(n_final)
        
        # For each point, sum all forces/moments to the LEFT
        for i, x in enumerate(final_x):
            V = 0.0
            M = 0.0
            
            # Supports (reactions are treated as applied forces to the left section)
            # Positive upward
            for support in beam.supports:
                if support.position <= x:
                    # Reaction Y: positive upward = positive shear
                    V += support.reaction_y
                    M += support.reaction_y * (x - support.position)
                    
                    if support.support_type == SupportType.FIXED:
                        # Reaction Moment: CCW reaction causes negative internal moment
                        M -= support.reaction_moment
                        
            # Applied Loads
            from app.core.loads import DistributedLoad, TriangularLoad, TrapezoidalLoad, MomentLoad, PointLoad, InclinedLoad
            from app.core.loads import get_distributed_fy_up_to, get_distributed_moment_up_to
            
            for load in beam.loads:
                if isinstance(load, (DistributedLoad, TriangularLoad, TrapezoidalLoad)):
                    V += get_distributed_fy_up_to(load, x)
                    M += get_distributed_moment_up_to(load, x, cut=x)
                elif isinstance(load, MomentLoad):
                    if load.position <= x:
                        M -= load.magnitude
                else: # PointLoad, InclinedLoad
                    if load.position <= x:
                        V += load.get_fy()
                        M += load.get_fy() * (x - load.position)
                
            V_final[i] = V
            M_final[i] = M
            
        return InternalForcesResult(final_x, V_final, M_final)
