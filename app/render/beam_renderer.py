"""
Renderizado gráfico de la viga principal.

Proporciona ``BeamGraphicsItem``, un ``QGraphicsItem`` que dibuja
la viga horizontal con gradiente, marcas de cota, efectos hover
y resaltado de selección.
"""

from __future__ import annotations

import math
from typing import Optional

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetricsF,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PyQt6.QtWidgets import (
    QGraphicsItem,
    QGraphicsSceneHoverEvent,
    QStyleOptionGraphicsItem,
    QWidget,
)

from app.render.colors import theme_colors


class BeamGraphicsItem(QGraphicsItem):
    """
    Elemento gráfico que representa la viga principal.

    Dibuja una línea horizontal gruesa con gradiente, terminaciones
    redondeadas, marcas de escala, línea de cota con longitud, y
    un indicador del sistema de coordenadas en el origen.

    Attributes:
        length: Longitud de la viga en unidades del modelo (metros).
        scale_factor: Factor px/m para convertir coordenadas de modelo a píxeles.
        color: Color base de la viga (por defecto el del tema).
    """

    # ── Constantes de dibujo ────────────────────────────────
    BEAM_THICKNESS: float = 8.0
    HOVER_GLOW_RADIUS: float = 6.0
    SELECTION_BORDER_WIDTH: float = 2.5
    TICK_LENGTH: float = 6.0
    DIMENSION_OFFSET: float = 35.0
    DIMENSION_ARROW_SIZE: float = 6.0
    AXIS_LENGTH: float = 40.0
    AXIS_ARROW_SIZE: float = 8.0
    AXIS_OFFSET_Y: float = -50.0

    def __init__(
        self,
        length: float = 6.0,
        scale_factor: float = 100.0,
        color: QColor | None = None,
        parent: QGraphicsItem | None = None,
    ) -> None:
        super().__init__(parent)

        self._length: float = length
        self._scale_factor: float = scale_factor
        self._color: QColor = color or theme_colors.beam

        self._hovered: bool = False

        # Flags de interacción
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setZValue(0)

        self.setToolTip(f"Viga — Longitud: {self._length:.2f} m")

    # ── Propiedades ─────────────────────────────────────────

    @property
    def length(self) -> float:
        """Longitud de la viga en metros."""
        return self._length

    @length.setter
    def length(self, value: float) -> None:
        self.prepareGeometryChange()
        self._length = max(0.1, value)
        self.setToolTip(f"Viga — Longitud: {self._length:.2f} m")
        self.update()

    @property
    def scale_factor(self) -> float:
        """Factor de escala px/m."""
        return self._scale_factor

    @scale_factor.setter
    def scale_factor(self, value: float) -> None:
        self.prepareGeometryChange()
        self._scale_factor = max(1.0, value)
        self.update()

    @property
    def color(self) -> QColor:
        """Color base de la viga."""
        return self._color

    @color.setter
    def color(self, value: QColor) -> None:
        self._color = value
        self.update()

    @property
    def pixel_length(self) -> float:
        """Longitud de la viga en píxeles."""
        return self._length * self._scale_factor

    # ── Geometría del ítem ──────────────────────────────────

    def boundingRect(self) -> QRectF:
        """Rectángulo envolvente que incluye todos los sub-elementos."""
        margin = 20.0
        px_len = self.pixel_length
        top = self.AXIS_OFFSET_Y - self.AXIS_LENGTH - margin
        bottom = self.DIMENSION_OFFSET + 30.0
        return QRectF(
            -self.AXIS_LENGTH - margin,
            top,
            px_len + self.AXIS_LENGTH + 2 * margin,
            bottom - top + margin,
        )

    def shape(self) -> QPainterPath:
        """Forma precisa para detección de clics y colisiones."""
        path = QPainterPath()
        half = self.BEAM_THICKNESS / 2.0 + 4.0
        path.addRect(QRectF(-4.0, -half, self.pixel_length + 8.0, half * 2.0))
        return path

    # ── Pintura ─────────────────────────────────────────────

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: Optional[QWidget] = None,
    ) -> None:
        """Dibuja la viga y todos sus elementos decorativos."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        px_len = self.pixel_length
        half_t = self.BEAM_THICKNESS / 2.0

        # ── 1. Efecto glow al pasar el ratón ───────────────
        if self._hovered:
            glow_color = QColor(self._color)
            glow_color.setAlpha(50)
            glow_pen = QPen(glow_color, self.BEAM_THICKNESS + self.HOVER_GLOW_RADIUS * 2)
            glow_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(glow_pen)
            painter.drawLine(QPointF(0, 0), QPointF(px_len, 0))

        # ── 2. Resaltado de selección ───────────────────────
        if self.isSelected():
            sel_color = QColor('#ffd700')
            sel_pen = QPen(sel_color, self.BEAM_THICKNESS + self.SELECTION_BORDER_WIDTH * 2)
            sel_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(sel_pen)
            painter.drawLine(QPointF(0, 0), QPointF(px_len, 0))

        # ── 3. Gradiente de la viga ─────────────────────────
        gradient = QLinearGradient(0, -half_t, 0, half_t)
        lighter = QColor(self._color)
        lighter.setAlpha(255)
        lighter_val = lighter.lighter(130)
        darker_val = QColor(self._color).darker(120)
        gradient.setColorAt(0.0, lighter_val)
        gradient.setColorAt(0.5, self._color)
        gradient.setColorAt(1.0, darker_val)

        beam_pen = QPen(QBrush(gradient), self.BEAM_THICKNESS)
        beam_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(beam_pen)
        painter.drawLine(QPointF(0, 0), QPointF(px_len, 0))

        # ── 4. Marcas de escala (ticks) ─────────────────────
        self._draw_tick_marks(painter, px_len)

        # ── 5. Línea de cota ────────────────────────────────
        self._draw_dimension_line(painter, px_len)

        # ── 6. Ejes de coordenadas ──────────────────────────
        self._draw_coordinate_axes(painter)

    # ── Sub-dibujos privados ────────────────────────────────

    def _draw_tick_marks(self, painter: QPainter, px_len: float) -> None:
        """Dibuja marcas de escala a intervalos regulares sobre la viga."""
        tick_pen = QPen(theme_colors.dimension, 1.0)
        tick_pen.setCosmetic(True)
        painter.setPen(tick_pen)

        interval_m = self._compute_tick_interval()
        half_t = self.BEAM_THICKNESS / 2.0

        pos_m = 0.0
        while pos_m <= self._length + 1e-9:
            x = pos_m * self._scale_factor
            if x > px_len + 0.5:
                break
            painter.drawLine(
                QPointF(x, half_t),
                QPointF(x, half_t + self.TICK_LENGTH),
            )
            pos_m += interval_m

    def _compute_tick_interval(self) -> float:
        """Calcula el intervalo de ticks basándose en la longitud de la viga."""
        if self._length <= 1.0:
            return 0.1
        if self._length <= 3.0:
            return 0.5
        if self._length <= 10.0:
            return 1.0
        if self._length <= 30.0:
            return 2.0
        return 5.0

    def _draw_dimension_line(self, painter: QPainter, px_len: float) -> None:
        """Dibuja la línea de cota con flechas y etiqueta de longitud."""
        dim_color = theme_colors.dimension
        dim_pen = QPen(dim_color, 1.0)
        dim_pen.setCosmetic(True)
        painter.setPen(dim_pen)

        y = self.DIMENSION_OFFSET
        arrow = self.DIMENSION_ARROW_SIZE

        # Líneas de extensión vertical
        ext_top = self.BEAM_THICKNESS / 2.0 + self.TICK_LENGTH
        painter.drawLine(QPointF(0, ext_top), QPointF(0, y + 4))
        painter.drawLine(QPointF(px_len, ext_top), QPointF(px_len, y + 4))

        # Línea horizontal de cota
        painter.drawLine(QPointF(0, y), QPointF(px_len, y))

        # Flecha izquierda
        painter.drawLine(QPointF(0, y), QPointF(arrow, y - arrow * 0.5))
        painter.drawLine(QPointF(0, y), QPointF(arrow, y + arrow * 0.5))

        # Flecha derecha
        painter.drawLine(QPointF(px_len, y), QPointF(px_len - arrow, y - arrow * 0.5))
        painter.drawLine(QPointF(px_len, y), QPointF(px_len - arrow, y + arrow * 0.5))

        # Etiqueta de longitud
        label = f"{self._length:.2f} m"
        font = QFont("Segoe UI", 9)
        painter.setFont(font)
        painter.setPen(QPen(dim_color))
        fm = QFontMetricsF(font)
        text_w = fm.horizontalAdvance(label)
        text_h = fm.height()
        text_x = (px_len - text_w) / 2.0
        text_y = y + text_h + 2.0
        painter.drawText(QPointF(text_x, text_y), label)

    def _draw_coordinate_axes(self, painter: QPainter) -> None:
        """Dibuja el marcador de ejes de coordenadas (+x, +y) en el origen."""
        ax_len = self.AXIS_LENGTH
        arr = self.AXIS_ARROW_SIZE
        origin_y = self.AXIS_OFFSET_Y

        # Eje +X (hacia la derecha)
        x_color = theme_colors.get_color('accent_red')
        x_pen = QPen(x_color, 1.5)
        x_pen.setCosmetic(True)
        painter.setPen(x_pen)
        painter.drawLine(QPointF(0, origin_y), QPointF(ax_len, origin_y))
        painter.drawLine(QPointF(ax_len, origin_y), QPointF(ax_len - arr, origin_y - arr * 0.4))
        painter.drawLine(QPointF(ax_len, origin_y), QPointF(ax_len - arr, origin_y + arr * 0.4))

        font = QFont("Segoe UI", 8)
        painter.setFont(font)
        painter.drawText(QPointF(ax_len + 3, origin_y + 4), "+x")

        # Eje +Y (hacia arriba, siguiendo la convención positiva arriba)
        y_color = theme_colors.get_color('accent_green')
        y_pen = QPen(y_color, 1.5)
        y_pen.setCosmetic(True)
        painter.setPen(y_pen)
        painter.drawLine(QPointF(0, origin_y), QPointF(0, origin_y - ax_len))
        painter.drawLine(
            QPointF(0, origin_y - ax_len),
            QPointF(-arr * 0.4, origin_y - ax_len + arr),
        )
        painter.drawLine(
            QPointF(0, origin_y - ax_len),
            QPointF(arr * 0.4, origin_y - ax_len + arr),
        )
        painter.drawText(QPointF(5, origin_y - ax_len + 4), "+y")

    # ── Eventos hover ───────────────────────────────────────

    def hoverEnterEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        """Activa el efecto glow al entrar el cursor."""
        self._hovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        """Desactiva el efecto glow al salir el cursor."""
        self._hovered = False
        self.update()
        super().hoverLeaveEvent(event)

    # ── Utilidades ──────────────────────────────────────────

    def model_to_pixel(self, x_meters: float) -> float:
        """Convierte una coordenada x del modelo (metros) a píxeles locales."""
        return x_meters * self._scale_factor

    def pixel_to_model(self, x_pixels: float) -> float:
        """Convierte una coordenada x en píxeles locales a metros."""
        return x_pixels / self._scale_factor

    def refresh_colors(self) -> None:
        """Refresca los colores tras un cambio de tema."""
        self._color = theme_colors.beam
        self.update()

    def __repr__(self) -> str:
        return (
            f"BeamGraphicsItem(length={self._length:.2f}m, "
            f"scale={self._scale_factor:.0f}px/m)"
        )
