"""
beam_canvas.py — Lienzo interactivo para modelado de vigas.

Implementa un QGraphicsView/QGraphicsScene con herramientas
de colocación, arrastre, zoom y pan para modelar vigas 2D.
"""

from __future__ import annotations

from enum import Enum, auto
from typing import Optional

from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QBrush, QWheelEvent,
    QMouseEvent, QKeyEvent, QCursor,
)
from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsItem,
    QMenu, QWidget,
)

from app.render.beam_renderer import BeamGraphicsItem
from app.render.support_renderer import (
    PinnedSupportItem, RollerSupportItem, FixedSupportItem,
)
from app.render.load_renderer import (
    PointLoadItem, DistributedLoadItem, TriangularLoadItem,
    TrapezoidalLoadItem, MomentLoadItem, InclinedLoadItem,
)
from app.render.dimension_renderer import GridOverlay, CoordinateLabel
from app.render.colors import ThemeColors


class ToolMode(Enum):
    """Modos de herramienta disponibles en el lienzo."""
    SELECT = auto()
    DELETE = auto()
    CREATE_BEAM = auto()


# Scale: 1 meter = PIXELS_PER_METER pixels on screen
PIXELS_PER_METER: float = 80.0


class BeamScene(QGraphicsScene):
    """
    Escena gráfica que contiene todos los elementos estructurales.

    Gestiona la colocación de elementos, el modo de herramienta activo
    y la interacción con el modelo de viga.
    """

    element_added = pyqtSignal(str, object)  # (type_name, data_dict)
    element_selected = pyqtSignal(object)    # graphics item or None
    element_moved = pyqtSignal(object, float, float)  # item, old_x, new_x
    element_deleted = pyqtSignal(object)
    cursor_position_changed = pyqtSignal(float, float)  # scene x, y in meters

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._tool_mode = ToolMode.SELECT
        self._beam_item: Optional[BeamGraphicsItem] = None
        self._beam_length: float = 0.0
        self._grid: Optional[GridOverlay] = None
        self._theme = ThemeColors()

        self.setSceneRect(-200, -400, 2000, 800)
        self._setup_grid()

    # ─── setup ─────────────────────────────────────────────
    def _setup_grid(self) -> None:
        """Configura la cuadrícula de fondo."""
        self._grid = GridOverlay(
            width=2000, height=800,
            spacing=PIXELS_PER_METER,
            color=QColor(self._theme.get_color("grid_color")),
        )
        self._grid.setPos(-200, -400)
        self._grid.setZValue(-10)
        self.addItem(self._grid)

    # ─── beam management ──────────────────────────────────
    def create_beam(self, length: float) -> None:
        """Crea o reemplaza la viga en la escena."""
        if self._beam_item is not None:
            self.removeItem(self._beam_item)

        self._beam_length = length
        self._beam_item = BeamGraphicsItem(
            length=length,
            scale_factor=PIXELS_PER_METER,
        )
        self._beam_item.setPos(0, 0)
        self._beam_item.setZValue(0)
        self.addItem(self._beam_item)

    def get_beam_item(self) -> Optional[BeamGraphicsItem]:
        return self._beam_item

    # ─── tool mode ────────────────────────────────────────
    def set_tool_mode(self, mode: ToolMode) -> None:
        self._tool_mode = mode

    def get_tool_mode(self) -> ToolMode:
        return self._tool_mode

    # ─── coordinate helpers ───────────────────────────────
    def scene_to_beam_x(self, scene_x: float) -> float:
        """Convierte coordenada de escena a posición en metros sobre la viga."""
        return scene_x / PIXELS_PER_METER

    def beam_to_scene_x(self, beam_x: float) -> float:
        """Convierte posición en metros a coordenada de escena."""
        return beam_x * PIXELS_PER_METER

    def snap_to_beam(self, scene_pos: QPointF) -> Optional[float]:
        """
        Ajusta una posición de escena a la línea de la viga, 
        aplicando snapping a extremos y divisiones de 0.5m.
        """
        if self._beam_item is None:
            return None
        x_m = self.scene_to_beam_x(scene_pos.x())
        if 0 <= x_m <= self._beam_length:
            # Tolerancia de snapping en metros (ej. 0.2m)
            snap_tol = 0.2
            
            # Snap a 0
            if abs(x_m - 0) < snap_tol:
                return 0.0
            # Snap a L
            if abs(x_m - self._beam_length) < snap_tol:
                return self._beam_length
            
            # Snap a multiplos de 0.5
            nearest_half = round(x_m * 2) / 2
            if abs(x_m - nearest_half) < snap_tol:
                return nearest_half
                
            return round(x_m, 3)
        return None

    # ─── mouse events ─────────────────────────────────────
    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        """Gestiona clics según el modo de herramienta activo."""
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        if self._tool_mode == ToolMode.SELECT:
            super().mousePressEvent(event)
            sel = self.selectedItems()
            self.element_selected.emit(sel[0] if sel else None)
            return

        if self._tool_mode == ToolMode.DELETE:
            item = self.itemAt(event.scenePos(), self.views()[0].transform() if self.views() else __import__('PyQt6.QtGui', fromlist=['QTransform']).QTransform())
            if item and item is not self._beam_item and item is not self._grid:
                self.element_deleted.emit(item)
            return

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        """Emite la posición del cursor en coordenadas de la viga."""
        pos = event.scenePos()
        x_m = self.scene_to_beam_x(pos.x())
        y_m = -pos.y() / PIXELS_PER_METER  # Y invertido
        self.cursor_position_changed.emit(x_m, y_m)
        super().mouseMoveEvent(event)

    # ─── element management ───────────────────────────────
    def clear_elements(self) -> None:
        """Elimina todos los elementos excepto la viga y la cuadrícula."""
        for item in list(self.items()):
            if item is not self._beam_item and item is not self._grid:
                self.removeItem(item)

    def clear_all(self) -> None:
        """Elimina absolutamente todo de la escena."""
        self.clear()
        self._beam_item = None
        self._setup_grid()

    def get_all_structural_items(self) -> list[QGraphicsItem]:
        """Devuelve todos los items estructurales (apoyos, cargas, momentos)."""
        return [
            item for item in self.items()
            if item is not self._beam_item
            and item is not self._grid
            and not isinstance(item, CoordinateLabel)
        ]

    def update_support_reactions(self, reactions: dict[str, dict]) -> None:
        """
        Actualiza las etiquetas de reacciones en los apoyos.

        Args:
            reactions: {support_name: {"Rx": val, "Ry": val, "M": val}}
        """
        for item in self.items():
            if isinstance(item, (PinnedSupportItem, RollerSupportItem, FixedSupportItem)):
                name = getattr(item, "_label", "")
                if name in reactions:
                    item.reaction_values = reactions[name]

    def render_beam_model(self, beam) -> None:
        """Reconstruye los elementos gráficos a partir del modelo."""
        from app.core.supports import SupportType
        from app.core.loads import PointLoad, DistributedLoad, TriangularLoad, TrapezoidalLoad, MomentLoad, InclinedLoad
        
        self.clear_elements()
        if self._beam_item is None:
            self.create_beam(beam.length)
            
        # Draw supports
        for support in beam.supports:
            scene_x = self.beam_to_scene_x(support.position)
            if support.support_type == SupportType.PINNED:
                item = PinnedSupportItem(label=support.name)
            elif support.support_type == SupportType.ROLLER:
                item = RollerSupportItem(label=support.name)
            else:
                item = FixedSupportItem(label=support.name)
            item.setPos(scene_x, 0)
            item.setZValue(1)
            # ItemIsMovable is false by default in renderer now
            self.addItem(item)
            
        # Draw loads
        for load in beam.loads:
            scene_x = self.beam_to_scene_x(load.position) if hasattr(load, "position") else self.beam_to_scene_x(load.start)
            
            if isinstance(load, PointLoad):
                item = PointLoadItem(magnitude=load.magnitude)
                item.setPos(scene_x, 0)
            elif isinstance(load, DistributedLoad) and not isinstance(load, (TriangularLoad, TrapezoidalLoad)):
                w = (load.end - load.start) * PIXELS_PER_METER
                item = DistributedLoadItem(
                    width=w, intensity=load.w,
                    scale_factor=PIXELS_PER_METER,
                )
                item.setPos(self.beam_to_scene_x(load.start), 0)
            elif isinstance(load, TriangularLoad):
                w = (load.end - load.start) * PIXELS_PER_METER
                item = TriangularLoadItem(
                    width=w, w_start=load.w_start, w_end=load.w_end,
                    scale_factor=PIXELS_PER_METER,
                )
                item.setPos(self.beam_to_scene_x(load.start), 0)
            elif isinstance(load, TrapezoidalLoad):
                w = (load.end - load.start) * PIXELS_PER_METER
                item = TrapezoidalLoadItem(
                    width=w, w_start=load.w_start, w_end=load.w_end,
                    scale_factor=PIXELS_PER_METER,
                )
                item.setPos(self.beam_to_scene_x(load.start), 0)
            elif isinstance(load, MomentLoad):
                item = MomentLoadItem(magnitude=load.magnitude)
                item.setPos(scene_x, 0)
            elif isinstance(load, InclinedLoad):
                item = InclinedLoadItem(magnitude=load.magnitude, angle=load.angle)
                item.setPos(scene_x, 0)
            else:
                continue
                
            item.setZValue(2)
            self.addItem(item)


class BeamCanvas(QGraphicsView):
    """
    Vista interactiva del lienzo de la viga.

    Proporciona zoom con rueda del ratón, pan con clic central,
    y renderizado antialiased de alta calidad.
    """

    ZOOM_MIN: float = 0.15
    ZOOM_MAX: float = 8.0
    ZOOM_STEP: float = 1.12

    zoom_changed = pyqtSignal(float)

    def __init__(self, scene: BeamScene, parent: Optional[QWidget] = None) -> None:
        super().__init__(scene, parent)
        self._zoom_level: float = 1.0
        self._is_panning: bool = False
        self._pan_start: QPointF = QPointF()
        self._theme = ThemeColors()

        self._setup_view()

    def _setup_view(self) -> None:
        """Configura las opciones de renderizado y comportamiento."""
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
            | QPainter.RenderHint.TextAntialiasing
        )
        self.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.FullViewportUpdate
        )
        self.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse
        )
        self.setResizeAnchor(
            QGraphicsView.ViewportAnchor.AnchorViewCenter
        )
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        bg = self._theme.get_color("bg_primary")
        self.setStyleSheet(f"QGraphicsView {{ border: none; background-color: {bg}; }}")

    # ─── zoom ─────────────────────────────────────────────
    def wheelEvent(self, event: QWheelEvent) -> None:  # type: ignore[override]
        """Zoom con la rueda del ratón."""
        if event.angleDelta().y() > 0:
            factor = self.ZOOM_STEP
        else:
            factor = 1.0 / self.ZOOM_STEP

        new_zoom = self._zoom_level * factor
        if self.ZOOM_MIN <= new_zoom <= self.ZOOM_MAX:
            self.scale(factor, factor)
            self._zoom_level = new_zoom
            self.zoom_changed.emit(self._zoom_level)

    # ─── pan ──────────────────────────────────────────────
    def mousePressEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        """Inicia paneo con clic central o Ctrl+clic izquierdo."""
        if (event.button() == Qt.MouseButton.MiddleButton
                or (event.button() == Qt.MouseButton.LeftButton
                    and event.modifiers() & Qt.KeyboardModifier.ControlModifier)):
            self._is_panning = True
            self._pan_start = event.position()
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        """Mueve la vista durante el paneo."""
        if self._is_panning:
            delta = event.position() - self._pan_start
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x())
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y())
            )
            self._pan_start = event.position()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        """Finaliza el paneo."""
        if self._is_panning and (
            event.button() == Qt.MouseButton.MiddleButton
            or event.button() == Qt.MouseButton.LeftButton
        ):
            self._is_panning = False
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            event.accept()
            return
        super().mouseReleaseEvent(event)

    # ─── keyboard shortcuts ───────────────────────────────
    def keyPressEvent(self, event: QKeyEvent) -> None:  # type: ignore[override]
        """Atajos de teclado: Escape para seleccionar, Delete para eliminar."""
        if event.key() == Qt.Key.Key_Escape:
            scene: BeamScene = self.scene()  # type: ignore
            scene.set_tool_mode(ToolMode.SELECT)
        elif event.key() == Qt.Key.Key_Delete:
            scene: BeamScene = self.scene()  # type: ignore
            for item in scene.selectedItems():
                if item is not scene.get_beam_item():
                    scene.element_deleted.emit(item)
        else:
            super().keyPressEvent(event)

    # ─── public api ───────────────────────────────────────
    def reset_zoom(self) -> None:
        """Reinicia el zoom al 100%."""
        self.resetTransform()
        self._zoom_level = 1.0
        self.zoom_changed.emit(1.0)

    def zoom_to_fit(self) -> None:
        """Ajusta la vista para mostrar toda la viga."""
        scene: BeamScene = self.scene()  # type: ignore
        beam = scene.get_beam_item()
        if beam is not None:
            rect = beam.boundingRect().translated(beam.pos())
            margin = 100
            rect.adjust(-margin, -margin, margin, margin)
            self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
            self._zoom_level = self.transform().m11()
            self.zoom_changed.emit(self._zoom_level)

    def get_zoom_level(self) -> float:
        return self._zoom_level
