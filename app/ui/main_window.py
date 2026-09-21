"""
main_window.py - Ventana principal de la aplicación.
"""

import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QSplitter, QDockWidget, QStatusBar, QMessageBox, QFileDialog, QTabWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction

from app.controllers.app_controller import AppController
from app.ui.beam_canvas import BeamScene, BeamCanvas
from app.ui.toolbar_panel import ToolbarPanel
from app.ui.property_panel import PropertyPanel
from app.ui.report_panel import ReportPanel
from app.ui.dialogs.beam_dialog import BeamDialog
from app.ui.element_table_panel import ElementTablePanel
from app.ui.dialogs.element_dialogs import (
    SupportDialog, PointLoadDialog, DistributedLoadDialog, MomentDialog, InclinedLoadDialog
)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RM Calculadora de Momentos y Cortantes")
        self.setMinimumSize(1200, 800)
        
        # Controller
        self.controller = AppController(self)
        
        # UI Setup
        self._setup_ui()
        self._connect_signals()
        
        # Start empty
        self._prompt_new_beam()
        
    def _setup_ui(self):
        # Top toolbar (QToolBar for general actions)
        self.top_toolbar = self.addToolBar("General")
        self.action_new = QAction("Nueva Viga", self)
        self.top_toolbar.addAction(self.action_new)
        self.action_solve = QAction("Resolver Análisis", self)
        self.top_toolbar.addAction(self.action_solve)
        
        # Central widget and layout
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #30363d; border-radius: 4px; }
            QTabBar::tab { background: #161b22; color: #8b949e; padding: 10px 20px; border: 1px solid #30363d; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background: #0d1117; color: #58a6ff; font-weight: bold; border-bottom-color: #0d1117; }
            QTabBar::tab:hover { background: #21262d; }
        """)
        self.setCentralWidget(self.tabs)
        
        # --- TAB 1: MODELADO ---
        self.tab_modelado = QWidget()
        modelado_layout = QHBoxLayout(self.tab_modelado)
        modelado_layout.setContentsMargins(0, 0, 0, 0)
        
        # Left toolbar (tools)
        self.toolbar = ToolbarPanel()
        modelado_layout.addWidget(self.toolbar)
        
        # Canvas
        self.scene = BeamScene(self)
        self.canvas = BeamCanvas(self.scene, self)
        modelado_layout.addWidget(self.canvas)
        
        self.controller.set_scene(self.scene, self.canvas)
        
        self.tabs.addTab(self.tab_modelado, "Modelado de la Viga")
        
        # --- TAB 2: RESULTADOS ---
        self.tab_resultados = QWidget()
        resultados_layout = QVBoxLayout(self.tab_resultados)
        resultados_layout.setContentsMargins(0, 0, 0, 0)
        
        self.report_panel = ReportPanel(self)
        resultados_layout.addWidget(self.report_panel)
        
        self.tabs.addTab(self.tab_resultados, "Resultados y Diagramas")
        
        # Left Dock: Properties and Table
        self.right_dock = QDockWidget("Controles y Elementos", self)
        
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        self.property_panel = PropertyPanel()
        right_layout.addWidget(self.property_panel)
        
        self.table_panel = ElementTablePanel()
        right_layout.addWidget(self.table_panel)
        
        self.right_dock.setWidget(right_container)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.right_dock)
        
        # Status Bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Listo")
        
    def _connect_signals(self):
        # Actions
        self.action_new.triggered.connect(self._prompt_new_beam)
        self.action_solve.triggered.connect(self.controller.solve)
        
        self.toolbar.tool_selected.connect(self._on_tool_selected)
        
        # Table
        self.table_panel.delete_requested.connect(self.controller.delete_element_by_index)
        self.table_panel.edit_requested.connect(self._on_element_edit_requested)
        
        # Controller
        # Controller signals mapping
        self.controller.status_message.connect(self.status.showMessage)
        self.controller.validation_errors.connect(self._show_errors)
        self.controller.model_changed.connect(self.table_panel.update_table)
        self.controller.model_changed.connect(lambda x: self.report_panel.clear_report())
        self.controller.model_cleared.connect(self.report_panel.clear_report)
        # Using deflection_ready because it's the last step in the solver pipeline
        self.controller.deflection_ready.connect(self._on_analysis_complete)
        
        # Canvas
        self.scene.element_selected.connect(self._on_element_selected)
        
    def _prompt_new_beam(self):
        dialog = BeamDialog(self)
        if dialog.exec():
            params = dialog.get_parameters()
            if params:
                self.controller.create_beam(params.length)
                self.controller.get_beam().E = params.elastic_modulus
                self.controller.get_beam().I = params.moment_of_inertia
                self.canvas.zoom_to_fit()
                self.table_panel.update_table(self.controller.get_beam())
            
    def _on_tool_selected(self, tool_name: str):
        # Deselect tool visually since we don't hold state
        self.toolbar._button_group.setExclusive(False)
        for btn in self.toolbar._buttons.values():
            btn.setChecked(False)
        self.toolbar._button_group.setExclusive(True)
        
        beam_len = self.controller.get_beam().length
        
        dialog = None
        if tool_name in ["pinned_support", "roller_support", "fixed_support"]:
            dialog = SupportDialog(beam_len, tool_name, self)
        elif tool_name == "point_load":
            dialog = PointLoadDialog(beam_len, self)
        elif tool_name in ["distributed_load", "triangular_load", "trapezoidal_load"]:
            dialog = DistributedLoadDialog(beam_len, tool_name, self)
        elif tool_name == "moment":
            dialog = MomentDialog(beam_len, self)
        elif tool_name == "inclined_load":
            dialog = InclinedLoadDialog(beam_len, self)
        elif tool_name == "delete":
            # For delete we can just rely on the table panel now, or clear canvas selection
            pass
            
        if dialog and dialog.exec():
            data = dialog.get_data()
            self.controller.add_element(data["type"], data)
            
    def _on_element_edit_requested(self, group: str, idx: int):
        elem = self.controller.get_element_by_index(group, idx)
        if not elem:
            return
            
        data = elem.to_dict()
        beam_len = self.controller.get_beam().length
        
        dialog = None
        if group == "support":
            dialog = SupportDialog(beam_len, "", self)
        elif group == "load":
            t = data.get("load_type", "")
            if t == "point":
                dialog = PointLoadDialog(beam_len, self)
            elif t in ("distributed_uniform", "triangular", "trapezoidal"):
                if t == "distributed_uniform":
                    data["type"] = "distributed"
                elif t == "triangular":
                    data["type"] = "triangular"
                else:
                    data["type"] = "trapezoidal"
                dialog = DistributedLoadDialog(beam_len, "", self)
            elif t == "moment":
                dialog = MomentDialog(beam_len, self)
            elif t == "inclined":
                dialog = InclinedLoadDialog(beam_len, self)
                
        if dialog:
            # Re-map load_type to type for dialog consistency
            if "load_type" in data and "type" not in data:
                data["type"] = data["load_type"]
            # For supports, support_type to type
            if "support_type" in data and "type" not in data:
                val = data["support_type"]
                if val == "pinned_support" or val == 1: # if enum
                    data["type"] = "pinned"
                elif val == "roller_support" or val == 2:
                    data["type"] = "roller"
                elif val == "fixed_support" or val == 3:
                    data["type"] = "fixed"
            
            # Map enum values safely
            if hasattr(data.get("support_type", None), "value"):
                 val = data["support_type"].value
                 if "pinned" in str(val).lower(): data["type"] = "pinned"
                 elif "roller" in str(val).lower(): data["type"] = "roller"
                 elif "fixed" in str(val).lower(): data["type"] = "fixed"

            dialog.set_data(data)
            if dialog.exec():
                new_data = dialog.get_data()
                self.controller.update_element_by_index(group, idx, new_data)

    def _on_element_selected(self, item):
        pass # self.property_panel.set_item(item)
        
    def _on_analysis_complete(self, deflection):
        # Todos los resultados están listos en el controller
        beam = self.controller.get_beam()
        solution = self.controller.get_solution()
        forces = self.controller.get_forces()
        equations = self.controller.get_equations()
        critical = self.controller.get_critical_report()
        
        if all([beam, solution, forces, equations, critical]):
            self.report_panel.update_report(beam, solution, forces, equations, critical)
            self.tabs.setCurrentIndex(1)
        
    def _show_errors(self, errors):
        msgs = "\\n".join([e.message for e in errors])
        QMessageBox.warning(self, "Errores de Validación", msgs)
        
    def apply_theme(self, theme_path: str):
        if os.path.exists(theme_path):
            with open(theme_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
