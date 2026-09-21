"""
Diálogo para agregar o editar apoyos de la viga.

Soporta tres tipos de apoyo: articulado (pin), rodillo (roller) y
empotrado (fixed), con validación de posición dentro de la longitud
de la viga y nombres auto-generados.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QPolygonF
from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


# ──────────────────────────────────────────────────────────────────────
# Enumeración de tipos de apoyo
# ──────────────────────────────────────────────────────────────────────

class SupportType(Enum):
    """Tipos de apoyo disponibles."""

    PIN = "Articulado"
    ROLLER = "Rodillo"
    FIXED = "Empotrado"


# ──────────────────────────────────────────────────────────────────────
# Resultado
# ──────────────────────────────────────────────────────────────────────

@dataclass
class SupportData:
    """Datos del apoyo devueltos por el diálogo."""

    support_type: SupportType
    position: float
    name: str


# ──────────────────────────────────────────────────────────────────────
# Widget de icono de apoyo
# ──────────────────────────────────────────────────────────────────────

class _SupportIcon(QWidget):
    """Widget que dibuja un icono esquemático del tipo de apoyo."""

    def __init__(self, support_type: SupportType, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._support_type = support_type
        self.setFixedSize(80, 80)

    def set_support_type(self, support_type: SupportType) -> None:
        """Actualiza el tipo de apoyo y redibuja."""
        self._support_type = support_type
        self.update()

    def paintEvent(self, event: object) -> None:  # noqa: N802
        """Dibuja el icono del apoyo."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pen = QPen(QColor("#58a6ff"), 2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        cx = self.width() / 2
        base_y = self.height() * 0.75

        if self._support_type == SupportType.PIN:
            self._draw_pin(painter, cx, base_y)
        elif self._support_type == SupportType.ROLLER:
            self._draw_roller(painter, cx, base_y)
        elif self._support_type == SupportType.FIXED:
            self._draw_fixed(painter, cx, base_y)

        painter.end()

    def _draw_pin(self, painter: QPainter, cx: float, base_y: float) -> None:
        """Dibuja un apoyo articulado (triángulo)."""
        size = 24.0
        triangle = QPolygonF([
            QPointF(cx, base_y - size),
            QPointF(cx - size * 0.7, base_y),
            QPointF(cx + size * 0.7, base_y),
        ])
        painter.drawPolygon(triangle)
        # Línea de tierra
        painter.drawLine(
            QPointF(cx - size, base_y + 2),
            QPointF(cx + size, base_y + 2),
        )
        # Achurado
        for i in range(5):
            x = cx - size + i * (2 * size / 4)
            painter.drawLine(
                QPointF(x, base_y + 2),
                QPointF(x - 6, base_y + 10),
            )

    def _draw_roller(self, painter: QPainter, cx: float, base_y: float) -> None:
        """Dibuja un apoyo de rodillo (triángulo + círculos)."""
        size = 24.0
        triangle = QPolygonF([
            QPointF(cx, base_y - size),
            QPointF(cx - size * 0.7, base_y),
            QPointF(cx + size * 0.7, base_y),
        ])
        painter.drawPolygon(triangle)

        # Círculos (rodillos)
        r = 5.0
        for dx in (-10.0, 0.0, 10.0):
            painter.drawEllipse(QPointF(cx + dx, base_y + r + 2), r, r)

        # Línea de tierra
        painter.drawLine(
            QPointF(cx - size, base_y + 2 * r + 4),
            QPointF(cx + size, base_y + 2 * r + 4),
        )

    def _draw_fixed(self, painter: QPainter, cx: float, base_y: float) -> None:
        """Dibuja un empotramiento (pared con achurado)."""
        wall_height = 40.0
        wall_x = cx - 10

        # Pared vertical
        painter.drawLine(
            QPointF(wall_x, base_y - wall_height / 2),
            QPointF(wall_x, base_y + wall_height / 2),
        )
        # Achurado
        for i in range(6):
            y = base_y - wall_height / 2 + i * (wall_height / 5)
            painter.drawLine(
                QPointF(wall_x, y),
                QPointF(wall_x - 12, y + 8),
            )
        # Línea horizontal (viga)
        painter.drawLine(
            QPointF(wall_x, base_y),
            QPointF(cx + 20, base_y),
        )


# ──────────────────────────────────────────────────────────────────────
# Diálogo principal
# ──────────────────────────────────────────────────────────────────────

class SupportDialog(QDialog):
    """Diálogo para agregar o editar un apoyo de la viga."""

    # Letras para auto-generación de nombres
    _ALPHA = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        beam_length: float = 10.0,
        existing_names: Optional[list[str]] = None,
        edit_data: Optional[SupportData] = None,
    ) -> None:
        """
        Crea el diálogo de apoyo.

        Parameters
        ----------
        parent : QWidget | None
            Widget padre.
        beam_length : float
            Longitud de la viga en metros.
        existing_names : list[str] | None
            Nombres de apoyos ya existentes (para evitar duplicados).
        edit_data : SupportData | None
            Si se proporciona, el diálogo entra en modo edición.
        """
        super().__init__(parent)
        self._beam_length = beam_length
        self._existing_names = existing_names or []
        self._edit_mode = edit_data is not None
        self._edit_original_name = edit_data.name if edit_data else ""

        self.setWindowTitle("Editar Apoyo" if self._edit_mode else "Agregar Apoyo")
        self.setMinimumWidth(420)
        self.setModal(True)

        self._result_data: Optional[SupportData] = None
        self._build_ui()

        if edit_data is not None:
            self._populate_from_data(edit_data)
        else:
            self._auto_generate_name()

        self._connect_signals()

    # ── Construcción de UI ────────────────────────────────────────────

    def _build_ui(self) -> None:
        """Construye la interfaz del diálogo."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)

        # Título
        title = QLabel("Editar Apoyo" if self._edit_mode else "Agregar Apoyo")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        # ── Tipo de apoyo + icono ─────────────────────────────────────
        type_group = QGroupBox("Tipo de Apoyo")
        type_layout = QHBoxLayout(type_group)

        form_col = QVBoxLayout()
        self._combo_type = QComboBox()
        for st in SupportType:
            self._combo_type.addItem(st.value, st)
        form_col.addWidget(QLabel("Tipo:"))
        form_col.addWidget(self._combo_type)

        # Descripción dinámica
        self._lbl_type_desc = QLabel("")
        self._lbl_type_desc.setWordWrap(True)
        self._lbl_type_desc.setStyleSheet("color: #8b949e; font-size: 11px;")
        form_col.addWidget(self._lbl_type_desc)
        form_col.addStretch()

        type_layout.addLayout(form_col, stretch=2)

        # Icono visual
        self._support_icon = _SupportIcon(SupportType.PIN)
        type_layout.addWidget(self._support_icon, stretch=1, alignment=Qt.AlignmentFlag.AlignCenter)

        main_layout.addWidget(type_group)

        # ── Posición y nombre ─────────────────────────────────────────
        props_group = QGroupBox("Propiedades")
        props_layout = QFormLayout(props_group)

        self._spin_position = QDoubleSpinBox()
        self._spin_position.setRange(0.0, self._beam_length)
        self._spin_position.setDecimals(4)
        self._spin_position.setSuffix(" m")
        self._spin_position.setValue(0.0)
        self._spin_position.setToolTip("Posición del apoyo a lo largo de la viga")

        self._edit_name = QLineEdit()
        self._edit_name.setMaxLength(10)
        self._edit_name.setToolTip("Nombre identificador del apoyo")

        props_layout.addRow("Posición:", self._spin_position)
        props_layout.addRow("Nombre:", self._edit_name)
        main_layout.addWidget(props_group)

        # ── Botones ──────────────────────────────────────────────────
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Aceptar")
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

    # ── Señales ───────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        """Conecta señales de los widgets."""
        self._combo_type.currentIndexChanged.connect(self._on_type_changed)
        self._on_type_changed()

    def _on_type_changed(self) -> None:
        """Actualiza icono y descripción según el tipo seleccionado."""
        support_type = self._combo_type.currentData()
        if support_type is None:
            return

        self._support_icon.set_support_type(support_type)

        descriptions = {
            SupportType.PIN: (
                "Apoyo articulado: restringe desplazamiento vertical y horizontal, "
                "permite rotación. Aporta 2 reacciones (Rx, Ry)."
            ),
            SupportType.ROLLER: (
                "Apoyo de rodillo: restringe desplazamiento vertical, permite "
                "desplazamiento horizontal y rotación. Aporta 1 reacción (Ry)."
            ),
            SupportType.FIXED: (
                "Empotramiento: restringe desplazamiento y rotación. "
                "Aporta 3 reacciones (Rx, Ry, M)."
            ),
        }
        self._lbl_type_desc.setText(descriptions.get(support_type, ""))

    # ── Auto-generar nombre ───────────────────────────────────────────

    def _auto_generate_name(self) -> None:
        """Genera un nombre automático (A, B, C, ...) que no esté en uso."""
        for letter in self._ALPHA:
            if letter not in self._existing_names:
                self._edit_name.setText(letter)
                return
        # Si se agotaron las letras simples, usar letras dobles
        for i, l1 in enumerate(self._ALPHA):
            for l2 in self._ALPHA:
                name = f"{l1}{l2}"
                if name not in self._existing_names:
                    self._edit_name.setText(name)
                    return

    # ── Poblar desde datos existentes ─────────────────────────────────

    def _populate_from_data(self, data: SupportData) -> None:
        """Rellena campos con datos de un apoyo existente."""
        idx = self._combo_type.findData(data.support_type)
        if idx >= 0:
            self._combo_type.setCurrentIndex(idx)
        self._spin_position.setValue(data.position)
        self._edit_name.setText(data.name)

    # ── Validación ────────────────────────────────────────────────────

    def _validate(self) -> list[str]:
        """Valida los datos ingresados."""
        errors: list[str] = []
        pos = self._spin_position.value()
        name = self._edit_name.text().strip()

        if pos < 0 or pos > self._beam_length:
            errors.append(
                f"La posición debe estar entre 0 y {self._beam_length:.2f} m."
            )

        if not name:
            errors.append("El nombre del apoyo no puede estar vacío.")
        elif (
            name in self._existing_names
            and name != self._edit_original_name
        ):
            errors.append(f"Ya existe un apoyo con el nombre '{name}'.")

        return errors

    # ── Aceptar ───────────────────────────────────────────────────────

    def _on_accept(self) -> None:
        """Valida y acepta el diálogo."""
        errors = self._validate()
        if errors:
            QMessageBox.warning(
                self,
                "Datos inválidos",
                "\n".join(f"• {e}" for e in errors),
            )
            return

        self._result_data = SupportData(
            support_type=self._combo_type.currentData(),
            position=self._spin_position.value(),
            name=self._edit_name.text().strip(),
        )
        self.accept()

    # ── API pública ───────────────────────────────────────────────────

    def get_support_data(self) -> Optional[SupportData]:
        """
        Devuelve los datos del apoyo configurado.

        Returns
        -------
        SupportData | None
            Los datos si el diálogo fue aceptado, ``None`` en caso contrario.
        """
        return self._result_data
