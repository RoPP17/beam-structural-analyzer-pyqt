"""
Diálogo "Acerca de" para BeamAnalyzer.

Muestra información sobre la aplicación, créditos universitarios
y versión, con estilo visual profesional.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap, QPainter, QColor, QPen
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class AboutDialog(QDialog):
    """Ventana 'Acerca de' con información de la aplicación y créditos."""

    _APP_NAME = "BeamAnalyzer"
    _VERSION = "1.0.0"
    _DESCRIPTION = "Aplicación profesional para análisis estructural de vigas"
    _UNIVERSITY = "Universidad Técnica de Ambato"
    _FACULTY = "Facultad de Ingeniería Civil y Mecánica"
    _COURSE = "Resistencia de Materiales"

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Crea el diálogo 'Acerca de'.

        Parameters
        ----------
        parent : QWidget | None
            Widget padre.
        """
        super().__init__(parent)
        self.setWindowTitle(f"Acerca de {self._APP_NAME}")
        self.setFixedSize(520, 480)
        self.setModal(True)

        self._build_ui()

    # ── Construcción de UI ────────────────────────────────────────────

    def _build_ui(self) -> None:
        """Construye la interfaz del diálogo."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(32, 24, 32, 24)

        # Logo placeholder
        logo = self._create_logo_placeholder()
        main_layout.addWidget(logo, alignment=Qt.AlignmentFlag.AlignCenter)

        # Nombre de la aplicación
        name_label = QLabel(self._APP_NAME)
        name_font = QFont()
        name_font.setPointSize(22)
        name_font.setBold(True)
        name_label.setFont(name_font)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet("color: #58a6ff;")
        main_layout.addWidget(name_label)

        # Versión
        version_label = QLabel(f"Versión {self._VERSION}")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("color: #8b949e; font-size: 13px;")
        main_layout.addWidget(version_label)

        # Descripción
        desc_label = QLabel(self._DESCRIPTION)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("font-size: 12px; margin-top: 4px;")
        main_layout.addWidget(desc_label)

        # Separador visual
        separator = QLabel()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #30363d; margin: 8px 0;")
        main_layout.addWidget(separator)

        # Información universitaria
        uni_info = QLabel(
            f"<div style='text-align: center; line-height: 1.6;'>"
            f"<span style='font-size: 13px; font-weight: bold; "
            f"color: #f0883e;'>{self._UNIVERSITY}</span><br>"
            f"<span style='font-size: 12px; color: #c9d1d9;'>"
            f"{self._FACULTY}</span><br>"
            f"<span style='font-size: 11px; color: #8b949e;'>"
            f"{self._COURSE}</span>"
            f"</div>"
        )
        uni_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        uni_info.setTextFormat(Qt.TextFormat.RichText)
        main_layout.addWidget(uni_info)

        # Separador
        sep2 = QLabel()
        sep2.setFixedHeight(1)
        sep2.setStyleSheet("background-color: #30363d; margin: 8px 0;")
        main_layout.addWidget(sep2)

        # Créditos
        credits_label = QLabel(
            "<div style='text-align: center; line-height: 1.5;'>"
            "<span style='font-size: 11px; font-weight: bold; "
            "color: #c9d1d9;'>Créditos</span><br>"
            "<span style='font-size: 11px; color: #8b949e;'>"
            "Desarrollado con Python, PyQt6, SymPy y Matplotlib<br>"
            "Motor de análisis basado en ecuaciones de equilibrio estático<br>"
            "y métodos de integración simbólica</span>"
            "</div>"
        )
        credits_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        credits_label.setTextFormat(Qt.TextFormat.RichText)
        main_layout.addWidget(credits_label)

        main_layout.addStretch()

        # Botón cerrar
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.button(QDialogButtonBox.StandardButton.Close).setText("Cerrar")
        button_box.rejected.connect(self.close)
        main_layout.addWidget(button_box)

    # ── Logo placeholder ──────────────────────────────────────────────

    @staticmethod
    def _create_logo_placeholder() -> QLabel:
        """
        Crea un QLabel con un icono placeholder de viga estilizado.

        Returns
        -------
        QLabel
            Label con el pixmap del logo.
        """
        size = 80
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Círculo de fondo
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#1f3a5f"))
        painter.drawEllipse(4, 4, size - 8, size - 8)

        # Borde del círculo
        pen = QPen(QColor("#58a6ff"), 2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(4, 4, size - 8, size - 8)

        # Dibujar una viga simplificada
        beam_pen = QPen(QColor("#58a6ff"), 3)
        painter.setPen(beam_pen)

        # Línea horizontal (viga)
        y_beam = size * 0.45
        x_start = size * 0.18
        x_end = size * 0.82
        painter.drawLine(int(x_start), int(y_beam), int(x_end), int(y_beam))

        # Triángulo apoyo izquierdo
        support_pen = QPen(QColor("#f0883e"), 2)
        painter.setPen(support_pen)
        tri_h = 12
        painter.drawLine(int(x_start), int(y_beam), int(x_start - 6), int(y_beam + tri_h))
        painter.drawLine(int(x_start), int(y_beam), int(x_start + 6), int(y_beam + tri_h))
        painter.drawLine(int(x_start - 6), int(y_beam + tri_h), int(x_start + 6), int(y_beam + tri_h))

        # Triángulo apoyo derecho
        painter.drawLine(int(x_end), int(y_beam), int(x_end - 6), int(y_beam + tri_h))
        painter.drawLine(int(x_end), int(y_beam), int(x_end + 6), int(y_beam + tri_h))
        painter.drawLine(int(x_end - 6), int(y_beam + tri_h), int(x_end + 6), int(y_beam + tri_h))

        # Flecha de carga
        arrow_pen = QPen(QColor("#f85149"), 2)
        painter.setPen(arrow_pen)
        cx = size / 2
        arrow_top = y_beam - 20
        painter.drawLine(int(cx), int(arrow_top), int(cx), int(y_beam - 2))
        # Punta de flecha
        painter.drawLine(int(cx), int(y_beam - 2), int(cx - 4), int(y_beam - 8))
        painter.drawLine(int(cx), int(y_beam - 2), int(cx + 4), int(y_beam - 8))

        painter.end()

        label = QLabel()
        label.setPixmap(pixmap)
        label.setFixedSize(size, size)
        return label
