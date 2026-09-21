"""
load_renderer.py - QGraphicsItems para renderizar cargas aplicadas.
"""

from PyQt6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QPainterPath, QFont
from PyQt6.QtCore import QRectF, Qt, QPointF
import math

from app.render.colors import ThemeColors

class BaseLoadItem(QGraphicsItem):
    def __init__(self, color_name="load_color"):
        super().__init__()
        self.theme = ThemeColors()
        self.color = QColor(self.theme.get_color(color_name))
        
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, False)
        self.setAcceptHoverEvents(True)
        self.is_hovered = False
        self.setZValue(2)
        
    def shape(self) -> QPainterPath:
        path = QPainterPath()
        path.addRect(self.boundingRect())
        return path
        
    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.scene():
            # Restringir movimiento al eje X sobre la viga
            new_pos = value
            return QPointF(new_pos.x(), 0)
        return super().itemChange(change, value)
        
    def hoverEnterEvent(self, event):
        self.is_hovered = True
        self.update()
        
    def hoverLeaveEvent(self, event):
        self.is_hovered = False
        self.update()

class PointLoadItem(BaseLoadItem):
    def __init__(self, magnitude: float = 10.0):
        super().__init__("load_color")
        self.magnitude = magnitude
        self.arrow_len = min(max(30, abs(magnitude) * 2), 100) # scale visually
        self.arrow_width = 4
        self.head_len = 12
        self.head_width = 8
        self.is_down = magnitude >= 0
        
    def boundingRect(self) -> QRectF:
        if self.is_down:
            return QRectF(-self.head_width - 10, -self.arrow_len - 30, 2 * self.head_width + 20, self.arrow_len + 35)
        else:
            return QRectF(-self.head_width - 10, -5, 2 * self.head_width + 20, self.arrow_len + 35)
            
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget):
        pen = QPen(self.color, self.arrow_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        if self.isSelected():
            pen.setColor(QColor(self.theme.get_color("accent_blue")))
        elif self.is_hovered:
            pen.setColor(self.color.lighter(130))
            
        painter.setPen(pen)
        painter.setBrush(pen.color())
        
        # Arrow line
        y_start = -self.arrow_len if self.is_down else self.arrow_len
        y_end = 0
        painter.drawLine(QPointF(0, y_start), QPointF(0, y_end))
        
        # Arrow head
        path = QPainterPath()
        path.moveTo(0, y_end)
        if self.is_down:
            path.lineTo(-self.head_width, y_end - self.head_len)
            path.lineTo(self.head_width, y_end - self.head_len)
        else:
            path.lineTo(-self.head_width, y_end + self.head_len)
            path.lineTo(self.head_width, y_end + self.head_len)
        path.closeSubpath()
        painter.drawPath(path)
        
        # Label
        painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        text = f"{abs(self.magnitude):.1f} kN"
        rect = QRectF(-30, -self.arrow_len - 25 if self.is_down else self.arrow_len + 5, 60, 20)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)


class DistributedLoadItem(BaseLoadItem):
    def __init__(self, width: float, intensity: float, scale_factor: float):
        super().__init__("distributed_color")
        self.width = width
        self.intensity = intensity
        self.height = min(max(20, abs(intensity) * 3), 60)
        self.is_down = intensity >= 0
        
    def boundingRect(self) -> QRectF:
        if self.is_down:
            return QRectF(0, -self.height - 25, self.width, self.height + 30)
        else:
            return QRectF(0, -5, self.width, self.height + 30)
            
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget):
        pen = QPen(self.color, 2)
        if self.isSelected():
            pen.setColor(QColor(self.theme.get_color("accent_blue")))
        elif self.is_hovered:
            pen.setColor(self.color.lighter(130))
            
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor(pen.color().red(), pen.color().green(), pen.color().blue(), 80)))
        
        y_top = -self.height if self.is_down else self.height
        y_bot = 0
        
        # Body
        painter.drawRect(QRectF(0, y_top if self.is_down else 0, self.width, self.height))
        
        # Arrows
        num_arrows = max(3, int(self.width / 20))
        spacing = self.width / (num_arrows - 1) if num_arrows > 1 else self.width
        painter.setBrush(pen.color())
        
        for i in range(num_arrows):
            x = i * spacing
            painter.drawLine(QPointF(x, y_top), QPointF(x, y_bot))
            # Head
            path = QPainterPath()
            path.moveTo(x, y_bot)
            if self.is_down:
                path.lineTo(x - 4, y_bot - 6)
                path.lineTo(x + 4, y_bot - 6)
            else:
                path.lineTo(x - 4, y_bot + 6)
                path.lineTo(x + 4, y_bot + 6)
            path.closeSubpath()
            painter.drawPath(path)
            
        # Label
        painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        text = f"{abs(self.intensity):.1f} kN/m"
        rect = QRectF(self.width/2 - 40, y_top - 20 if self.is_down else y_top + 5, 80, 20)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

# For simplicity, we create wrapper classes that inherit from DistributedLoadItem 
# for triangular/trapezoidal, as they are visually similar or we can override paint.
class TriangularLoadItem(DistributedLoadItem):
    def __init__(self, width: float, w_start: float, w_end: float, scale_factor: float):
        super().__init__(width, max(w_start, w_end), scale_factor)
        self.w_start = w_start
        self.w_end = w_end
        
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget):
        pen = QPen(self.color, 2)
        if self.isSelected():
            pen.setColor(QColor(self.theme.get_color("accent_blue")))
        painter.setPen(pen)
        
        h_start = min(max(0, abs(self.w_start) * 3), 60)
        h_end = min(max(0, abs(self.w_end) * 3), 60)
        
        y_dir = -1 if self.is_down else 1
        
        # Shape
        path = QPainterPath()
        path.moveTo(0, 0)
        path.lineTo(0, h_start * y_dir)
        path.lineTo(self.width, h_end * y_dir)
        path.lineTo(self.width, 0)
        path.closeSubpath()
        
        painter.setBrush(QBrush(QColor(pen.color().red(), pen.color().green(), pen.color().blue(), 80)))
        painter.drawPath(path)
        
        # Label
        painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        text = f"W1: {self.w_start:.1f} W2: {self.w_end:.1f}"
        rect = QRectF(self.width/2 - 50, -max(h_start, h_end) - 20 if self.is_down else max(h_start, h_end) + 5, 100, 20)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)


class TrapezoidalLoadItem(TriangularLoadItem):
    pass


class MomentLoadItem(BaseLoadItem):
    def __init__(self, magnitude: float = 20.0):
        super().__init__("moment_color")
        self.magnitude = magnitude
        self.radius = 20
        self.is_ccw = magnitude > 0
        
    def boundingRect(self) -> QRectF:
        return QRectF(-self.radius - 15, -self.radius - 25, 2 * self.radius + 30, 2 * self.radius + 40)
        
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget):
        pen = QPen(self.color, 3)
        if self.isSelected():
            pen.setColor(QColor(self.theme.get_color("accent_blue")))
        painter.setPen(pen)
        
        rect = QRectF(-self.radius, -self.radius, 2*self.radius, 2*self.radius)
        # Draw arc
        # startAngle and spanAngle are in 1/16ths of a degree
        start = 30 * 16
        span = 240 * 16
        painter.drawArc(rect, start, span)
        
        # Draw arrow head
        path = QPainterPath()
        if self.is_ccw:
            # point on circle around 270 degrees
            x = self.radius * math.cos(math.radians(270))
            y = -self.radius * math.sin(math.radians(270))
            path.moveTo(x, y)
            path.lineTo(x + 8, y + 8)
            path.lineTo(x - 2, y + 10)
        else:
            x = self.radius * math.cos(math.radians(30))
            y = -self.radius * math.sin(math.radians(30))
            path.moveTo(x, y)
            path.lineTo(x - 8, y - 8)
            path.lineTo(x + 2, y - 10)
        
        painter.setBrush(pen.color())
        painter.drawPath(path)
        
        painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        text = f"{abs(self.magnitude):.1f} kN·m"
        painter.drawText(QRectF(-30, -self.radius - 20, 60, 20), Qt.AlignmentFlag.AlignCenter, text)

class InclinedLoadItem(PointLoadItem):
    def __init__(self, magnitude: float = 10.0, angle: float = 45.0):
        super().__init__(magnitude)
        self.angle = angle
        
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget):
        pen = QPen(self.color, self.arrow_width, Qt.PenStyle.SolidLine)
        if self.isSelected():
            pen.setColor(QColor(self.theme.get_color("accent_blue")))
        painter.setPen(pen)
        
        painter.save()
        # Rotate painter
        painter.rotate(-self.angle + 90) # adjust so 90 is vertical
        super().paint(painter, option, widget)
        painter.restore()
