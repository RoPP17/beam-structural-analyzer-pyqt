"""
dimension_renderer.py - Elementos de la cuadrícula y cotas.
"""

from PyQt6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem
from PyQt6.QtGui import QPainter, QPen, QColor, QFont
from PyQt6.QtCore import QRectF, Qt, QPointF

class GridOverlay(QGraphicsItem):
    def __init__(self, width: float, height: float, spacing: float, color: QColor):
        super().__init__()
        self.width = width
        self.height = height
        self.spacing = spacing
        self.color = color
        self.setZValue(-10)
        
    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.width, self.height)
        
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget):
        pen = QPen(self.color, 1, Qt.PenStyle.DotLine)
        painter.setPen(pen)
        
        # Vertical lines
        x = 0.0
        while x <= self.width:
            painter.drawLine(QPointF(x, 0), QPointF(x, self.height))
            x += self.spacing
            
        # Horizontal lines
        y = 0.0
        while y <= self.height:
            painter.drawLine(QPointF(0, y), QPointF(self.width, y))
            y += self.spacing

class CoordinateLabel(QGraphicsItem):
    def __init__(self, text: str):
        super().__init__()
        self.text = text
        self.setZValue(10)
        
    def boundingRect(self) -> QRectF:
        return QRectF(-20, 0, 40, 20)
        
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget):
        painter.setFont(QFont("Arial", 8))
        painter.setPen(QColor(150, 150, 150))
        painter.drawText(self.boundingRect(), Qt.AlignmentFlag.AlignCenter, self.text)
