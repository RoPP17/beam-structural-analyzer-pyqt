"""
solver.py - Solves support reactions using static equilibrium.
"""

import sympy as sp
from dataclasses import dataclass
from typing import Dict, List, Any
from app.core.beam_model import BeamModel
from app.core.supports import SupportType

@dataclass
class SolutionStep:
    description: str
    equation_latex: str
    result_latex: str

@dataclass
class SolutionResult:
    reactions: Dict[str, Dict[str, float]]  # {support_name: {"Rx": val, "Ry": val, "M": val}}
    steps: List[SolutionStep]
    is_valid: bool
    error_message: str = ""

class ReactionSolver:
    """Resuelve las reacciones de los apoyos usando SymPy y las ecuaciones de equilibrio."""
    
    def solve(self, beam: BeamModel) -> SolutionResult:
        steps = []
        reactions = {}
        
        # Count unknowns
        unknowns = []
        symbols_map = {}
        
        for support in beam.supports:
            if support.support_type == SupportType.PINNED:
                Rx = sp.Symbol(f'H_{support.name}')
                Ry = sp.Symbol(f'V_{support.name}')
                unknowns.extend([Rx, Ry])
                symbols_map[Rx] = (support.name, 'Rx')
                symbols_map[Ry] = (support.name, 'Ry')
            elif support.support_type == SupportType.ROLLER:
                Ry = sp.Symbol(f'V_{support.name}')
                unknowns.extend([Ry])
                symbols_map[Ry] = (support.name, 'Ry')
            elif support.support_type == SupportType.FIXED:
                Rx = sp.Symbol(f'H_{support.name}')
                Ry = sp.Symbol(f'V_{support.name}')
                M = sp.Symbol(f'M_{support.name}')
                unknowns.extend([Rx, Ry, M])
                symbols_map[Rx] = (support.name, 'Rx')
                symbols_map[Ry] = (support.name, 'Ry')
                symbols_map[M] = (support.name, 'M')
                
        if len(unknowns) != 3:
            return SolutionResult({}, [], False, f"La viga no es isostática (incógnitas: {len(unknowns)}).")
            
        # Equations: sum Fx = 0, sum Fy = 0, sum M_A = 0
        sum_Fx = 0
        sum_Fy = 0
        sum_M = 0
        
        # Add support reactions to equations
        for support in beam.supports:
            if support.support_type == SupportType.PINNED:
                Rx = sp.Symbol(f'H_{support.name}')
                Ry = sp.Symbol(f'V_{support.name}')
                sum_Fx += Rx
                sum_Fy += Ry
                sum_M += Ry * support.position
            elif support.support_type == SupportType.ROLLER:
                Ry = sp.Symbol(f'V_{support.name}')
                sum_Fy += Ry
                sum_M += Ry * support.position
            elif support.support_type == SupportType.FIXED:
                Rx = sp.Symbol(f'H_{support.name}')
                Ry = sp.Symbol(f'V_{support.name}')
                M = sp.Symbol(f'M_{support.name}')
                sum_Fx += Rx
                sum_Fy += Ry
                sum_M += Ry * support.position + M
                
        # Add applied loads
        for load in beam.loads:
            Fx = load.get_fx()
            Fy = load.get_fy()
            # Loads are usually positive down, so subtract from sum_Fy
            # Or if get_fy() returns positive for down, we subtract it:
            sum_Fx += Fx
            sum_Fy += Fy
            
            # Moments: positive CCW
            sum_M += load.moment_about(0)
            
        eq1 = sp.Eq(sum_Fx, 0)
        eq2 = sp.Eq(sum_Fy, 0)
        eq3 = sp.Eq(sum_M, 0)
        
        steps.append(SolutionStep(
            "Sumatoria de Fuerzas Horizontales (ΣFx = 0)",
            sp.latex(eq1),
            ""
        ))
        steps.append(SolutionStep(
            "Sumatoria de Fuerzas Verticales (ΣFy = 0)",
            sp.latex(eq2),
            ""
        ))
        steps.append(SolutionStep(
            "Sumatoria de Momentos desde el origen (ΣM = 0)",
            sp.latex(eq3),
            ""
        ))
        
        try:
            solution = sp.solve((eq1, eq2, eq3), unknowns)
            
            if not solution:
                 return SolutionResult({}, [], False, "El sistema de ecuaciones no tiene solución única.")
            
            for sym, val in solution.items():
                s_name, r_type = symbols_map[sym]
                if s_name not in reactions:
                    reactions[s_name] = {}
                reactions[s_name][r_type] = float(val)
                steps.append(SolutionStep(
                    f"Despejando {sp.latex(sym)}",
                    sp.latex(sym) + " = " + sp.latex(val),
                    f"{float(val):.3f}"
                ))
                
            return SolutionResult(reactions, steps, True)
            
        except Exception as e:
            return SolutionResult({}, [], False, f"Error al resolver el sistema: {str(e)}")
