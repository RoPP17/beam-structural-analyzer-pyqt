"""
Diálogo de preferencias de la aplicación BeamAnalyzer.

Permite configurar el tema visual, unidades por defecto, intervalo de
auto-guardado y opciones de estilo de diagramas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


# ──────────────────────────────────────────────────────────────────────
# Modelo de preferencias
# ──────────────────────────────────────────────────────────────────────

@dataclass
class AppPreferences:
    """Estructura con todas las preferencias de la aplicación."""

    # Apariencia
    theme: str = "Oscuro"
    font_size: int = 12
    show_grid: bool = True

    # Unidades por defecto
    default_length_unit: str = "m"
    default_force_unit: str = "kN"
    default_moment_unit: str = "kN·m"
    default_stress_unit: str = "MPa"

    # Auto-guardado
    auto_save_enabled: bool = True
    auto_save_interval_min: int = 5

    # Diagramas
    diagram_line_width: int = 2
    diagram_show_values: bool = True
    diagram_show_fill: bool = True
    diagram_color_shear: str = "#58a6ff"
    diagram_color_moment: str = "#f78166"
    diagram_decimal_places: int = 2


# ──────────────────────────────────────────────────────────────────────
# Diálogo
# ──────────────────────────────────────────────────────────────────────

class PreferencesDialog(QDialog):
    """Diálogo de preferencias generales de la aplicación."""

    _THEMES = ["Oscuro", "Claro"]
    _LENGTH_UNITS = ["m", "cm", "mm", "ft"]
    _FORCE_UNITS = ["kN", "N", "lbf", "kgf"]
    _MOMENT_UNITS = ["kN·m", "N·m", "lbf·ft"]
    _STRESS_UNITS = ["MPa", "GPa", "Pa", "ksi"]
    _SHEAR_COLORS = {
        "Azul": "#58a6ff",
        "Verde": "#3fb950",
        "Rojo": "#f85149",
        "Amarillo": "#d29922",
        "Púrpura": "#bc8cff",
    }
    _MOMENT_COLORS = {
        "Naranja": "#f78166",
        "Verde": "#3fb950",
        "Rojo": "#f85149",
        "Azul": "#58a6ff",
        "Púrpura": "#bc8cff",
    }

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        current_prefs: Optional[AppPreferences] = None,
    ) -> None:
        """
        Crea el diálogo de preferencias.

        Parameters
        ----------
        parent : QWidget | None
            Widget padre.
        current_prefs : AppPreferences | None
            Preferencias actuales para rellenar los campos.
        """
        super().__init__(parent)
        self.setWindowTitle("Preferencias")
        self.setMinimumSize(500, 480)
        self.setModal(True)

        self._prefs = current_prefs or AppPreferences()
        self._result_prefs: Optional[AppPreferences] = None

        self._build_ui()
        self._populate()

    # ── Construcción de UI ────────────────────────────────────────────

    def _build_ui(self) -> None:
        """Construye la interfaz con pestañas."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)

        # Título
        title = QLabel("Preferencias")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        # Pestañas
        self._tabs = QTabWidget()

        self._tabs.addTab(self._build_appearance_tab(), "Apariencia")
        self._tabs.addTab(self._build_units_tab(), "Unidades")
        self._tabs.addTab(self._build_autosave_tab(), "Guardado")
        self._tabs.addTab(self._build_diagrams_tab(), "Diagramas")

        main_layout.addWidget(self._tabs)

        # Botones
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.RestoreDefaults
        )
        button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Aceptar")
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        button_box.button(
            QDialogButtonBox.StandardButton.RestoreDefaults
        ).setText("Restaurar por defecto")

        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        button_box.button(
            QDialogButtonBox.StandardButton.RestoreDefaults
        ).clicked.connect(self._restore_defaults)

        main_layout.addWidget(button_box)

    def _build_appearance_tab(self) -> QWidget:
        """Pestaña de apariencia visual."""
        page = QWidget()
        layout = QVBoxLayout(page)

        group = QGroupBox("Tema Visual")
        form = QFormLayout(group)

        self._combo_theme = QComboBox()
        self._combo_theme.addItems(self._THEMES)
        form.addRow("Tema:", self._combo_theme)

        self._spin_font_size = QSpinBox()
        self._spin_font_size.setRange(8, 24)
        self._spin_font_size.setSuffix(" pt")
        form.addRow("Tamaño de fuente:", self._spin_font_size)

        self._chk_grid = QCheckBox("Mostrar cuadrícula en el lienzo")
        form.addRow(self._chk_grid)

        layout.addWidget(group)
        layout.addStretch()
        return page

    def _build_units_tab(self) -> QWidget:
        """Pestaña de unidades por defecto."""
        page = QWidget()
        layout = QVBoxLayout(page)

        group = QGroupBox("Unidades por Defecto")
        form = QFormLayout(group)

        self._combo_length = QComboBox()
        self._combo_length.addItems(self._LENGTH_UNITS)
        form.addRow("Longitud:", self._combo_length)

        self._combo_force = QComboBox()
        self._combo_force.addItems(self._FORCE_UNITS)
        form.addRow("Fuerza:", self._combo_force)

        self._combo_moment = QComboBox()
        self._combo_moment.addItems(self._MOMENT_UNITS)
        form.addRow("Momento:", self._combo_moment)

        self._combo_stress = QComboBox()
        self._combo_stress.addItems(self._STRESS_UNITS)
        form.addRow("Esfuerzo:", self._combo_stress)

        layout.addWidget(group)
        layout.addStretch()
        return page

    def _build_autosave_tab(self) -> QWidget:
        """Pestaña de auto-guardado."""
        page = QWidget()
        layout = QVBoxLayout(page)

        group = QGroupBox("Auto-Guardado")
        form = QFormLayout(group)

        self._chk_autosave = QCheckBox("Habilitar auto-guardado")
        form.addRow(self._chk_autosave)

        self._spin_autosave = QSpinBox()
        self._spin_autosave.setRange(1, 60)
        self._spin_autosave.setSuffix(" min")
        self._spin_autosave.setToolTip("Intervalo de auto-guardado en minutos")
        form.addRow("Intervalo:", self._spin_autosave)

        self._chk_autosave.toggled.connect(self._spin_autosave.setEnabled)

        layout.addWidget(group)
        layout.addStretch()
        return page

    def _build_diagrams_tab(self) -> QWidget:
        """Pestaña de estilo de diagramas."""
        page = QWidget()
        layout = QVBoxLayout(page)

        group = QGroupBox("Estilo de Diagramas")
        form = QFormLayout(group)

        self._spin_line_width = QSpinBox()
        self._spin_line_width.setRange(1, 6)
        self._spin_line_width.setSuffix(" px")
        form.addRow("Grosor de línea:", self._spin_line_width)

        self._chk_show_values = QCheckBox("Mostrar valores en diagramas")
        form.addRow(self._chk_show_values)

        self._chk_show_fill = QCheckBox("Rellenar área bajo las curvas")
        form.addRow(self._chk_show_fill)

        self._combo_shear_color = QComboBox()
        for name, hex_val in self._SHEAR_COLORS.items():
            self._combo_shear_color.addItem(name, hex_val)
        form.addRow("Color cortante:", self._combo_shear_color)

        self._combo_moment_color = QComboBox()
        for name, hex_val in self._MOMENT_COLORS.items():
            self._combo_moment_color.addItem(name, hex_val)
        form.addRow("Color momento:", self._combo_moment_color)

        self._spin_decimals = QSpinBox()
        self._spin_decimals.setRange(0, 6)
        form.addRow("Decimales:", self._spin_decimals)

        layout.addWidget(group)
        layout.addStretch()
        return page

    # ── Poblar campos ─────────────────────────────────────────────────

    def _populate(self) -> None:
        """Rellena todos los campos con las preferencias actuales."""
        p = self._prefs

        # Apariencia
        idx = self._combo_theme.findText(p.theme)
        if idx >= 0:
            self._combo_theme.setCurrentIndex(idx)
        self._spin_font_size.setValue(p.font_size)
        self._chk_grid.setChecked(p.show_grid)

        # Unidades
        self._set_combo_text(self._combo_length, p.default_length_unit)
        self._set_combo_text(self._combo_force, p.default_force_unit)
        self._set_combo_text(self._combo_moment, p.default_moment_unit)
        self._set_combo_text(self._combo_stress, p.default_stress_unit)

        # Auto-guardado
        self._chk_autosave.setChecked(p.auto_save_enabled)
        self._spin_autosave.setValue(p.auto_save_interval_min)
        self._spin_autosave.setEnabled(p.auto_save_enabled)

        # Diagramas
        self._spin_line_width.setValue(p.diagram_line_width)
        self._chk_show_values.setChecked(p.diagram_show_values)
        self._chk_show_fill.setChecked(p.diagram_show_fill)
        self._set_combo_data(self._combo_shear_color, p.diagram_color_shear)
        self._set_combo_data(self._combo_moment_color, p.diagram_color_moment)
        self._spin_decimals.setValue(p.diagram_decimal_places)

    @staticmethod
    def _set_combo_text(combo: QComboBox, text: str) -> None:
        """Selecciona un item del combo por texto."""
        idx = combo.findText(text)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    @staticmethod
    def _set_combo_data(combo: QComboBox, data: str) -> None:
        """Selecciona un item del combo por data."""
        idx = combo.findData(data)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    # ── Restaurar por defecto ─────────────────────────────────────────

    def _restore_defaults(self) -> None:
        """Restaura todas las preferencias a los valores por defecto."""
        self._prefs = AppPreferences()
        self._populate()

    # ── Recopilar preferencias ────────────────────────────────────────

    def _collect_prefs(self) -> AppPreferences:
        """Recopila los valores de todos los campos."""
        return AppPreferences(
            theme=self._combo_theme.currentText(),
            font_size=self._spin_font_size.value(),
            show_grid=self._chk_grid.isChecked(),
            default_length_unit=self._combo_length.currentText(),
            default_force_unit=self._combo_force.currentText(),
            default_moment_unit=self._combo_moment.currentText(),
            default_stress_unit=self._combo_stress.currentText(),
            auto_save_enabled=self._chk_autosave.isChecked(),
            auto_save_interval_min=self._spin_autosave.value(),
            diagram_line_width=self._spin_line_width.value(),
            diagram_show_values=self._chk_show_values.isChecked(),
            diagram_show_fill=self._chk_show_fill.isChecked(),
            diagram_color_shear=self._combo_shear_color.currentData() or "#58a6ff",
            diagram_color_moment=self._combo_moment_color.currentData() or "#f78166",
            diagram_decimal_places=self._spin_decimals.value(),
        )

    # ── Aceptar ───────────────────────────────────────────────────────

    def _on_accept(self) -> None:
        """Acepta el diálogo y guarda las preferencias."""
        self._result_prefs = self._collect_prefs()
        self.accept()

    # ── API pública ───────────────────────────────────────────────────

    def get_preferences(self) -> Optional[AppPreferences]:
        """
        Devuelve las preferencias configuradas.

        Returns
        -------
        AppPreferences | None
            Las preferencias si se aceptó el diálogo, ``None`` si se canceló.
        """
        return self._result_prefs
