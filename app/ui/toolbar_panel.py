"""
Panel de herramientas lateral izquierdo para BeamAnalyzer.

Proporciona una barra de herramientas vertical con botones agrupados
para selección, creación de vigas, apoyos, cargas y acciones.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QLabel,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QApplication,
)



class ToolbarPanel(QWidget):
    """Panel lateral izquierdo con herramientas de edición de vigas.

    Attributes:
        tool_selected: Señal emitida cuando el usuario selecciona una
            herramienta.  Envía el nombre interno de la herramienta
            (por ejemplo ``"select"``, ``"point_load"``).
    """

    tool_selected = pyqtSignal(str)

    # ── Definición de herramientas ──────────────────────────────
    # Cada tupla: (nombre_interno, icono_unicode, etiqueta_español, tooltip)
    _TOOL_GROUPS: list[tuple[str, list[tuple[str, str, str, str]]]] = [
        (
            "",  # sin cabecera – herramientas generales
            [
                ("select", "🖱️", "Seleccionar", "Seleccionar y ver detalles"),
            ],
        ),
        (
            "Apoyos",
            [
                ("pinned_support", "📌", "Apoyo Articulado",
                 "Colocar apoyo articulado (restricción en X e Y)"),
                ("roller_support", "⚙", "Apoyo de Rodillo",
                 "Colocar apoyo de rodillo (restricción en Y)"),
                ("fixed_support", "🔒", "Empotrado",
                 "Colocar empotramiento (restricción en X, Y y momento)"),
            ],
        ),
        (
            "Cargas",
            [
                ("point_load", "⬇️", "Carga Puntual",
                 "Aplicar una carga concentrada"),
                ("distributed_load", "📊", "Carga Distribuida",
                 "Aplicar una carga uniformemente distribuida"),
                ("triangular_load", "📈", "Carga Triangular",
                 "Aplicar una carga triangular (variación lineal)"),
                ("trapezoidal_load", "📉", "Carga Trapezoidal",
                 "Aplicar una carga trapezoidal"),
                ("moment", "🔄", "Momento",
                 "Aplicar un momento puntual"),
                ("inclined_load", "↗️", "Carga Inclinada",
                 "Aplicar una carga inclinada"),
            ],
        ),
    ]

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("toolbarPanel")
        self.setMinimumWidth(180)
        self.setMaximumWidth(220)

        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)
        self._buttons: dict[str, QToolButton] = {}

        self._setup_ui()
        self._connect_signals()

        # Seleccionar la herramienta "select" por defecto
        if "select" in self._buttons:
            self._buttons["select"].setChecked(True)

    # ── Construcción de la interfaz ─────────────────────────────

    def _setup_ui(self) -> None:
        """Construye la disposición del panel de herramientas."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 12)
        layout.setSpacing(2)

        # Título del panel
        title_label = QLabel("Herramientas")
        title_label.setObjectName("accentLabel")
        title_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        title_label.setStyleSheet("font-size: 15px; font-weight: bold; padding-bottom: 4px;")
        layout.addWidget(title_label)

        # Separador bajo el título
        layout.addWidget(self._create_separator())

        button_id = 0
        for group_header, tools in self._TOOL_GROUPS:
            # Cabecera de sección (si existe)
            if group_header:
                layout.addSpacing(6)
                header = QLabel(group_header.upper())
                header.setObjectName("sectionHeader")
                layout.addWidget(header)

            for tool_name, icon_text, label, tooltip in tools:
                btn = self._create_tool_button(tool_name, icon_text, label, tooltip)
                self._button_group.addButton(btn, button_id)
                self._buttons[tool_name] = btn
                layout.addWidget(btn)
                button_id += 1

            # Separador entre grupos
            layout.addWidget(self._create_separator())

        layout.addStretch()

    def _create_tool_button(
        self, tool_name: str, icon_text: str, label: str, tooltip: str
    ) -> QToolButton:
        """Crea un botón de herramienta estilizado.

        Args:
            tool_name: Nombre interno de la herramienta.
            icon_text: Emoji o carácter Unicode usado como icono.
            label: Texto visible junto al icono.
            tooltip: Descripción emergente al pasar el cursor.

        Returns:
            Un ``QToolButton`` configurado y checkable.
        """
        btn = QToolButton(self)
        btn.setObjectName("toolbarButton")
        btn.setText(f"  {icon_text}  {label}")
        btn.setToolTip(tooltip)
        btn.setCheckable(True)
        btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        btn.setSizePolicy(
            btn.sizePolicy().horizontalPolicy(),
            btn.sizePolicy().verticalPolicy(),
        )
        btn.setMinimumHeight(36)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        # Expandir horizontalmente para que ocupe todo el ancho
        btn.setFixedHeight(36)
        btn.setMinimumWidth(160)
        return btn

    @staticmethod
    def _create_separator() -> QFrame:
        """Crea un separador horizontal sutil."""
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Plain)
        sep.setFixedHeight(1)
        return sep

    # ── Señales ─────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        """Conecta las señales internas del grupo de botones."""
        self._button_group.buttonClicked.connect(self._on_button_clicked)

    def _on_button_clicked(self, button: QToolButton) -> None:
        """Despacha la señal ``tool_selected`` con el nombre de herramienta."""
        for name, btn in self._buttons.items():
            if btn is button:
                self.tool_selected.emit(name)
                return

    # ── API pública ─────────────────────────────────────────────

    def set_active_tool(self, tool_name: str) -> None:
        """Selecciona programáticamente una herramienta.

        Args:
            tool_name: Nombre interno de la herramienta (por ejemplo
                ``"select"``, ``"point_load"``).
        """
        btn = self._buttons.get(tool_name)
        if btn is not None:
            btn.setChecked(True)
            self.tool_selected.emit(tool_name)

    def get_active_tool(self) -> str:
        """Devuelve el nombre de la herramienta actualmente seleccionada.

        Returns:
            Nombre interno, o cadena vacía si ninguna está seleccionada.
        """
        for name, btn in self._buttons.items():
            if btn.isChecked():
                return name
        return ""

    def set_tool_enabled(self, tool_name: str, enabled: bool) -> None:
        """Habilita o deshabilita una herramienta específica.

        Args:
            tool_name: Nombre interno de la herramienta.
            enabled: ``True`` para habilitar, ``False`` para deshabilitar.
        """
        btn = self._buttons.get(tool_name)
        if btn is not None:
            btn.setEnabled(enabled)
