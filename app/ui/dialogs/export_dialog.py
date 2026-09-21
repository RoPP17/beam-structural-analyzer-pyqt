"""
Diálogo de exportación para BeamAnalyzer.

Permite seleccionar el formato de exportación (PDF, PNG, SVG, JSON)
y configurar opciones específicas de cada formato, como secciones
a incluir en el reporte PDF e información del estudiante.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


# ──────────────────────────────────────────────────────────────────────
# Enumeraciones y datos
# ──────────────────────────────────────────────────────────────────────

class ExportFormat(Enum):
    """Formatos de exportación disponibles."""

    PDF = "Reporte PDF"
    PNG = "Imagen PNG"
    SVG = "Imagen SVG"
    JSON = "Proyecto JSON"


_FORMAT_EXTENSIONS: dict[ExportFormat, str] = {
    ExportFormat.PDF: ".pdf",
    ExportFormat.PNG: ".png",
    ExportFormat.SVG: ".svg",
    ExportFormat.JSON: ".json",
}

_FORMAT_FILTERS: dict[ExportFormat, str] = {
    ExportFormat.PDF: "Archivos PDF (*.pdf)",
    ExportFormat.PNG: "Imágenes PNG (*.png)",
    ExportFormat.SVG: "Imágenes SVG (*.svg)",
    ExportFormat.JSON: "Archivos JSON (*.json)",
}


@dataclass
class ExportOptions:
    """Opciones de exportación configuradas por el usuario."""

    export_format: ExportFormat = ExportFormat.PDF
    file_path: str = ""

    # Opciones PDF
    include_cover: bool = True
    include_data: bool = True
    include_diagrams: bool = True
    include_calculations: bool = True
    include_conclusions: bool = True

    # Información del estudiante (para PDF)
    student_name: str = ""
    student_id: str = ""
    course_name: str = "Resistencia de Materiales"
    professor_name: str = ""


# ──────────────────────────────────────────────────────────────────────
# Diálogo
# ──────────────────────────────────────────────────────────────────────

class ExportDialog(QDialog):
    """Diálogo para configurar la exportación del análisis."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        default_filename: str = "beam_analysis",
    ) -> None:
        """
        Crea el diálogo de exportación.

        Parameters
        ----------
        parent : QWidget | None
            Widget padre.
        default_filename : str
            Nombre de archivo sugerido (sin extensión).
        """
        super().__init__(parent)
        self.setWindowTitle("Exportar")
        self.setMinimumWidth(560)
        self.setModal(True)

        self._default_filename = default_filename
        self._result_options: Optional[ExportOptions] = None

        self._build_ui()
        self._connect_signals()
        self._on_format_changed()

    # ── Construcción de UI ────────────────────────────────────────────

    def _build_ui(self) -> None:
        """Construye la interfaz del diálogo."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)

        # Título
        title = QLabel("Exportar")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        # ── Formato ──────────────────────────────────────────────────
        format_group = QGroupBox("Formato de Exportación")
        format_layout = QFormLayout(format_group)

        self._combo_format = QComboBox()
        for fmt in ExportFormat:
            self._combo_format.addItem(fmt.value, fmt)
        format_layout.addRow("Formato:", self._combo_format)

        main_layout.addWidget(format_group)

        # ── Ruta del archivo ──────────────────────────────────────────
        path_group = QGroupBox("Destino")
        path_layout = QHBoxLayout(path_group)

        self._edit_path = QLineEdit()
        self._edit_path.setPlaceholderText("Seleccionar ubicación del archivo...")
        self._edit_path.setReadOnly(True)
        path_layout.addWidget(self._edit_path, stretch=3)

        self._btn_browse = QPushButton("Examinar…")
        self._btn_browse.clicked.connect(self._browse_file)
        path_layout.addWidget(self._btn_browse, stretch=1)

        main_layout.addWidget(path_group)

        # ── Opciones apiladas ─────────────────────────────────────────
        self._stacked = QStackedWidget()
        self._stacked.addWidget(self._build_pdf_options())
        self._stacked.addWidget(self._build_image_options())
        self._stacked.addWidget(self._build_json_options())
        main_layout.addWidget(self._stacked)

        # ── Botones ──────────────────────────────────────────────────
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Exportar")
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

    def _build_pdf_options(self) -> QWidget:
        """Opciones específicas para exportación PDF."""
        page = QWidget()
        layout = QVBoxLayout(page)

        # Secciones a incluir
        sections_group = QGroupBox("Secciones del Reporte")
        sec_layout = QVBoxLayout(sections_group)

        self._chk_cover = QCheckBox("Portada")
        self._chk_cover.setChecked(True)
        sec_layout.addWidget(self._chk_cover)

        self._chk_data = QCheckBox("Datos del problema")
        self._chk_data.setChecked(True)
        sec_layout.addWidget(self._chk_data)

        self._chk_diagrams = QCheckBox("Diagramas (cortante y momento)")
        self._chk_diagrams.setChecked(True)
        sec_layout.addWidget(self._chk_diagrams)

        self._chk_calcs = QCheckBox("Cálculos paso a paso")
        self._chk_calcs.setChecked(True)
        sec_layout.addWidget(self._chk_calcs)

        self._chk_conclusions = QCheckBox("Conclusiones")
        self._chk_conclusions.setChecked(True)
        sec_layout.addWidget(self._chk_conclusions)

        layout.addWidget(sections_group)

        # Información del estudiante
        student_group = QGroupBox("Información del Estudiante")
        student_layout = QFormLayout(student_group)

        self._edit_student_name = QLineEdit()
        self._edit_student_name.setPlaceholderText("Nombre completo")
        student_layout.addRow("Nombre:", self._edit_student_name)

        self._edit_student_id = QLineEdit()
        self._edit_student_id.setPlaceholderText("Ej: 1804123456")
        student_layout.addRow("Cédula / ID:", self._edit_student_id)

        self._edit_course = QLineEdit("Resistencia de Materiales")
        student_layout.addRow("Asignatura:", self._edit_course)

        self._edit_professor = QLineEdit()
        self._edit_professor.setPlaceholderText("Nombre del docente")
        student_layout.addRow("Docente:", self._edit_professor)

        layout.addWidget(student_group)

        return page

    def _build_image_options(self) -> QWidget:
        """Opciones para exportación de imagen (PNG/SVG)."""
        page = QWidget()
        layout = QVBoxLayout(page)

        info = QLabel(
            "📷 Se exportará una captura del estado actual de los diagramas.\n"
            "La imagen incluirá todos los diagramas visibles en la vista principal."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #8b949e; font-size: 12px; padding: 12px;")
        layout.addWidget(info)
        layout.addStretch()

        return page

    def _build_json_options(self) -> QWidget:
        """Opciones para exportación de proyecto JSON."""
        page = QWidget()
        layout = QVBoxLayout(page)

        info = QLabel(
            "💾 Se exportará el proyecto completo en formato JSON.\n"
            "Incluye la configuración de la viga, apoyos, cargas y metadatos.\n"
            "El archivo puede importarse posteriormente para continuar el análisis."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #8b949e; font-size: 12px; padding: 12px;")
        layout.addWidget(info)
        layout.addStretch()

        return page

    # ── Señales ───────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        """Conecta señales de los widgets."""
        self._combo_format.currentIndexChanged.connect(self._on_format_changed)

    def _on_format_changed(self) -> None:
        """Cambia las opciones visibles según el formato seleccionado."""
        fmt: ExportFormat = self._combo_format.currentData()
        if fmt == ExportFormat.PDF:
            self._stacked.setCurrentIndex(0)
        elif fmt in (ExportFormat.PNG, ExportFormat.SVG):
            self._stacked.setCurrentIndex(1)
        elif fmt == ExportFormat.JSON:
            self._stacked.setCurrentIndex(2)

        # Limpiar ruta al cambiar formato
        self._edit_path.clear()

    # ── Seleccionar archivo ───────────────────────────────────────────

    def _browse_file(self) -> None:
        """Abre un diálogo para seleccionar la ruta del archivo de destino."""
        fmt: ExportFormat = self._combo_format.currentData()
        ext = _FORMAT_EXTENSIONS[fmt]
        file_filter = _FORMAT_FILTERS[fmt]

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Seleccionar destino",
            f"{self._default_filename}{ext}",
            file_filter,
        )
        if path:
            if not path.lower().endswith(ext):
                path += ext
            self._edit_path.setText(path)

    # ── Validación ────────────────────────────────────────────────────

    def _validate(self) -> list[str]:
        """Valida las opciones de exportación."""
        errors: list[str] = []

        if not self._edit_path.text().strip():
            errors.append("Debe seleccionar una ruta de destino para el archivo.")

        fmt: ExportFormat = self._combo_format.currentData()
        if fmt == ExportFormat.PDF:
            # Al menos una sección debe estar seleccionada
            if not any([
                self._chk_cover.isChecked(),
                self._chk_data.isChecked(),
                self._chk_diagrams.isChecked(),
                self._chk_calcs.isChecked(),
                self._chk_conclusions.isChecked(),
            ]):
                errors.append("Debe seleccionar al menos una sección para el reporte PDF.")

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

        fmt: ExportFormat = self._combo_format.currentData()

        self._result_options = ExportOptions(
            export_format=fmt,
            file_path=self._edit_path.text().strip(),
            include_cover=self._chk_cover.isChecked() if fmt == ExportFormat.PDF else True,
            include_data=self._chk_data.isChecked() if fmt == ExportFormat.PDF else True,
            include_diagrams=self._chk_diagrams.isChecked() if fmt == ExportFormat.PDF else True,
            include_calculations=self._chk_calcs.isChecked() if fmt == ExportFormat.PDF else True,
            include_conclusions=self._chk_conclusions.isChecked() if fmt == ExportFormat.PDF else True,
            student_name=self._edit_student_name.text().strip() if fmt == ExportFormat.PDF else "",
            student_id=self._edit_student_id.text().strip() if fmt == ExportFormat.PDF else "",
            course_name=self._edit_course.text().strip() if fmt == ExportFormat.PDF else "",
            professor_name=self._edit_professor.text().strip() if fmt == ExportFormat.PDF else "",
        )
        self.accept()

    # ── API pública ───────────────────────────────────────────────────

    def get_export_options(self) -> Optional[ExportOptions]:
        """
        Devuelve las opciones de exportación configuradas.

        Returns
        -------
        ExportOptions | None
            Las opciones si se aceptó, ``None`` si se canceló.
        """
        return self._result_options
