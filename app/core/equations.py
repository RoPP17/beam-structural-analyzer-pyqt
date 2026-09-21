"""
equations.py - Builds piecewise symbolic equations for V(x) and M(x).
"""

import sympy as sp
from dataclasses import dataclass
from typing import List
from app.core.beam_model import BeamModel

@dataclass
class IntervalEquation:
    x_start: float
    x_end: float
    V_expr: sp.Expr
    M_expr: sp.Expr
    V_latex: str
    M_latex: str

@dataclass
class EquationsResult:
    intervals: List[IntervalEquation]

class PiecewiseEquationBuilder:
    """Construye las ecuaciones simbólicas por tramos usando SymPy."""
    
    def build(self, beam: BeamModel) -> EquationsResult:
        intervals = []
        critical_points = beam.get_critical_points()
        
        x_sym = sp.Symbol('x')
        
        # Iterar sobre cada intervalo [x_start, x_end]
        for i in range(len(critical_points) - 1):
            x_start = critical_points[i]
            x_end = critical_points[i+1]
            
            if x_end - x_start < 1e-5:
                continue
                
            # Calcular V(x) y M(x) para un punto genérico x en este intervalo
            # sumando las contribuciones de las cargas a la IZQUIERDA del corte x.
            
            V_expr = sp.Integer(0)
            M_expr = sp.Integer(0)
            
            # Supports (reactions are applied forces to the left)
            for support in beam.supports:
                if support.position <= x_start:
                    # Upward force adds to positive shear
                    V_expr += support.reaction_y
                    M_expr += support.reaction_y * (x_sym - support.position)
                    
                    if support.reaction_moment != 0:
                        M_expr -= support.reaction_moment
            
            # Loads
            from app.core.loads import PointLoad, MomentLoad, DistributedLoad, TriangularLoad, TrapezoidalLoad, InclinedLoad
            for load in beam.loads:
                if isinstance(load, (PointLoad, InclinedLoad)):
                    if load.position <= x_start:
                        fy = load.get_fy()
                        V_expr += fy
                        M_expr += fy * (x_sym - load.position)
                elif isinstance(load, MomentLoad):
                    if load.position <= x_start:
                        M_expr -= load.magnitude
                elif isinstance(load, (DistributedLoad, TriangularLoad, TrapezoidalLoad)):
                    if load.start < x_end:
                        # La carga comienza antes del fin de este intervalo
                        # Se debe integrar w(t) dt desde start hasta min(x, load.end)
                        t = sp.Symbol('t')
                        if isinstance(load, DistributedLoad):
                            w_t = -load.w  # negativa hacia abajo
                        else:
                            L = load.end - load.start
                            if L > 0:
                                slope = (load.w_end - load.w_start) / L
                                w_t = -(load.w_start + slope * (t - load.start))
                            else:
                                w_t = sp.Integer(0)
                        
                        # El límite superior de integración depende de si estamos dentro de la carga o a la derecha
                        if load.end <= x_start:
                            # Toda la carga está a la izquierda
                            upper_limit = load.end
                        else:
                            # El corte x "corta" la carga
                            upper_limit = x_sym
                            
                        # V_contribution = integral(w(t) dt) from start to upper_limit
                        V_contrib = sp.integrate(w_t, (t, load.start, upper_limit))
                        V_expr += V_contrib
                        
                        # M_contribution = integral(w(t)*(x - t) dt)
                        M_contrib = sp.integrate(w_t * (x_sym - t), (t, load.start, upper_limit))
                        M_expr += M_contrib
                        
            # Simplify expressions
            V_expr = sp.simplify(V_expr)
            M_expr = sp.expand(M_expr) # expand looks better for polynomials
            
            # Clean tiny floating point values
            V_expr = self._clean_tiny_floats(V_expr)
            M_expr = self._clean_tiny_floats(M_expr)
            
            intervals.append(IntervalEquation(
                x_start=x_start,
                x_end=x_end,
                V_expr=V_expr,
                M_expr=M_expr,
                V_latex=sp.latex(V_expr),
                M_latex=sp.latex(M_expr)
            ))
            
        return EquationsResult(intervals)

    def _clean_tiny_floats(self, expr: sp.Expr, tol: float = 1e-10) -> sp.Expr:
        """Removes tiny floating point artifacts from SymPy expressions."""
        if isinstance(expr, sp.Float):
            if abs(expr) < tol:
                return sp.Integer(0)
            return sp.Float(round(float(expr), 3))
        elif expr.is_Add or expr.is_Mul:
            args = [self._clean_tiny_floats(arg, tol) for arg in expr.args]
            return type(expr)(*args)
        return expr
