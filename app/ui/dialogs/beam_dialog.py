"""
Diálogo para crear y configurar la viga principal.

Permite al usuario definir la longitud de la viga, el módulo de elasticidad
y el momento de inercia, con selectores de unidades apropiados.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDoubleValidator, QFont, QIcon
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QComboBox,
    QLabel,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)


# ──────────────────────────────────────────────────────────────────────
# Constantes de conversión
# ──────────────────────────────────────────────────────────────────────

LENGTH_UNITS: dict[str, float] = {
    "m": 1.0,
    "cm": 0.01,
    "mm": 0.001,
    "ft": 0.3048,
}
"""Factores para convertir cada unidad a metros."""

ELASTIC_MOD_UNITS: dict[str, float] = {
    "GPa": 1.0e9,
    "MPa": 1.0e6,
    "ksi": 6.894757e6,
    "Pa": 1.0,
}
"""Factores para convertir cada unidad a Pascales."""

INERTIA_UNITS: dict[str, float] = {
    "m⁴": 1.0,
    "cm⁴": 1.0e-8,
    "mm⁴": 1.0e-12,
    "in⁴": 4.162314e-7,
}
"""Factores para convertir cada unidad a m⁴."""


@dataclass
class BeamParameters:
    """Parámetros de la viga devueltos por el diálogo."""

    length: float
    """Longitud en metros."""
    elastic_modulus: float
    """Módulo de elasticidad en Pascales."""
    moment_of_inertia: float
    """Momento de inercia en m⁴."""
    length_unit: str
    """Unidad de longitud seleccionada."""
    e_unit: str
    """Unidad de módulo de elasticidad seleccionada."""
    i_unit: str
    """Unidad de momento de inercia seleccionada."""
    raw_length: float
    """Valor de longitud en unidades originales."""
    raw_e: float
    """Valor de E en unidades originales."""
    raw_i: float
    """Valor de I en unidades originales."""


class BeamDialog(QDialog):
    """Diálogo para configurar la viga principal del análisis."""

    # ── Límites de validación ──────────────────────────────────────────
    _MIN_LENGTH_M = 0.001  # 1 mm
    _MAX_LENGTH_M = 1000.0  # 1 km
    _MIN_E_PA = 1.0e3
    _MAX_E_PA = 1.0e12
    _MIN_I_M4 = 1.0e-16
    _MAX_I_M4 = 1.0e4

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        initial_length: float = 6.0,
        initial_e: float = 200.0,
        initial_i: float = 1000.0,
        length_unit: str = "m",
        e_unit: str = "GPa",
        i_unit: str = "cm⁴",
    ) -> None:
        """
        Crea el diálogo de configuración de viga.

        Parameters
        ----------
        parent : QWidget | None
            Widget padre.
        initial_length : float
            Longitud inicial en la unidad indicada.
        initial_e : float
            Módulo de elasticidad inicial en la unidad indicada.
        initial_i : float
            Momento de inercia inicial en la unidad indicada.
        length_unit : str
            Unidad de longitud inicial.
        e_unit : str
            Unidad de E inicial.
        i_unit : str
            Unidad de I inicial.
        """
        super().__init__(parent)
        self.setWindowTitle("Configurar Viga")
        self.setMinimumWidth(480)
        self.setModal(True)

        self._result_params: Optional[BeamParameters] = None

        self._build_ui()
        self._set_initial_values(
            initial_length, initial_e, initial_i,
            length_unit, e_unit, i_unit,
        )
        self._connect_signals()

    # ── Construcción de la interfaz ────────────────────────────────────

    def _build_ui(self) -> None:
        """Construye todos los widgets del diálogo."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)

        # Título
        title_label = QLabel("Configurar Viga")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        # ── Grupo: Geometría ──────────────────────────────────────────
        geo_group = QGroupBox("Geometría")
        geo_layout = QFormLayout(geo_group)
        geo_layout.setSpacing(8)

        self._spin_length = QDoubleSpinBox()
        self._spin_length.setRange(0.001, 1_000_000.0)
        self._spin_length.setDecimals(4)
        self._spin_length.setSuffix("")
        self._spin_length.setToolTip("Longitud total de la viga")

        self._combo_length_unit = QComboBox()
        self._combo_length_unit.addItems(list(LENGTH_UNITS.keys()))
        self._combo_length_unit.setToolTip("Unidad de longitud")

        length_row = QHBoxLayout()
        length_row.addWidget(self._spin_length, stretch=3)
        length_row.addWidget(self._combo_length_unit, stretch=1)

        geo_layout.addRow("Longitud:", length_row)
        main_layout.addWidget(geo_group)

        # ── Grupo: Propiedades del material ───────────────────────────
        mat_group = QGroupBox("Propiedades del Material")
        mat_layout = QFormLayout(mat_group)
        mat_layout.setSpacing(8)

        # E
        self._spin_e = QDoubleSpinBox()
        self._spin_e.setRange(0.0001, 1.0e12)
        self._spin_e.setDecimals(4)
        self._spin_e.setToolTip("Módulo de elasticidad del material")

        self._combo_e_unit = QComboBox()
        self._combo_e_unit.addItems(list(ELASTIC_MOD_UNITS.keys()))
        self._combo_e_unit.setToolTip("Unidad del módulo de elasticidad")

        e_row = QHBoxLayout()
        e_row.addWidget(self._spin_e, stretch=3)
        e_row.addWidget(self._combo_e_unit, stretch=1)

        mat_layout.addRow("Módulo de Elasticidad (E):", e_row)

        # I
        self._spin_i = QDoubleSpinBox()
        self._spin_i.setRange(0.0001, 1.0e12)
        self._spin_i.setDecimals(6)
        self._spin_i.setToolTip("Momento de inercia de la sección transversal")

        self._combo_i_unit = QComboBox()
        self._combo_i_unit.addItems(list(INERTIA_UNITS.keys()))
        self._combo_i_unit.setToolTip("Unidad del momento de inercia")

        i_row = QHBoxLayout()
        i_row.addWidget(self._spin_i, stretch=3)
        i_row.addWidget(self._combo_i_unit, stretch=1)

        mat_layout.addRow("Momento de Inercia (I):", i_row)
        main_layout.addWidget(mat_group)

        # ── Información convertida ────────────────────────────────────
        self._lbl_info = QLabel("")
        self._lbl_info.setWordWrap(True)
        self._lbl_info.setStyleSheet("color: #8b949e; font-size: 11px;")
        main_layout.addWidget(self._lbl_info)

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

    # ── Valores iniciales ─────────────────────────────────────────────

    def _set_initial_values(
        self,
        length: float,
        e: float,
        i: float,
        l_unit: str,
        e_unit: str,
        i_unit: str,
    ) -> None:
        """Rellena los campos con los valores iniciales."""
        self._spin_length.setValue(length)
        idx = self._combo_length_unit.findText(l_unit)
        if idx >= 0:
            self._combo_length_unit.setCurrentIndex(idx)

        self._spin_e.setValue(e)
        idx = self._combo_e_unit.findText(e_unit)
        if idx >= 0:
            self._combo_e_unit.setCurrentIndex(idx)

        self._spin_i.setValue(i)
        idx = self._combo_i_unit.findText(i_unit)
        if idx >= 0:
            self._combo_i_unit.setCurrentIndex(idx)

        self._update_info()

    # ── Señales ───────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        """Conecta cambios en los campos para actualizar la vista previa."""
        self._spin_length.valueChanged.connect(self._update_info)
        self._combo_length_unit.currentIndexChanged.connect(self._update_info)
        self._spin_e.valueChanged.connect(self._update_info)
        self._combo_e_unit.currentIndexChanged.connect(self._update_info)
        self._spin_i.valueChanged.connect(self._update_info)
        self._combo_i_unit.currentIndexChanged.connect(self._update_info)

    # ── Conversión y validación ───────────────────────────────────────

    def _convert_to_si(self) -> tuple[float, float, float]:
        """Convierte los valores ingresados a unidades SI (m, Pa, m⁴)."""
        l_unit = self._combo_length_unit.currentText()
        e_unit = self._combo_e_unit.currentText()
        i_unit = self._combo_i_unit.currentText()

        length_m = self._spin_length.value() * LENGTH_UNITS[l_unit]
        e_pa = self._spin_e.value() * ELASTIC_MOD_UNITS[e_unit]
        i_m4 = self._spin_i.value() * INERTIA_UNITS[i_unit]

        return length_m, e_pa, i_m4

    def _update_info(self) -> None:
        """Actualiza la etiqueta informativa con los valores en SI."""
        length_m, e_pa, i_m4 = self._convert_to_si()
        self._lbl_info.setText(
            f"Valores en SI → L = {length_m:.4g} m  |  "
            f"E = {e_pa:.4g} Pa  |  I = {i_m4:.4g} m⁴"
        )

    def _validate(self) -> list[str]:
        """
        Valida los datos ingresados.

        Returns
        -------
        list[str]
            Lista de mensajes de error (vacía si todo es válido).
        """
        errors: list[str] = []
        length_m, e_pa, i_m4 = self._convert_to_si()

        if length_m <= 0:
            errors.append("La longitud debe ser un valor positivo.")
        elif length_m < self._MIN_LENGTH_M:
            errors.append(
                f"La longitud es demasiado pequeña (mínimo {self._MIN_LENGTH_M} m)."
            )
        elif length_m > self._MAX_LENGTH_M:
            errors.append(
                f"La longitud es demasiado grande (máximo {self._MAX_LENGTH_M} m)."
            )

        if e_pa <= 0:
            errors.append("El módulo de elasticidad debe ser positivo.")
        elif e_pa < self._MIN_E_PA:
            errors.append("El módulo de elasticidad es demasiado bajo.")
        elif e_pa > self._MAX_E_PA:
            errors.append("El módulo de elasticidad es demasiado alto.")

        if i_m4 <= 0:
            errors.append("El momento de inercia debe ser positivo.")
        elif i_m4 < self._MIN_I_M4:
            errors.append("El momento de inercia es demasiado bajo.")
        elif i_m4 > self._MAX_I_M4:
            errors.append("El momento de inercia es demasiado alto.")

        return errors

    # ── Aceptar ───────────────────────────────────────────────────────

    def _on_accept(self) -> None:
        """Valida y acepta el diálogo si los datos son correctos."""
        errors = self._validate()
        if errors:
            QMessageBox.warning(
                self,
                "Datos inválidos",
                "\n".join(f"• {e}" for e in errors),
            )
            return

        length_m, e_pa, i_m4 = self._convert_to_si()
        self._result_params = BeamParameters(
            length=length_m,
            elastic_modulus=e_pa,
            moment_of_inertia=i_m4,
            length_unit=self._combo_length_unit.currentText(),
            e_unit=self._combo_e_unit.currentText(),
            i_unit=self._combo_i_unit.currentText(),
            raw_length=self._spin_length.value(),
            raw_e=self._spin_e.value(),
            raw_i=self._spin_i.value(),
        )
        self.accept()

    # ── API pública ───────────────────────────────────────────────────

    def get_parameters(self) -> Optional[BeamParameters]:
        """
        Devuelve los parámetros de la viga configurados.

        Returns
        -------
        BeamParameters | None
            Los parámetros si el diálogo fue aceptado, ``None`` en caso contrario.
        """
        return self._result_params
