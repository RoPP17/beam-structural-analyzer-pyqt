"""
Diálogo para agregar o editar cargas aplicadas sobre la viga.

Soporta múltiples tipos de carga (puntual, distribuida uniforme,
triangular, trapezoidal, momento e inclinada) con formularios dinámicos
que cambian según el tipo seleccionado.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


# ──────────────────────────────────────────────────────────────────────
# Enumeraciones
# ──────────────────────────────────────────────────────────────────────

class LoadType(Enum):
    """Tipos de carga soportados."""

    POINT = "Puntual"
    DISTRIBUTED = "Distribuida Uniforme"
    TRIANGULAR = "Triangular"
    TRAPEZOIDAL = "Trapezoidal"
    MOMENT = "Momento"
    INCLINED = "Inclinada"


class LoadDirection(Enum):
    """Dirección de la carga."""

    DOWN = "Abajo (↓)"
    UP = "Arriba (↑)"


class MomentDirection(Enum):
    """Sentido de giro del momento."""

    CLOCKWISE = "Horario (↻)"
    COUNTERCLOCKWISE = "Antihorario (↺)"


# ──────────────────────────────────────────────────────────────────────
# Resultado
# ──────────────────────────────────────────────────────────────────────

@dataclass
class LoadData:
    """Datos de carga devueltos por el diálogo."""

    load_type: LoadType
    magnitude: float = 0.0
    position: float = 0.0
    start: float = 0.0
    end: float = 0.0
    w_start: float = 0.0
    w_end: float = 0.0
    angle: float = 0.0
    direction: str = "down"
    moment_direction: str = "counterclockwise"
    description: str = ""


# ──────────────────────────────────────────────────────────────────────
# Diálogo principal
# ──────────────────────────────────────────────────────────────────────

class LoadDialog(QDialog):
    """Diálogo para agregar o editar una carga sobre la viga."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        beam_length: float = 10.0,
        edit_data: Optional[LoadData] = None,
    ) -> None:
        """
        Crea el diálogo de carga.

        Parameters
        ----------
        parent : QWidget | None
            Widget padre.
        beam_length : float
            Longitud de la viga en metros (para validación de posiciones).
        edit_data : LoadData | None
            Si se proporciona, el diálogo entra en modo edición.
        """
        super().__init__(parent)
        self._beam_length = beam_length
        self._edit_mode = edit_data is not None
        self.setWindowTitle("Editar Carga" if self._edit_mode else "Agregar Carga")
        self.setMinimumWidth(520)
        self.setModal(True)

        self._result_data: Optional[LoadData] = None
        self._form_pages: dict[LoadType, QWidget] = {}

        self._build_ui()
        if edit_data is not None:
            self._populate_from_data(edit_data)
        self._connect_signals()
        self._on_type_changed()

    # ── Construcción de UI ────────────────────────────────────────────

    def _build_ui(self) -> None:
        """Construye la interfaz completa del diálogo."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)

        # Título
        title = QLabel("Editar Carga" if self._edit_mode else "Agregar Carga")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        # Selector de tipo
        type_group = QGroupBox("Tipo de Carga")
        type_layout = QFormLayout(type_group)
        self._combo_type = QComboBox()
        for lt in LoadType:
            self._combo_type.addItem(lt.value, lt)
        type_layout.addRow("Tipo:", self._combo_type)
        main_layout.addWidget(type_group)

        # Formularios apilados
        self._stacked = QStackedWidget()
        self._build_point_form()
        self._build_distributed_form()
        self._build_triangular_form()
        self._build_trapezoidal_form()
        self._build_moment_form()
        self._build_inclined_form()
        main_layout.addWidget(self._stacked)

        # Vista previa de descripción
        self._lbl_preview = QLabel("")
        self._lbl_preview.setWordWrap(True)
        self._lbl_preview.setStyleSheet(
            "color: #8b949e; font-size: 11px; padding: 6px; "
            "border: 1px solid #30363d; border-radius: 4px;"
        )
        main_layout.addWidget(self._lbl_preview)

        # Botones
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Aceptar")
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

    # ── Creadores de formularios ──────────────────────────────────────

    def _make_spin(
        self,
        minimum: float = -1.0e6,
        maximum: float = 1.0e6,
        decimals: int = 4,
        value: float = 0.0,
        suffix: str = "",
        tooltip: str = "",
    ) -> QDoubleSpinBox:
        """Crea un QDoubleSpinBox pre-configurado."""
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setDecimals(decimals)
        spin.setValue(value)
        if suffix:
            spin.setSuffix(f" {suffix}")
        if tooltip:
            spin.setToolTip(tooltip)
        spin.valueChanged.connect(self._update_preview)
        return spin

    def _build_point_form(self) -> None:
        """Formulario: Carga Puntual."""
        page = QWidget()
        layout = QFormLayout(page)

        self._point_magnitude = self._make_spin(
            minimum=0.0001, maximum=1.0e6, value=10.0,
            suffix="kN", tooltip="Magnitud de la fuerza puntual",
        )
        self._point_position = self._make_spin(
            minimum=0.0, maximum=self._beam_length, value=self._beam_length / 2,
            suffix="m", tooltip="Posición a lo largo de la viga",
        )
        self._point_direction = QComboBox()
        for d in LoadDirection:
            self._point_direction.addItem(d.value, d)
        self._point_direction.currentIndexChanged.connect(self._update_preview)

        layout.addRow("Magnitud (P):", self._point_magnitude)
        layout.addRow("Posición (x):", self._point_position)
        layout.addRow("Dirección:", self._point_direction)

        self._form_pages[LoadType.POINT] = page
        self._stacked.addWidget(page)

    def _build_distributed_form(self) -> None:
        """Formulario: Carga Distribuida Uniforme."""
        page = QWidget()
        layout = QFormLayout(page)

        self._dist_intensity = self._make_spin(
            minimum=0.0001, maximum=1.0e6, value=5.0,
            suffix="kN/m", tooltip="Intensidad de la carga distribuida",
        )
        self._dist_start = self._make_spin(
            minimum=0.0, maximum=self._beam_length, value=0.0,
            suffix="m", tooltip="Posición de inicio",
        )
        self._dist_end = self._make_spin(
            minimum=0.0, maximum=self._beam_length, value=self._beam_length,
            suffix="m", tooltip="Posición de fin",
        )
        self._dist_direction = QComboBox()
        for d in LoadDirection:
            self._dist_direction.addItem(d.value, d)
        self._dist_direction.currentIndexChanged.connect(self._update_preview)

        layout.addRow("Intensidad (w):", self._dist_intensity)
        layout.addRow("Inicio (a):", self._dist_start)
        layout.addRow("Fin (b):", self._dist_end)
        layout.addRow("Dirección:", self._dist_direction)

        self._form_pages[LoadType.DISTRIBUTED] = page
        self._stacked.addWidget(page)

    def _build_triangular_form(self) -> None:
        """Formulario: Carga Triangular."""
        page = QWidget()
        layout = QFormLayout(page)

        self._tri_w_start = self._make_spin(
            minimum=0.0, maximum=1.0e6, value=0.0,
            suffix="kN/m", tooltip="Intensidad al inicio",
        )
        self._tri_w_end = self._make_spin(
            minimum=0.0, maximum=1.0e6, value=20.0,
            suffix="kN/m", tooltip="Intensidad al final",
        )
        self._tri_start = self._make_spin(
            minimum=0.0, maximum=self._beam_length, value=0.0,
            suffix="m", tooltip="Posición de inicio",
        )
        self._tri_end = self._make_spin(
            minimum=0.0, maximum=self._beam_length, value=self._beam_length,
            suffix="m", tooltip="Posición de fin",
        )
        self._tri_direction = QComboBox()
        for d in LoadDirection:
            self._tri_direction.addItem(d.value, d)
        self._tri_direction.currentIndexChanged.connect(self._update_preview)

        layout.addRow("w inicio:", self._tri_w_start)
        layout.addRow("w final:", self._tri_w_end)
        layout.addRow("Inicio (a):", self._tri_start)
        layout.addRow("Fin (b):", self._tri_end)
        layout.addRow("Dirección:", self._tri_direction)

        self._form_pages[LoadType.TRIANGULAR] = page
        self._stacked.addWidget(page)

    def _build_trapezoidal_form(self) -> None:
        """Formulario: Carga Trapezoidal."""
        page = QWidget()
        layout = QFormLayout(page)

        self._trap_w_start = self._make_spin(
            minimum=0.0001, maximum=1.0e6, value=5.0,
            suffix="kN/m", tooltip="Intensidad al inicio",
        )
        self._trap_w_end = self._make_spin(
            minimum=0.0001, maximum=1.0e6, value=15.0,
            suffix="kN/m", tooltip="Intensidad al final",
        )
        self._trap_start = self._make_spin(
            minimum=0.0, maximum=self._beam_length, value=0.0,
            suffix="m", tooltip="Posición de inicio",
        )
        self._trap_end = self._make_spin(
            minimum=0.0, maximum=self._beam_length, value=self._beam_length,
            suffix="m", tooltip="Posición de fin",
        )
        self._trap_direction = QComboBox()
        for d in LoadDirection:
            self._trap_direction.addItem(d.value, d)
        self._trap_direction.currentIndexChanged.connect(self._update_preview)

        layout.addRow("w inicio:", self._trap_w_start)
        layout.addRow("w final:", self._trap_w_end)
        layout.addRow("Inicio (a):", self._trap_start)
        layout.addRow("Fin (b):", self._trap_end)
        layout.addRow("Dirección:", self._trap_direction)

        self._form_pages[LoadType.TRAPEZOIDAL] = page
        self._stacked.addWidget(page)

    def _build_moment_form(self) -> None:
        """Formulario: Momento concentrado."""
        page = QWidget()
        layout = QFormLayout(page)

        self._mom_magnitude = self._make_spin(
            minimum=0.0001, maximum=1.0e6, value=10.0,
            suffix="kN·m", tooltip="Magnitud del momento",
        )
        self._mom_position = self._make_spin(
            minimum=0.0, maximum=self._beam_length, value=self._beam_length / 2,
            suffix="m", tooltip="Posición del momento",
        )
        self._mom_direction = QComboBox()
        for md in MomentDirection:
            self._mom_direction.addItem(md.value, md)
        self._mom_direction.currentIndexChanged.connect(self._update_preview)

        layout.addRow("Magnitud (M):", self._mom_magnitude)
        layout.addRow("Posición (x):", self._mom_position)
        layout.addRow("Sentido:", self._mom_direction)

        self._form_pages[LoadType.MOMENT] = page
        self._stacked.addWidget(page)

    def _build_inclined_form(self) -> None:
        """Formulario: Carga Inclinada."""
        page = QWidget()
        layout = QFormLayout(page)

        self._incl_magnitude = self._make_spin(
            minimum=0.0001, maximum=1.0e6, value=10.0,
            suffix="kN", tooltip="Magnitud de la fuerza",
        )
        self._incl_position = self._make_spin(
            minimum=0.0, maximum=self._beam_length, value=self._beam_length / 2,
            suffix="m", tooltip="Posición de aplicación",
        )
        self._incl_angle = self._make_spin(
            minimum=-360.0, maximum=360.0, value=45.0,
            suffix="°", tooltip="Ángulo respecto a la horizontal (positivo = arriba)",
        )

        layout.addRow("Magnitud (F):", self._incl_magnitude)
        layout.addRow("Posición (x):", self._incl_position)
        layout.addRow("Ángulo (θ):", self._incl_angle)

        self._form_pages[LoadType.INCLINED] = page
        self._stacked.addWidget(page)

    # ── Señales ───────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        """Conecta las señales de los widgets."""
        self._combo_type.currentIndexChanged.connect(self._on_type_changed)

    def _on_type_changed(self) -> None:
        """Cambia el formulario visible según el tipo de carga seleccionado."""
        load_type = self._combo_type.currentData()
        if load_type is None:
            return
        page = self._form_pages.get(load_type)
        if page is not None:
            self._stacked.setCurrentWidget(page)
        self._update_preview()

    # ── Vista previa ──────────────────────────────────────────────────

    def _update_preview(self) -> None:
        """Actualiza la descripción de la carga actual."""
        load_type = self._combo_type.currentData()
        if load_type is None:
            return

        desc = self._generate_description(load_type)
        self._lbl_preview.setText(f"📋 {desc}")

    def _generate_description(self, load_type: LoadType) -> str:
        """Genera una descripción textual de la carga configurada."""
        if load_type == LoadType.POINT:
            mag = self._point_magnitude.value()
            pos = self._point_position.value()
            direction = self._point_direction.currentData()
            dir_txt = "hacia abajo" if direction == LoadDirection.DOWN else "hacia arriba"
            return f"Carga puntual de {mag:.2f} kN {dir_txt} en x = {pos:.2f} m"

        if load_type == LoadType.DISTRIBUTED:
            w = self._dist_intensity.value()
            a = self._dist_start.value()
            b = self._dist_end.value()
            direction = self._dist_direction.currentData()
            dir_txt = "hacia abajo" if direction == LoadDirection.DOWN else "hacia arriba"
            return (
                f"Carga distribuida uniforme de {w:.2f} kN/m {dir_txt} "
                f"de x = {a:.2f} m a x = {b:.2f} m"
            )

        if load_type == LoadType.TRIANGULAR:
            w0 = self._tri_w_start.value()
            w1 = self._tri_w_end.value()
            a = self._tri_start.value()
            b = self._tri_end.value()
            direction = self._tri_direction.currentData()
            dir_txt = "hacia abajo" if direction == LoadDirection.DOWN else "hacia arriba"
            return (
                f"Carga triangular de {w0:.2f} a {w1:.2f} kN/m {dir_txt} "
                f"de x = {a:.2f} m a x = {b:.2f} m"
            )

        if load_type == LoadType.TRAPEZOIDAL:
            w0 = self._trap_w_start.value()
            w1 = self._trap_w_end.value()
            a = self._trap_start.value()
            b = self._trap_end.value()
            direction = self._trap_direction.currentData()
            dir_txt = "hacia abajo" if direction == LoadDirection.DOWN else "hacia arriba"
            return (
                f"Carga trapezoidal de {w0:.2f} a {w1:.2f} kN/m {dir_txt} "
                f"de x = {a:.2f} m a x = {b:.2f} m"
            )

        if load_type == LoadType.MOMENT:
            mag = self._mom_magnitude.value()
            pos = self._mom_position.value()
            md = self._mom_direction.currentData()
            dir_txt = "horario" if md == MomentDirection.CLOCKWISE else "antihorario"
            return f"Momento de {mag:.2f} kN·m ({dir_txt}) en x = {pos:.2f} m"

        if load_type == LoadType.INCLINED:
            mag = self._incl_magnitude.value()
            pos = self._incl_position.value()
            ang = self._incl_angle.value()
            return (
                f"Carga inclinada de {mag:.2f} kN a {ang:.1f}° "
                f"en x = {pos:.2f} m"
            )

        return ""

    # ── Poblar desde datos existentes ─────────────────────────────────

    def _populate_from_data(self, data: LoadData) -> None:
        """Rellena los campos con datos de una carga existente (modo edición)."""
        idx = self._combo_type.findData(data.load_type)
        if idx >= 0:
            self._combo_type.setCurrentIndex(idx)

        if data.load_type == LoadType.POINT:
            self._point_magnitude.setValue(data.magnitude)
            self._point_position.setValue(data.position)
            dir_enum = LoadDirection.UP if data.direction == "up" else LoadDirection.DOWN
            dir_idx = self._point_direction.findData(dir_enum)
            if dir_idx >= 0:
                self._point_direction.setCurrentIndex(dir_idx)

        elif data.load_type == LoadType.DISTRIBUTED:
            self._dist_intensity.setValue(data.w_start)
            self._dist_start.setValue(data.start)
            self._dist_end.setValue(data.end)
            dir_enum = LoadDirection.UP if data.direction == "up" else LoadDirection.DOWN
            dir_idx = self._dist_direction.findData(dir_enum)
            if dir_idx >= 0:
                self._dist_direction.setCurrentIndex(dir_idx)

        elif data.load_type == LoadType.TRIANGULAR:
            self._tri_w_start.setValue(data.w_start)
            self._tri_w_end.setValue(data.w_end)
            self._tri_start.setValue(data.start)
            self._tri_end.setValue(data.end)
            dir_enum = LoadDirection.UP if data.direction == "up" else LoadDirection.DOWN
            dir_idx = self._tri_direction.findData(dir_enum)
            if dir_idx >= 0:
                self._tri_direction.setCurrentIndex(dir_idx)

        elif data.load_type == LoadType.TRAPEZOIDAL:
            self._trap_w_start.setValue(data.w_start)
            self._trap_w_end.setValue(data.w_end)
            self._trap_start.setValue(data.start)
            self._trap_end.setValue(data.end)
            dir_enum = LoadDirection.UP if data.direction == "up" else LoadDirection.DOWN
            dir_idx = self._trap_direction.findData(dir_enum)
            if dir_idx >= 0:
                self._trap_direction.setCurrentIndex(dir_idx)

        elif data.load_type == LoadType.MOMENT:
            self._mom_magnitude.setValue(data.magnitude)
            self._mom_position.setValue(data.position)
            md = (
                MomentDirection.CLOCKWISE
                if data.moment_direction == "clockwise"
                else MomentDirection.COUNTERCLOCKWISE
            )
            md_idx = self._mom_direction.findData(md)
            if md_idx >= 0:
                self._mom_direction.setCurrentIndex(md_idx)

        elif data.load_type == LoadType.INCLINED:
            self._incl_magnitude.setValue(data.magnitude)
            self._incl_position.setValue(data.position)
            self._incl_angle.setValue(data.angle)

    # ── Validación ────────────────────────────────────────────────────

    def _validate(self) -> list[str]:
        """Valida los datos ingresados y devuelve errores encontrados."""
        errors: list[str] = []
        load_type = self._combo_type.currentData()

        if load_type == LoadType.POINT:
            if self._point_magnitude.value() <= 0:
                errors.append("La magnitud de la carga puntual debe ser positiva.")
            if not 0 <= self._point_position.value() <= self._beam_length:
                errors.append(
                    f"La posición debe estar entre 0 y {self._beam_length:.2f} m."
                )

        elif load_type == LoadType.DISTRIBUTED:
            if self._dist_intensity.value() <= 0:
                errors.append("La intensidad debe ser positiva.")
            if self._dist_start.value() >= self._dist_end.value():
                errors.append("La posición de inicio debe ser menor que la de fin.")
            if self._dist_start.value() < 0 or self._dist_end.value() > self._beam_length:
                errors.append(
                    f"Las posiciones deben estar entre 0 y {self._beam_length:.2f} m."
                )

        elif load_type == LoadType.TRIANGULAR:
            if self._tri_w_start.value() == 0 and self._tri_w_end.value() == 0:
                errors.append("Al menos una intensidad debe ser distinta de cero.")
            if self._tri_start.value() >= self._tri_end.value():
                errors.append("La posición de inicio debe ser menor que la de fin.")
            if self._tri_start.value() < 0 or self._tri_end.value() > self._beam_length:
                errors.append(
                    f"Las posiciones deben estar entre 0 y {self._beam_length:.2f} m."
                )

        elif load_type == LoadType.TRAPEZOIDAL:
            if self._trap_w_start.value() <= 0 or self._trap_w_end.value() <= 0:
                errors.append("Ambas intensidades deben ser positivas.")
            if self._trap_start.value() >= self._trap_end.value():
                errors.append("La posición de inicio debe ser menor que la de fin.")
            if self._trap_start.value() < 0 or self._trap_end.value() > self._beam_length:
                errors.append(
                    f"Las posiciones deben estar entre 0 y {self._beam_length:.2f} m."
                )

        elif load_type == LoadType.MOMENT:
            if self._mom_magnitude.value() <= 0:
                errors.append("La magnitud del momento debe ser positiva.")
            if not 0 <= self._mom_position.value() <= self._beam_length:
                errors.append(
                    f"La posición debe estar entre 0 y {self._beam_length:.2f} m."
                )

        elif load_type == LoadType.INCLINED:
            if self._incl_magnitude.value() <= 0:
                errors.append("La magnitud de la fuerza debe ser positiva.")
            if not 0 <= self._incl_position.value() <= self._beam_length:
                errors.append(
                    f"La posición debe estar entre 0 y {self._beam_length:.2f} m."
                )

        return errors

    # ── Recopilar datos ───────────────────────────────────────────────

    def _collect_data(self) -> LoadData:
        """Recopila los datos del formulario activo y devuelve un LoadData."""
        load_type: LoadType = self._combo_type.currentData()

        if load_type == LoadType.POINT:
            direction = self._point_direction.currentData()
            return LoadData(
                load_type=load_type,
                magnitude=self._point_magnitude.value(),
                position=self._point_position.value(),
                direction="up" if direction == LoadDirection.UP else "down",
                description=self._generate_description(load_type),
            )

        if load_type == LoadType.DISTRIBUTED:
            direction = self._dist_direction.currentData()
            return LoadData(
                load_type=load_type,
                w_start=self._dist_intensity.value(),
                w_end=self._dist_intensity.value(),
                start=self._dist_start.value(),
                end=self._dist_end.value(),
                direction="up" if direction == LoadDirection.UP else "down",
                description=self._generate_description(load_type),
            )

        if load_type == LoadType.TRIANGULAR:
            direction = self._tri_direction.currentData()
            return LoadData(
                load_type=load_type,
                w_start=self._tri_w_start.value(),
                w_end=self._tri_w_end.value(),
                start=self._tri_start.value(),
                end=self._tri_end.value(),
                direction="up" if direction == LoadDirection.UP else "down",
                description=self._generate_description(load_type),
            )

        if load_type == LoadType.TRAPEZOIDAL:
            direction = self._trap_direction.currentData()
            return LoadData(
                load_type=load_type,
                w_start=self._trap_w_start.value(),
                w_end=self._trap_w_end.value(),
                start=self._trap_start.value(),
                end=self._trap_end.value(),
                direction="up" if direction == LoadDirection.UP else "down",
                description=self._generate_description(load_type),
            )

        if load_type == LoadType.MOMENT:
            md = self._mom_direction.currentData()
            return LoadData(
                load_type=load_type,
                magnitude=self._mom_magnitude.value(),
                position=self._mom_position.value(),
                moment_direction=(
                    "clockwise" if md == MomentDirection.CLOCKWISE else "counterclockwise"
                ),
                description=self._generate_description(load_type),
            )

        # INCLINED
        return LoadData(
            load_type=load_type,
            magnitude=self._incl_magnitude.value(),
            position=self._incl_position.value(),
            angle=self._incl_angle.value(),
            description=self._generate_description(load_type),
        )

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
        self._result_data = self._collect_data()
        self.accept()

    # ── API pública ───────────────────────────────────────────────────

    def get_load_data(self) -> Optional[LoadData]:
        """
        Devuelve los datos de la carga configurada.

        Returns
        -------
        LoadData | None
            Los datos si el diálogo fue aceptado, ``None`` en caso contrario.
        """
        return self._result_data
