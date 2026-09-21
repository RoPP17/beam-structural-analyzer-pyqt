"""
app_controller.py — Controlador principal de la aplicación.

Conecta el modelo de viga con la interfaz gráfica y el motor de cálculo.
Gestiona el flujo de datos, las herramientas, undo/redo y auto-guardado.
"""

from __future__ import annotations

from typing import Optional, Any

from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtGui import QUndoStack
from PyQt6.QtWidgets import QGraphicsItem

from app.core.beam_model import BeamModel
from app.core.supports import Support, SupportType
from app.core.loads import (
    PointLoad, DistributedLoad, TriangularLoad,
    TrapezoidalLoad, MomentLoad, InclinedLoad,
)
from app.core.solver import ReactionSolver, SolutionResult
from app.core.internal_forces import InternalForcesSolver, InternalForcesResult
from app.core.equations import PiecewiseEquationBuilder, EquationsResult
from app.core.critical_zones import CriticalZoneAnalyzer, CriticalZoneReport
from app.core.deflection import DeflectionSolver, DeflectionResult
from app.core.units import UnitSystem

from app.ui.beam_canvas import BeamScene, BeamCanvas, ToolMode, PIXELS_PER_METER
from app.controllers.undo_commands import (
    AddSupportCommand, RemoveSupportCommand,
    AddLoadCommand, RemoveLoadCommand,
    ModifyPropertyCommand, SetBeamLengthCommand,
)
from app.utils.validators import BeamValidator, ValidationError


class AppController(QObject):
    """
    Controlador central que conecta modelo ↔ vista ↔ motor de cálculo.

    Responsabilidades:
    - Gestionar el ciclo de vida del modelo de viga.
    - Traducir acciones de la UI en operaciones del modelo.
    - Disparar el pipeline de resolución automáticamente.
    - Coordinar la actualización de todos los paneles.
    """

    # Signals for UI updates
    solution_ready = pyqtSignal(object)        # SolutionResult
    diagrams_ready = pyqtSignal(object)        # InternalForcesResult
    equations_ready = pyqtSignal(object)       # EquationsResult
    critical_ready = pyqtSignal(object)        # CriticalZoneReport
    deflection_ready = pyqtSignal(object)      # DeflectionResult
    validation_errors = pyqtSignal(list)       # list[ValidationError]
    status_message = pyqtSignal(str)           # status bar message
    beam_created = pyqtSignal(float)           # beam length
    model_cleared = pyqtSignal()
    model_changed = pyqtSignal(object)         # BeamModel

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

        # Core model
        self._beam = BeamModel()
        self._unit_system = UnitSystem()

        # Undo/Redo
        self.undo_stack = QUndoStack(self)

        # Solvers
        self._reaction_solver = ReactionSolver()
        self._internal_solver = InternalForcesSolver()
        self._equation_builder = PiecewiseEquationBuilder()
        self._critical_analyzer = CriticalZoneAnalyzer()
        self._deflection_solver = DeflectionSolver()
        self._validator = BeamValidator()

        # Results cache
        self._solution: Optional[SolutionResult] = None
        self._forces: Optional[InternalForcesResult] = None
        self._equations: Optional[EquationsResult] = None
        self._critical: Optional[CriticalZoneReport] = None
        self._deflection: Optional[DeflectionResult] = None

        # Scene reference (set by main_window)
        self._scene: Optional[BeamScene] = None
        self._canvas: Optional[BeamCanvas] = None

        # Auto-recalc timer (debounce)
        self._recalc_timer = QTimer(self)
        self._recalc_timer.setSingleShot(True)
        self._recalc_timer.setInterval(300)  # ms
        self._recalc_timer.timeout.connect(self._run_solve_pipeline)

        # Item-to-model mapping
        self._item_map: dict[int, Any] = {}  # graphics item id -> model element
        self._next_support_name_idx: int = 0

    # ─── initialization ───────────────────────────────────
    def set_scene(self, scene: BeamScene, canvas: BeamCanvas) -> None:
        """Conecta el controlador con la escena gráfica."""
        self._scene = scene
        self._canvas = canvas
        scene.element_added.connect(self._on_element_added)
        scene.element_deleted.connect(self._on_element_deleted)
        scene.element_selected.connect(self._on_element_selected)

    # ─── beam operations ──────────────────────────────────
    def create_beam(self, length: float) -> None:
        """Crea una nueva viga con la longitud especificada."""
        self._beam = BeamModel(length=length)
        self._next_support_name_idx = 0
        self.undo_stack.clear()
        self._clear_results()

        if self._scene:
            self._scene.clear_all()
            self._scene.create_beam(length)

        self.beam_created.emit(length)
        self.status_message.emit(f"Viga creada: L = {length:.2f} m")

    def set_beam_length(self, length: float) -> None:
        """Cambia la longitud de la viga existente."""
        old_length = self._beam.length
        cmd = SetBeamLengthCommand(self._beam, old_length, length)
        self.undo_stack.push(cmd)
        if self._scene:
            self._scene.create_beam(length)
        self._schedule_recalc()

    def get_beam(self) -> BeamModel:
        return self._beam

    # ─── element operations ───────────────────────────────
    def _get_next_support_name(self) -> str:
        """Genera nombre secuencial para apoyos: A, B, C, ..."""
        name = chr(ord('A') + self._next_support_name_idx)
        self._next_support_name_idx += 1
        return name

    def add_element(self, type_name: str, data: dict) -> None:
        """Añade un elemento al modelo a partir de datos de un diálogo."""
        self._on_element_added(type_name, data)
        
    def get_element_by_index(self, group: str, idx: int) -> Optional[Any]:
        if group == "support" and 0 <= idx < len(self._beam.supports):
            return self._beam.supports[idx]
        elif group == "load" and 0 <= idx < len(self._beam.loads):
            return self._beam.loads[idx]
        return None

    def update_element_by_index(self, group: str, idx: int, data: dict) -> None:
        """Actualiza un elemento existente. (Por simplicidad, lo reemplazamos)."""
        elem = self.get_element_by_index(group, idx)
        if not elem:
            return
            
        self.delete_element_by_index(group, idx)
        self.add_element(data["type"], data)

    def delete_element_by_index(self, group: str, idx: int) -> None:
        """Elimina un elemento del modelo usando su grupo e índice."""
        if group == "support" and 0 <= idx < len(self._beam.supports):
            support = self._beam.supports[idx]
            cmd = RemoveSupportCommand(self._beam, support)
            self.undo_stack.push(cmd)
            self.status_message.emit(f"Apoyo {support.name} eliminado")
            self._schedule_recalc()
        elif group == "load" and 0 <= idx < len(self._beam.loads):
            load = self._beam.loads[idx]
            cmd = RemoveLoadCommand(self._beam, load)
            self.undo_stack.push(cmd)
            self.status_message.emit("Carga eliminada")
            self._schedule_recalc()

    def _on_element_added(self, type_name: str, data: dict) -> None:
        if type_name in ("pinned", "roller", "fixed"):
            stype = {
                "pinned": SupportType.PINNED,
                "roller": SupportType.ROLLER,
                "fixed": SupportType.FIXED,
            }[type_name]
            name = self._get_next_support_name()
            support = Support(
                support_type=stype,
                position=data["position"],
                name=name,
            )
            cmd = AddSupportCommand(self._beam, support)
            self.undo_stack.push(cmd)
            self.status_message.emit(
                f"Apoyo {name} ({type_name}) agregado en x = {data['position']:.2f} m"
            )

        elif type_name == "point_load":
            load = PointLoad(
                position=data["position"],
                magnitude=data.get("magnitude", 10.0),
            )
            cmd = AddLoadCommand(self._beam, load)
            self.undo_stack.push(cmd)
            self.status_message.emit(
                f"Carga puntual de {load.magnitude:.1f} kN en x = {data['position']:.2f} m"
            )

        elif type_name == "distributed":
            load = DistributedLoad(
                start=data["start"],
                end=data["end"],
                w=data.get("w", 5.0),
            )
            cmd = AddLoadCommand(self._beam, load)
            self.undo_stack.push(cmd)
            self.status_message.emit(
                f"Carga distribuida de {load.w:.1f} kN/m de {data['start']:.2f} a {data['end']:.2f} m"
            )

        elif type_name == "triangular":
            load = TriangularLoad(
                start=data["start"],
                end=data["end"],
                w_start=data.get("w_start", 0.0),
                w_end=data.get("w_end", 10.0),
            )
            cmd = AddLoadCommand(self._beam, load)
            self.undo_stack.push(cmd)
            self.status_message.emit("Carga triangular agregada")

        elif type_name == "trapezoidal":
            load = TrapezoidalLoad(
                start=data["start"],
                end=data["end"],
                w_start=data.get("w_start", 5.0),
                w_end=data.get("w_end", 15.0),
            )
            cmd = AddLoadCommand(self._beam, load)
            self.undo_stack.push(cmd)
            self.status_message.emit("Carga trapezoidal agregada")

        elif type_name == "moment":
            load = MomentLoad(
                position=data["position"],
                magnitude=data.get("magnitude", 20.0),
            )
            cmd = AddLoadCommand(self._beam, load)
            self.undo_stack.push(cmd)
            self.status_message.emit(
                f"Momento de {load.magnitude:.1f} kN·m en x = {data['position']:.2f} m"
            )

        elif type_name == "inclined":
            load = InclinedLoad(
                position=data["position"],
                magnitude=data.get("magnitude", 10.0),
                angle=data.get("angle", 45.0),
            )
            cmd = AddLoadCommand(self._beam, load)
            self.undo_stack.push(cmd)
            self.status_message.emit(
                f"Carga inclinada de {load.magnitude:.1f} kN a {load.angle:.0f}° en x = {data['position']:.2f} m"
            )

        self._schedule_recalc()

    def _on_element_deleted(self, item: QGraphicsItem) -> None:
        """Callback cuando se elimina un elemento de la escena visual (ya no usado si se usa la tabla)."""
        if self._scene:
            self._scene.removeItem(item)
        self.status_message.emit("Elemento eliminado")
        self._schedule_recalc()

    def _on_element_selected(self, item: Optional[QGraphicsItem]) -> None:
        """Callback cuando se selecciona un elemento."""
        pass  # MainWindow will connect to update property panel

    # ─── solve pipeline ───────────────────────────────────
    def _schedule_recalc(self) -> None:
        """Programa un recálculo con debounce."""
        self._recalc_timer.start()

    def solve(self) -> None:
        """Ejecuta manualmente el pipeline de resolución."""
        self._run_solve_pipeline()

    def _run_solve_pipeline(self) -> None:
        """
        Pipeline completo de resolución:
        1. Validar configuración
        2. Resolver reacciones
        3. Calcular fuerzas internas
        4. Construir ecuaciones por tramos
        5. Analizar zonas críticas
        6. Calcular deflexión
        """
        # Notificar que el modelo y gráficos cambiaron independientemente de la resolución
        if self._scene:
            self._scene.render_beam_model(self._beam)
        self.model_changed.emit(self._beam)

        # Validar
        errors = self._validator.validate_beam(self._beam)
        critical_errors = [e for e in errors if e.severity == "ERROR"]
        if critical_errors:
            self.validation_errors.emit(errors)
            self._clear_results()
            return

        if errors:
            self.validation_errors.emit(errors)

        try:
            # 1. Resolver reacciones
            self._solution = self._reaction_solver.solve(self._beam)
            if not self._solution.is_valid:
                self.status_message.emit(
                    f"Error en resolución: {self._solution.error_message}"
                )
                self._clear_results()
                return
            self.solution_ready.emit(self._solution)

            # Aplicar reacciones al modelo
            for name, reactions in self._solution.reactions.items():
                for support in self._beam.supports:
                    if support.name == name:
                        support.reaction_x = reactions.get("Rx", 0.0)
                        support.reaction_y = reactions.get("Ry", 0.0)
                        support.reaction_moment = reactions.get("M", 0.0)

            # Update support reaction labels on canvas
            if self._scene:
                self._scene.update_support_reactions(self._solution.reactions)

            # 2. Fuerzas internas
            self._forces = self._internal_solver.compute(self._beam, n_points=2000)
            self.diagrams_ready.emit(self._forces)

            # 3. Ecuaciones por tramos
            self._equations = self._equation_builder.build(self._beam)
            self.equations_ready.emit(self._equations)

            # 4. Zonas críticas
            self._critical = self._critical_analyzer.analyze(
                self._forces.x_vals, self._forces.V_vals,
                self._forces.M_vals, self._beam,
            )
            self.critical_ready.emit(self._critical)

            # 5. Deflexión
            self._deflection = self._deflection_solver.compute(
                self._beam, self._forces.x_vals, self._forces.M_vals,
            )
            self.deflection_ready.emit(self._deflection)

            self.status_message.emit("✓ Análisis completado exitosamente")

        except Exception as e:
            self.status_message.emit(f"Error durante el análisis: {str(e)}")
            import traceback
            traceback.print_exc()

    def _clear_results(self) -> None:
        """Limpia todos los resultados almacenados."""
        self._solution = None
        self._forces = None
        self._equations = None
        self._critical = None
        self._deflection = None

    # ─── getters for results ──────────────────────────────
    def get_solution(self) -> Optional[SolutionResult]:
        return self._solution

    def get_forces(self) -> Optional[InternalForcesResult]:
        return self._forces

    def get_equations(self) -> Optional[EquationsResult]:
        return self._equations

    def get_critical_report(self) -> Optional[CriticalZoneReport]:
        return self._critical

    def get_deflection(self) -> Optional[DeflectionResult]:
        return self._deflection

    # ─── tool mode ────────────────────────────────────────
    def set_tool_mode(self, mode_name: str) -> None:
        """Establece el modo de herramienta actual por nombre."""
        mode_map = {
            "select": ToolMode.SELECT,
            "create_beam": ToolMode.CREATE_BEAM,
            "pinned": ToolMode.ADD_PINNED,
            "roller": ToolMode.ADD_ROLLER,
            "fixed": ToolMode.ADD_FIXED,
            "point_load": ToolMode.ADD_POINT_LOAD,
            "distributed": ToolMode.ADD_DISTRIBUTED,
            "triangular": ToolMode.ADD_TRIANGULAR,
            "trapezoidal": ToolMode.ADD_TRAPEZOIDAL,
            "moment": ToolMode.ADD_MOMENT,
            "inclined": ToolMode.ADD_INCLINED,
            "delete": ToolMode.DELETE,
        }
        mode = mode_map.get(mode_name, ToolMode.SELECT)
        if self._scene:
            self._scene.set_tool_mode(mode)

    # ─── templates ────────────────────────────────────────
    def load_template(self, template_beam: BeamModel) -> None:
        """Carga un modelo de viga predefinido como plantilla."""
        self._beam = template_beam
        self._next_support_name_idx = len(template_beam.supports)
        self.undo_stack.clear()

        self.beam_created.emit(template_beam.length)
        self.status_message.emit("Plantilla cargada exitosamente")
        self._schedule_recalc()

    # ─── clear / new ──────────────────────────────────────
    def new_project(self) -> None:
        """Limpia todo para un proyecto nuevo."""
        self._beam = BeamModel()
        self._next_support_name_idx = 0
        self.undo_stack.clear()
        self._clear_results()
        if self._scene:
            self._scene.clear_all()
        self.model_cleared.emit()
        self.status_message.emit("Nuevo proyecto creado")
