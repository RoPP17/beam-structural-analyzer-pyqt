"""
Panel de propiedades lateral derecho para BeamAnalyzer.

Muestra y permite editar las propiedades del elemento estructural
seleccionado (viga, apoyo, carga, momento, etc.).
"""

from __future__ import annotations

from typing import Any, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDoubleValidator
from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class _ValidatedLineEdit(QLineEdit):
    """QLineEdit con validación numérica en tiempo real.

    Pone un borde rojo cuando el contenido no es un número válido.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        allow_negative: bool = True,
        decimals: int = 4,
    ) -> None:
        super().__init__(parent)
        bottom = -1e12 if allow_negative else 0.0
        validator = QDoubleValidator(bottom, 1e12, decimals, self)
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.setValidator(validator)
        self.textChanged.connect(self._check_validity)

    def _check_validity(self, _text: str) -> None:
        valid = self.hasAcceptableInput()
        self.setProperty("invalid", not valid)
        self.style().unpolish(self)
        self.style().polish(self)

    def numeric_value(self) -> Optional[float]:
        """Devuelve el valor numérico o ``None`` si no es válido."""
        try:
            return float(self.text().replace(",", "."))
        except (ValueError, TypeError):
            return None


class PropertyPanel(QWidget):
    """Panel lateral derecho para inspección/edición de propiedades.

    Attributes:
        property_changed: Señal emitida cuando el usuario aplica un
            cambio.  Argumentos: ``(element_id, property_name, value)``.
    """

    property_changed = pyqtSignal(str, str, object)

    # Mapeo de tipo de elemento a definiciones de campos.
    # Cada campo: (nombre_interno, etiqueta, unidad, negativo_permitido)
    _FIELD_DEFS: dict[str, list[tuple[str, str, str, bool]]] = {
        "beam": [
            ("length", "Longitud", "m", False),
            ("E", "Módulo de Elasticidad (E)", "GPa", False),
            ("I", "Momento de Inercia (I)", "m⁴", False),
        ],
        "pinned_support": [
            ("position", "Posición", "m", False),
            ("name", "Nombre", "", True),
        ],
        "roller_support": [
            ("position", "Posición", "m", False),
            ("name", "Nombre", "", True),
        ],
        "fixed_support": [
            ("position", "Posición", "m", False),
            ("name", "Nombre", "", True),
        ],
        "point_load": [
            ("magnitude", "Magnitud", "kN", False),
            ("position", "Posición", "m", False),
        ],
        "distributed_load": [
            ("intensity", "Intensidad (w)", "kN/m", False),
            ("start", "Inicio", "m", False),
            ("end", "Fin", "m", False),
        ],
        "triangular_load": [
            ("w_start", "w inicio", "kN/m", True),
            ("w_end", "w fin", "kN/m", True),
            ("start", "Inicio", "m", False),
            ("end", "Fin", "m", False),
        ],
        "trapezoidal_load": [
            ("w_start", "w inicio", "kN/m", True),
            ("w_end", "w fin", "kN/m", True),
            ("start", "Inicio", "m", False),
            ("end", "Fin", "m", False),
        ],
        "moment": [
            ("magnitude", "Magnitud", "kN·m", True),
            ("position", "Posición", "m", False),
        ],
        "inclined_load": [
            ("magnitude", "Magnitud", "kN", False),
            ("position", "Posición", "m", False),
            ("angle", "Ángulo", "°", True),
        ],
    }

    # Campos tipo combo por elemento
    _COMBO_DEFS: dict[str, list[tuple[str, str, list[tuple[str, str]]]]] = {
        "point_load": [
            ("direction", "Dirección", [
                ("down", "↓ Hacia abajo"),
                ("up", "↑ Hacia arriba"),
            ]),
        ],
        "moment": [
            ("direction", "Sentido", [
                ("ccw", "↺ Antihorario (+)"),
                ("cw", "↻ Horario (−)"),
            ]),
        ],
        "beam": [
            ("units", "Sistema de Unidades", [
                ("si_kn_m", "kN, m"),
                ("si_n_mm", "N, mm"),
                ("imperial", "lb, ft"),
            ]),
        ],
    }

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("propertyPanel")
        self.setMinimumWidth(240)
        self.setMaximumWidth(320)

        self._current_element_id: Optional[str] = None
        self._current_element_type: Optional[str] = None
        self._field_widgets: dict[str, QLineEdit | QComboBox] = {}

        self._setup_ui()

    # ── Construcción de la interfaz ─────────────────────────────

    def _setup_ui(self) -> None:
        """Crea la disposición base del panel."""
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # Título
        title_label = QLabel("Propiedades")
        title_label.setObjectName("accentLabel")
        title_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        title_label.setStyleSheet(
            "font-size: 15px; font-weight: bold; padding: 12px 12px 8px 12px;"
        )
        outer_layout.addWidget(title_label)

        # Área scrollable para el formulario dinámico
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        outer_layout.addWidget(self._scroll_area)

        # Contenedor interno del scroll area
        self._form_container = QWidget()
        self._form_layout = QVBoxLayout(self._form_container)
        self._form_layout.setContentsMargins(12, 8, 12, 8)
        self._form_layout.setSpacing(8)
        self._scroll_area.setWidget(self._form_container)

        # Mensaje por defecto
        self._empty_label = QLabel("Ningún elemento seleccionado")
        self._empty_label.setObjectName("secondaryLabel")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setWordWrap(True)
        self._empty_label.setStyleSheet("padding: 40px 12px; font-size: 13px;")
        self._form_layout.addWidget(self._empty_label)
        self._form_layout.addStretch()

        # Botón Aplicar (oculto al inicio)
        self._apply_button = QPushButton("Aplicar")
        self._apply_button.setObjectName("primaryButton")
        self._apply_button.setMinimumHeight(34)
        self._apply_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_button.setVisible(False)
        self._apply_button.clicked.connect(self._on_apply_clicked)
        outer_layout.addWidget(
            self._apply_button,
            alignment=Qt.AlignmentFlag.AlignBottom,
        )

    # ── API pública ─────────────────────────────────────────────

    def show_properties(
        self,
        element_id: str,
        element_type: str,
        values: dict[str, Any],
    ) -> None:
        """Muestra el formulario de propiedades para un elemento.

        Args:
            element_id: Identificador único del elemento.
            element_type: Tipo del elemento (``"beam"``, ``"point_load"``, …).
            values: Diccionario ``{nombre_propiedad: valor_actual}``.
        """
        self._current_element_id = element_id
        self._current_element_type = element_type
        self._field_widgets.clear()
        self._clear_form_layout()

        group_title = self._friendly_type_name(element_type)
        group_box = QGroupBox(group_title)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(10)
        form.setContentsMargins(8, 16, 8, 8)

        # Campos numéricos / texto
        field_defs = self._FIELD_DEFS.get(element_type, [])
        for field_name, label_text, unit, allow_neg in field_defs:
            if field_name == "name":
                # Campo de texto simple para nombres
                line_edit = QLineEdit()
                line_edit.setText(str(values.get(field_name, "")))
                line_edit.editingFinished.connect(self._on_apply_clicked)
                self._field_widgets[field_name] = line_edit
                form.addRow(f"{label_text}:", line_edit)
            else:
                row_widget = QWidget()
                row_layout = QHBoxLayout(row_widget)
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.setSpacing(4)

                line_edit = _ValidatedLineEdit(
                    allow_negative=allow_neg,
                )
                val = values.get(field_name)
                if val is not None:
                    line_edit.setText(f"{float(val):.4g}")
                
                # Sincronización instantánea al terminar de editar (Enter o perder foco)
                line_edit.editingFinished.connect(self._on_apply_clicked)
                
                self._field_widgets[field_name] = line_edit
                row_layout.addWidget(line_edit, stretch=1)

                if unit:
                    unit_label = QLabel(unit)
                    unit_label.setObjectName("unitLabel")
                    row_layout.addWidget(unit_label)

                form.addRow(f"{label_text}:", row_widget)

        # Campos tipo ComboBox
        combo_defs = self._COMBO_DEFS.get(element_type, [])
        for combo_name, combo_label, options in combo_defs:
            combo = QComboBox()
            for option_value, option_text in options:
                combo.addItem(option_text, option_value)
            current_val = values.get(combo_name)
            if current_val is not None:
                index = combo.findData(current_val)
                if index >= 0:
                    combo.setCurrentIndex(index)
                    
            # Sincronización instantánea
            combo.currentIndexChanged.connect(self._on_apply_clicked)
            
            self._field_widgets[combo_name] = combo
            form.addRow(f"{combo_label}:", combo)

        group_box.setLayout(form)
        self._form_layout.insertWidget(0, group_box)
        self._form_layout.addStretch()
        # El botón de aplicar ya no es estrictamente necesario, pero lo dejamos por si acaso.
        self._apply_button.setVisible(True)

    def clear_properties(self) -> None:
        """Limpia el formulario y muestra el mensaje por defecto."""
        self._current_element_id = None
        self._current_element_type = None
        self._field_widgets.clear()
        self._clear_form_layout()

        self._empty_label = QLabel("Ningún elemento seleccionado")
        self._empty_label.setObjectName("secondaryLabel")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setWordWrap(True)
        self._empty_label.setStyleSheet("padding: 40px 12px; font-size: 13px;")
        self._form_layout.addWidget(self._empty_label)
        self._form_layout.addStretch()
        self._apply_button.setVisible(False)

    def get_current_values(self) -> dict[str, Any]:
        """Lee los valores actuales del formulario.

        Returns:
            Diccionario ``{nombre_propiedad: valor}``.
        """
        result: dict[str, Any] = {}
        for field_name, widget in self._field_widgets.items():
            if isinstance(widget, QComboBox):
                result[field_name] = widget.currentData()
            elif isinstance(widget, _ValidatedLineEdit):
                result[field_name] = widget.numeric_value()
            elif isinstance(widget, QLineEdit):
                result[field_name] = widget.text()
        return result

    # ── Internos ────────────────────────────────────────────────

    def _clear_form_layout(self) -> None:
        """Elimina todos los widgets del layout del formulario."""
        while self._form_layout.count():
            item = self._form_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _on_apply_clicked(self) -> None:
        """Emite ``property_changed`` por cada campo modificado."""
        if self._current_element_id is None:
            return
        values = self.get_current_values()
        for prop_name, value in values.items():
            if value is not None:
                self.property_changed.emit(
                    self._current_element_id, prop_name, value
                )

    @staticmethod
    def _friendly_type_name(element_type: str) -> str:
        """Traduce el tipo interno a un nombre legible en español."""
        names: dict[str, str] = {
            "beam": "Viga",
            "pinned_support": "Apoyo Articulado",
            "roller_support": "Apoyo de Rodillo",
            "fixed_support": "Empotrado",
            "point_load": "Carga Puntual",
            "distributed_load": "Carga Distribuida",
            "triangular_load": "Carga Triangular",
            "trapezoidal_load": "Carga Trapezoidal",
            "moment": "Momento",
            "inclined_load": "Carga Inclinada",
        }
        return names.get(element_type, element_type.replace("_", " ").title())
