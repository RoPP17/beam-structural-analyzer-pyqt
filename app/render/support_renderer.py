"""
Renderizado gráfico de los apoyos estructurales.

Proporciona ítems gráficos para los tres tipos de apoyo:

* ``PinnedSupportItem`` — apoyo articulado (triángulo + achurado)
* ``RollerSupportItem`` — apoyo de rodillo (triángulo + ruedas)
* ``FixedSupportItem`` — empotramiento (rectángulo + achurado)

Todos los ítems son arrastrables a lo largo del eje de la viga,
muestran tooltips, y pueden representar las reacciones calculadas.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QFont,
    QFontMetricsF,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
)
from PyQt6.QtWidgets import (
    QGraphicsItem,
    QGraphicsSceneContextMenuEvent,
    QGraphicsSceneHoverEvent,
    QGraphicsSceneMouseEvent,
    QMenu,
    QStyleOptionGraphicsItem,
    QWidget,
)

from app.render.colors import theme_colors


# ════════════════════════════════════════════════════════════
#  Base abstracta para apoyos
# ════════════════════════════════════════════════════════════

class _BaseSupportItem(QGraphicsItem):
    """
    Clase base para todos los ítems de apoyo.

    Gestiona la posición sobre la viga, arrastre horizontal,
    hover, selección, y renderizado de etiquetas de reacción.
    """

    # Tamaños de referencia
    TRIANGLE_HALF_BASE: float = 15.0
    TRIANGLE_HEIGHT: float = 22.0
    HATCH_WIDTH: float = 40.0
    HATCH_SPACING: float = 5.0
    HATCH_HEIGHT: float = 8.0
    REACTION_ARROW_LENGTH: float = 50.0
    REACTION_ARROW_HEAD: float = 8.0

    def __init__(
        self,
        x_position: float = 0.0,
        scale_factor: float = 100.0,
        label: str = "",
        parent: QGraphicsItem | None = None,
    ) -> None:
        super().__init__(parent)

        self._x_position: float = x_position
        self._scale_factor: float = scale_factor
        self._label: str = label
        self._hovered: bool = False
        self._reaction_values: dict[str, float] = {}
        self._beam_length: float = 10.0

        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, False)
        self.setZValue(1)

        self._update_position()

    # ── Propiedades ─────────────────────────────────────────

    @property
    def x_position(self) -> float:
        """Posición x del apoyo en metros."""
        return self._x_position

    @property
    def label(self) -> str:
        """Etiqueta del apoyo (e.g. 'A', 'B')."""
        return self._label

    @label.setter
    def label(self, value: str) -> None:
        self._label = value
        self._update_tooltip()
        self.update()

    @property
    def scale_factor(self) -> float:
        """Factor de escala px/m."""
        return self._scale_factor

    @scale_factor.setter
    def scale_factor(self, value: float) -> None:
        self._scale_factor = max(1.0, value)
        self._update_position()

    @property
    def beam_length(self) -> float:
        """Longitud de la viga para limitar el arrastre."""
        return self._beam_length

    @beam_length.setter
    def beam_length(self, value: float) -> None:
        self._beam_length = value

    # ── Posicionamiento ─────────────────────────────────────

    def setPosition(self, x_meters: float) -> None:
        """
        Posiciona el apoyo en la coordenada x (metros) sobre la viga.

        Args:
            x_meters: Coordenada x en metros.
        """
        self._x_position = max(0.0, min(x_meters, self._beam_length))
        self._update_position()
        self._update_tooltip()

    def _update_position(self) -> None:
        """Actualiza la posición gráfica a partir de la coordenada del modelo."""
        self.setPos(self._x_position * self._scale_factor, 0)

    # ── Reacciones ──────────────────────────────────────────

    @property
    def reaction_values(self) -> dict[str, float]:
        """Diccionario con las reacciones calculadas."""
        return self._reaction_values

    @reaction_values.setter
    def reaction_values(self, values: dict[str, float]) -> None:
        """
        Establece las reacciones para mostrar.

        Args:
            values: Dict con claves como ``'Ry'``, ``'Rx'``, ``'M'``
                    y valores numéricos en las unidades correspondientes.
        """
        self._reaction_values = dict(values)
        self.update()

    def clear_reactions(self) -> None:
        """Limpia las reacciones mostradas."""
        self._reaction_values.clear()
        self.update()

    # ── Tooltip ─────────────────────────────────────────────

    def _update_tooltip(self) -> None:
        """Actualiza el tooltip con la información del apoyo."""
        tip = self._support_type_name()
        if self._label:
            tip += f" «{self._label}»"
        tip += f"\nPosición: {self._x_position:.2f} m"
        if self._reaction_values:
            tip += "\nReacciones:"
            for key, val in self._reaction_values.items():
                unit = "kN·m" if key == "M" else "kN"
                tip += f"\n  {key} = {val:+.2f} {unit}"
        self.setToolTip(tip)

    def _support_type_name(self) -> str:
        """Devuelve el nombre del tipo de apoyo (se sobreescribe)."""
        return "Apoyo"

    # ── Arrastre restringido ────────────────────────────────

    def itemChange(
        self,
        change: QGraphicsItem.GraphicsItemChange,
        value: object,
    ) -> object:
        """Restringe el movimiento al eje horizontal de la viga."""
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            new_pos: QPointF = value  # type: ignore[assignment]
            max_x = self._beam_length * self._scale_factor
            clamped_x = max(0.0, min(new_pos.x(), max_x))
            self._x_position = clamped_x / self._scale_factor
            self._update_tooltip()
            return QPointF(clamped_x, 0)
        return super().itemChange(change, value)

    # ── Eventos hover ───────────────────────────────────────

    def hoverEnterEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self._hovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self._hovered = False
        self.update()
        super().hoverLeaveEvent(event)

    # ── Menú contextual ─────────────────────────────────────

    def contextMenuEvent(self, event: QGraphicsSceneContextMenuEvent) -> None:
        """Muestra menú contextual con opciones del apoyo."""
        menu = QMenu()
        menu.addAction(QAction(f"Apoyo: {self._support_type_name()}", menu))
        menu.addSeparator()

        edit_action = QAction("Editar posición…", menu)
        menu.addAction(edit_action)

        delete_action = QAction("Eliminar apoyo", menu)
        menu.addAction(delete_action)

        menu.exec(event.screenPos())

    # ── Dibujo de achurado (shared) ─────────────────────────

    def _draw_hatch_ground(
        self,
        painter: QPainter,
        x_start: float,
        y_top: float,
        width: float,
        direction: int = 1,
    ) -> None:
        """
        Dibuja el achurado de tierra debajo del apoyo.

        Args:
            painter: QPainter activo.
            x_start: Coordenada x izquierda del achurado.
            y_top: Coordenada y superior de la línea de suelo.
            width: Ancho total del achurado.
            direction: 1 para achurado hacia abajo-derecha, -1 invertido.
        """
        hatch_color = self._current_color()
        hatch_pen = QPen(hatch_color, 1.0)
        hatch_pen.setCosmetic(True)
        painter.setPen(hatch_pen)

        # Línea de suelo
        painter.drawLine(QPointF(x_start, y_top), QPointF(x_start + width, y_top))

        # Líneas inclinadas
        x = x_start
        while x <= x_start + width + 0.5:
            painter.drawLine(
                QPointF(x, y_top),
                QPointF(x - self.HATCH_HEIGHT * 0.6 * direction, y_top + self.HATCH_HEIGHT),
            )
            x += self.HATCH_SPACING

    def _current_color(self) -> QColor:
        """Color del apoyo según estado (hover/selección/normal)."""
        base = theme_colors.support
        if self.isSelected():
            return QColor('#ffd700')
        if self._hovered:
            return QColor(base).lighter(130)
        return base

    # ── Dibujo de reacciones ────────────────────────────────

    def _draw_reaction_arrow(
        self,
        painter: QPainter,
        x: float,
        y_start: float,
        value: float,
        label_text: str,
        horizontal: bool = False,
    ) -> None:
        """
        Dibuja una flecha de reacción con etiqueta.

        Args:
            painter: QPainter activo.
            x: Coordenada x de la base de la flecha.
            y_start: Coordenada y de la base de la flecha.
            value: Magnitud de la reacción (signo indica dirección).
            label_text: Texto de la etiqueta.
            horizontal: Si es ``True``, la flecha se dibuja horizontal.
        """
        if abs(value) < 1e-10:
            return

        arrow_len = self.REACTION_ARROW_LENGTH
        head = self.REACTION_ARROW_HEAD
        r_color = theme_colors.get_color('accent_green')
        r_pen = QPen(r_color, 1.8)
        r_pen.setCosmetic(True)
        painter.setPen(r_pen)

        if horizontal:
            if value >= 0:
                # Apunta a la derecha, la ubicamos a la izquierda del apoyo
                x_end = x
                x_base = x - arrow_len
                painter.drawLine(QPointF(x_base, y_start), QPointF(x_end, y_start))
                painter.drawLine(QPointF(x_end, y_start), QPointF(x_end - head, y_start - head * 0.5))
                painter.drawLine(QPointF(x_end, y_start), QPointF(x_end - head, y_start + head * 0.5))
                font = QFont("Segoe UI", 8)
                painter.setFont(font)
                painter.drawText(QPointF(x_base - 30, y_start - 4), label_text)
            else:
                # Apunta a la izquierda, la ubicamos a la derecha del apoyo
                x_end = x
                x_base = x + arrow_len
                painter.drawLine(QPointF(x_base, y_start), QPointF(x_end, y_start))
                painter.drawLine(QPointF(x_end, y_start), QPointF(x_end + head, y_start - head * 0.5))
                painter.drawLine(QPointF(x_end, y_start), QPointF(x_end + head, y_start + head * 0.5))
                font = QFont("Segoe UI", 8)
                painter.setFont(font)
                painter.drawText(QPointF(x_base + 4, y_start - 4), label_text)
        else:
            # Vertical
            if value >= 0:
                # Apunta hacia arriba, base más abajo del apoyo
                y_end = y_start
                y_base = y_start + arrow_len
                painter.drawLine(QPointF(x, y_base), QPointF(x, y_end))
                painter.drawLine(QPointF(x, y_end), QPointF(x - head * 0.5, y_end + head))
                painter.drawLine(QPointF(x, y_end), QPointF(x + head * 0.5, y_end + head))
                font = QFont("Segoe UI", 8)
                painter.setFont(font)
                painter.drawText(QPointF(x + 6, y_base), label_text)
            else:
                # Apunta hacia abajo, sale del apoyo hacia abajo
                y_end = y_start + arrow_len
                y_base = y_start
                painter.drawLine(QPointF(x, y_base), QPointF(x, y_end))
                painter.drawLine(QPointF(x, y_end), QPointF(x - head * 0.5, y_end - head))
                painter.drawLine(QPointF(x, y_end), QPointF(x + head * 0.5, y_end - head))
                font = QFont("Segoe UI", 8)
                painter.setFont(font)
                painter.drawText(QPointF(x + 6, y_end + 14), label_text)

    def _draw_moment_reaction(
        self,
        painter: QPainter,
        x: float,
        y: float,
        value: float,
        label_text: str,
    ) -> None:
        """
        Dibuja un arco de reacción de momento.

        Args:
            painter: QPainter activo.
            x: Centro x del arco.
            y: Centro y del arco.
            value: Magnitud del momento.
            label_text: Etiqueta del momento.
        """
        if abs(value) < 1e-10:
            return

        m_color = theme_colors.moment
        m_pen = QPen(m_color, 1.8)
        m_pen.setCosmetic(True)
        painter.setPen(m_pen)

        radius = 20.0
        rect = QRectF(x - radius, y - radius, radius * 2, radius * 2)

        # Ángulo del arco (positivo = anti-horario)
        start_angle = 0
        span_angle = 270 if value >= 0 else -270

        painter.drawArc(rect, start_angle * 16, span_angle * 16)

        # Cabeza de flecha al final del arco
        head = self.REACTION_ARROW_HEAD
        import math
        end_rad = math.radians((start_angle + span_angle / 16.0))
        # Simplificación: ponemos la flecha en posición fija para legibilidad
        if value >= 0:
            ax, ay = x, y - radius
            painter.drawLine(QPointF(ax, ay), QPointF(ax - head * 0.5, ay + head))
            painter.drawLine(QPointF(ax, ay), QPointF(ax + head * 0.5, ay + head))
        else:
            ax, ay = x, y - radius
            painter.drawLine(QPointF(ax, ay), QPointF(ax - head * 0.5, ay - head))
            painter.drawLine(QPointF(ax, ay), QPointF(ax + head * 0.5, ay - head))

        font = QFont("Segoe UI", 8)
        painter.setFont(font)
        painter.drawText(QPointF(x + radius + 4, y), label_text)

    def refresh_colors(self) -> None:
        """Refresca los colores tras un cambio de tema."""
        self.update()


# ════════════════════════════════════════════════════════════
#  Apoyo articulado (Pinned)
# ════════════════════════════════════════════════════════════

class PinnedSupportItem(_BaseSupportItem):
    """
    Apoyo articulado — triángulo con achurado de tierra.

    Permite reacciones horizontales (Rx) y verticales (Ry),
    pero no momento.
    """

    def _support_type_name(self) -> str:
        return "Articulado"

    def boundingRect(self) -> QRectF:
        margin = 10.0
        half_b = self.TRIANGLE_HALF_BASE + margin
        top = -self.REACTION_ARROW_LENGTH - margin - 20
        bottom = self.TRIANGLE_HEIGHT + self.HATCH_HEIGHT + margin
        return QRectF(-half_b - self.REACTION_ARROW_LENGTH, top,
                      half_b * 2 + self.REACTION_ARROW_LENGTH * 2,
                      bottom - top)

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        path.addRect(self.boundingRect())
        return path

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: Optional[QWidget] = None,
    ) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        color = self._current_color()
        pen = QPen(color, 2.0)
        pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        hb = self.TRIANGLE_HALF_BASE
        h = self.TRIANGLE_HEIGHT

        # Triángulo
        triangle = QPolygonF([
            QPointF(0, 0),
            QPointF(-hb, h),
            QPointF(hb, h),
        ])
        painter.drawPolygon(triangle)

        # Achurado de tierra
        self._draw_hatch_ground(painter, -hb, h, hb * 2)

        # Etiqueta del apoyo
        if self._label:
            font = QFont("Segoe UI", 9, QFont.Weight.Bold)
            painter.setFont(font)
            painter.setPen(QPen(theme_colors.text))
            fm = QFontMetricsF(font)
            tw = fm.horizontalAdvance(self._label)
            painter.drawText(
                QPointF(-tw / 2, h + self.HATCH_HEIGHT + fm.height() + 2),
                self._label,
            )

        # Reacciones
        if self._reaction_values:
            ry = self._reaction_values.get("Ry", 0.0)
            rx = self._reaction_values.get("Rx", 0.0)
            if abs(ry) > 1e-10:
                lbl = f"R{self._label}y = {ry:+.2f} kN" if self._label else f"Ry = {ry:+.2f} kN"
                self._draw_reaction_arrow(painter, 0, h + self.HATCH_HEIGHT + 4, ry, lbl, horizontal=False)
            if abs(rx) > 1e-10:
                lbl = f"R{self._label}x = {rx:+.2f} kN" if self._label else f"Rx = {rx:+.2f} kN"
                self._draw_reaction_arrow(painter, 0, h / 2, rx, lbl, horizontal=True)


# ════════════════════════════════════════════════════════════
#  Apoyo de rodillo (Roller)
# ════════════════════════════════════════════════════════════

class RollerSupportItem(_BaseSupportItem):
    """
    Apoyo de rodillo — triángulo con círculos debajo.

    Solo permite reacción vertical (Ry).
    """

    WHEEL_RADIUS: float = 4.0
    WHEEL_SPACING: float = 12.0

    def _support_type_name(self) -> str:
        return "Rodillo"

    def boundingRect(self) -> QRectF:
        margin = 10.0
        hb = self.TRIANGLE_HALF_BASE + margin
        top = -self.REACTION_ARROW_LENGTH - margin - 20
        wheel_bottom = self.TRIANGLE_HEIGHT + self.WHEEL_RADIUS * 2 + self.HATCH_HEIGHT
        return QRectF(-hb, top, hb * 2, wheel_bottom - top + margin + 30)

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        path.addRect(self.boundingRect())
        return path

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: Optional[QWidget] = None,
    ) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        color = self._current_color()
        pen = QPen(color, 2.0)
        pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        hb = self.TRIANGLE_HALF_BASE
        h = self.TRIANGLE_HEIGHT
        wr = self.WHEEL_RADIUS

        # Triángulo
        triangle = QPolygonF([
            QPointF(0, 0),
            QPointF(-hb, h),
            QPointF(hb, h),
        ])
        painter.drawPolygon(triangle)

        # Ruedas (círculos)
        wheel_y = h + wr
        positions = [-self.WHEEL_SPACING / 2, 0, self.WHEEL_SPACING / 2]
        for wx in positions:
            painter.drawEllipse(QPointF(wx, wheel_y), wr, wr)

        # Línea de suelo debajo de las ruedas + achurado
        ground_y = wheel_y + wr
        self._draw_hatch_ground(painter, -hb, ground_y, hb * 2)

        # Etiqueta
        if self._label:
            font = QFont("Segoe UI", 9, QFont.Weight.Bold)
            painter.setFont(font)
            painter.setPen(QPen(theme_colors.text))
            fm = QFontMetricsF(font)
            tw = fm.horizontalAdvance(self._label)
            painter.drawText(
                QPointF(-tw / 2, ground_y + self.HATCH_HEIGHT + fm.height() + 2),
                self._label,
            )

        # Reacciones (solo vertical)
        if self._reaction_values:
            ry = self._reaction_values.get("Ry", 0.0)
            if abs(ry) > 1e-10:
                lbl = f"R{self._label}y = {ry:+.2f} kN" if self._label else f"Ry = {ry:+.2f} kN"
                self._draw_reaction_arrow(painter, 0, ground_y + self.HATCH_HEIGHT + 4, ry, lbl, horizontal=False)


# ════════════════════════════════════════════════════════════
#  Empotramiento (Fixed)
# ════════════════════════════════════════════════════════════

class FixedSupportItem(_BaseSupportItem):
    """
    Empotramiento — rectángulo vertical con achurado lateral.

    Permite reacciones horizontales (Rx), verticales (Ry), y momento (M).
    """

    WALL_WIDTH: float = 8.0
    WALL_HALF_HEIGHT: float = 30.0
    HATCH_WALL_DEPTH: float = 14.0

    def __init__(
        self,
        x_position: float = 0.0,
        scale_factor: float = 100.0,
        label: str = "",
        side: str = "left",
        parent: QGraphicsItem | None = None,
    ) -> None:
        """
        Args:
            side: ``'left'`` o ``'right'`` — de qué lado está la pared.
        """
        self._side: str = side
        super().__init__(x_position, scale_factor, label, parent)

    def _support_type_name(self) -> str:
        return "Empotramiento"

    def boundingRect(self) -> QRectF:
        margin = 10.0
        wh = self.WALL_HALF_HEIGHT + margin
        ext = self.HATCH_WALL_DEPTH + self.WALL_WIDTH + self.REACTION_ARROW_LENGTH + margin
        return QRectF(-ext, -wh - self.REACTION_ARROW_LENGTH,
                      ext * 2, (wh + self.REACTION_ARROW_LENGTH) * 2 + 40)

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        path.addRect(self.boundingRect())
        return path

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: Optional[QWidget] = None,
    ) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        color = self._current_color()
        pen = QPen(color, 2.0)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        wh = self.WALL_HALF_HEIGHT
        ww = self.WALL_WIDTH
        hd = self.HATCH_WALL_DEPTH

        left = self._side == "left"

        if left:
            # Pared a la izquierda
            wall_x = -ww
            painter.drawRect(QRectF(wall_x, -wh, ww, wh * 2))
            # Achurado hacia la izquierda
            hatch_pen = QPen(color, 1.0)
            hatch_pen.setCosmetic(True)
            painter.setPen(hatch_pen)
            y = -wh
            while y <= wh:
                painter.drawLine(
                    QPointF(wall_x, y),
                    QPointF(wall_x - hd, y + hd * 0.7),
                )
                y += self.HATCH_SPACING
        else:
            # Pared a la derecha
            wall_x = 0.0
            painter.drawRect(QRectF(wall_x, -wh, ww, wh * 2))
            hatch_pen = QPen(color, 1.0)
            hatch_pen.setCosmetic(True)
            painter.setPen(hatch_pen)
            y = -wh
            while y <= wh:
                painter.drawLine(
                    QPointF(wall_x + ww, y),
                    QPointF(wall_x + ww + hd, y + hd * 0.7),
                )
                y += self.HATCH_SPACING

        # Etiqueta
        if self._label:
            font = QFont("Segoe UI", 9, QFont.Weight.Bold)
            painter.setFont(font)
            painter.setPen(QPen(theme_colors.text))
            fm = QFontMetricsF(font)
            tw = fm.horizontalAdvance(self._label)
            lx = (-ww - hd - tw) / 2 if left else (ww + hd - tw) / 2 + ww
            painter.drawText(QPointF(lx, wh + fm.height() + 4), self._label)

        # Reacciones
        if self._reaction_values:
            ry = self._reaction_values.get("Ry", 0.0)
            rx = self._reaction_values.get("Rx", 0.0)
            m_val = self._reaction_values.get("M", 0.0)

            base_y = wh + 6
            if abs(ry) > 1e-10:
                lbl = f"R{self._label}y = {ry:+.2f} kN" if self._label else f"Ry = {ry:+.2f} kN"
                self._draw_reaction_arrow(painter, 0, base_y, ry, lbl, horizontal=False)
            if abs(rx) > 1e-10:
                lbl = f"R{self._label}x = {rx:+.2f} kN" if self._label else f"Rx = {rx:+.2f} kN"
                offset_x = (-ww - 10) if left else (ww + 10)
                self._draw_reaction_arrow(painter, offset_x, 0, rx, lbl, horizontal=True)
            if abs(m_val) > 1e-10:
                lbl = f"M{self._label} = {m_val:+.2f} kN·m" if self._label else f"M = {m_val:+.2f} kN·m"
                self._draw_moment_reaction(painter, 0, -wh - 10, m_val, lbl)
