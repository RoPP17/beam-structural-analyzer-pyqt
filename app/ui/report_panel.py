"""
Panel de reporte interactivo. Reemplaza el sistema de pestañas para presentar
los resultados en un formato de informe continuo, desplazable y profesional.
"""

from typing import Optional, Sequence, List, Dict
import os
import math
import numpy as np
import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy, QPushButton, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtGui import QIcon

from app.reports.exporter import ReportExporter

from app.core.solver import SolutionResult
from app.core.equations import EquationsResult
from app.core.critical_zones import CriticalZoneReport
from app.core.internal_forces import InternalForcesResult
from app.core.deflection import DeflectionResult
from app.core.beam_model import BeamModel

# ── Estilos y Paleta (Oscura) ──────────────────────────────
_THEME = {
    "bg": "#0d1117",
    "card_bg": "#161b22",
    "border": "#30363d",
    "text_h1": "#e6edf3",
    "text_p": "#8b949e",
    "accent": "#58a6ff",
    "v_pos": "#58a6ff",
    "v_neg": "#f85149",
    "m_pos": "#3fb950",
    "m_neg": "#f0883e",
    "deflection": "#d2a8ff",
    "grid": "#21262d",
    "baseline": "#484f58",
}

class ReportCard(QFrame):
    """Tarjeta visual que agrupa una sección del reporte."""
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("reportCard")
        self.setStyleSheet(f"""
            QFrame#reportCard {{
                background-color: {_THEME['card_bg']};
                border: 1px solid {_THEME['border']};
                border-radius: 6px;
                margin-bottom: 12px;
            }}
        """)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 16, 16, 16)
        self.layout.setSpacing(12)
        
        self.title_label = QLabel(title)
        font = QFont("Segoe UI", 12, QFont.Weight.Bold)
        self.title_label.setFont(font)
        self.title_label.setStyleSheet(f"color: {_THEME['accent']}; margin-bottom: 4px;")
        self.layout.addWidget(self.title_label)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Plain)
        line.setStyleSheet(f"background-color: {_THEME['border']}; max-height: 1px;")
        self.layout.addWidget(line)

    def add_widget(self, widget: QWidget):
        self.layout.addWidget(widget)

class SingleGraphWidget(QWidget):
    """Contenedor para un gráfico individual con altura controlada."""
    def __init__(self, title: str, ylabel: str, color_pos: str, color_neg: str, invert_y: bool = False, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.figure = Figure(tight_layout=True)
        self.figure.set_facecolor(_THEME["card_bg"])
        self.canvas = FigureCanvas(self.figure)
        
        # Limitar altura para que no sea excesivamente estirada
        self.canvas.setMinimumHeight(280)
        self.canvas.setMaximumHeight(350)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        self.ax = self.figure.add_subplot(111)
        self._setup_axes(title, ylabel, invert_y)
        self.layout.addWidget(self.canvas)
        
        self.color_pos = color_pos
        self.color_neg = color_neg

    def _setup_axes(self, title, ylabel, invert_y):
        ax = self.ax
        ax.set_facecolor(_THEME["card_bg"])
        ax.tick_params(colors=_THEME["text_p"], labelsize=9)
        ax.spines["bottom"].set_color(_THEME["border"])
        ax.spines["left"].set_color(_THEME["border"])
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(True, color=_THEME["grid"], linewidth=0.5, alpha=0.7)
        ax.set_ylabel(ylabel, color=_THEME["text_h1"], fontsize=10)
        if invert_y:
            ax.invert_yaxis()

    def plot_data(self, x, y, critical_pts=None, label_prefix=""):
        self.ax.clear()
        invert_y = self.ax.yaxis.get_inverted()
        self._setup_axes("", self.ax.get_ylabel(), invert_y)
        
        self.ax.axhline(0, color=_THEME["baseline"], linewidth=1, zorder=1)
        self.ax.plot(x, y, color=self.color_pos, linewidth=1.5, zorder=3)
        
        y_pos = np.where(y >= 0, y, 0)
        y_neg = np.where(y <= 0, y, 0)
        self.ax.fill_between(x, y_pos, 0, alpha=0.2, color=self.color_pos, zorder=2)
        self.ax.fill_between(x, y_neg, 0, alpha=0.2, color=self.color_neg, zorder=2)
        
        if critical_pts:
            x_arr = np.asarray(x)
            x_range = x_arr[-1] - x_arr[0] if len(x_arr) > 1 and x_arr[-1] != x_arr[0] else 1.0
            x_threshold = x_range * 0.04
            placed = []
            
            for pt in critical_pts:
                px = pt["x"]
                py = pt["y"]
                label = pt.get("label", "")
                
                dy = 15 if py >= 0 else -15
                if invert_y:
                    dy = -dy
                    
                for (lx, ldy) in placed:
                    if abs(px - lx) < x_threshold and ((dy > 0) == (ldy > 0)):
                        if abs(dy - ldy) < 15:
                            dy = ldy + (15 if dy > 0 else -15)
                
                placed.append((px, dy))
                va = "bottom" if dy >= 0 else "top"
                
                props = dict(arrowstyle="-", color=_THEME["text_h1"], lw=0.5, alpha=0.5) if abs(dy) > 20 else None

                self.ax.plot(px, py, "o", color=_THEME["text_h1"], markersize=5, zorder=5)
                ann_text = f"{py:.2f}"
                if label:
                    ann_text = f"{label} = {ann_text}"
                self.ax.annotate(
                    ann_text,
                    (px, py),
                    textcoords="offset points",
                    xytext=(0, dy),
                    fontsize=8,
                    color=_THEME["text_h1"],
                    zorder=5,
                    ha="center",
                    va=va,
                    bbox=dict(boxstyle="round,pad=0.2", facecolor=_THEME["card_bg"], edgecolor='none', alpha=0.7),
                    arrowprops=props
                )
        
        # Ampliar márgenes del eje Y
        y_min, y_max = self.ax.get_ylim()
        y_range = y_max - y_min
        if y_range > 0:
            self.ax.set_ylim(y_min - y_range * 0.35, y_max + y_range * 0.35)

        self.figure.tight_layout(pad=1.5)
        self.canvas.draw_idle()

class ReportPanel(QScrollArea):
    """Panel principal que muestra todos los resultados en un informe."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setObjectName("reportPanel")
        self.setStyleSheet(f"""
            QScrollArea#reportPanel {{
                background-color: {_THEME['bg']};
                border: none;
            }}
            QWidget#scrollContent {{
                background-color: {_THEME['bg']};
            }}
        """)
        
        self.content_widget = QWidget()
        self.content_widget.setObjectName("scrollContent")
        self.main_layout = QVBoxLayout(self.content_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(0)
        
        # Guardar estado actual
        self.current_beam = None
        self.current_solution = None
        self.current_forces = None
        self.current_equations = None
        self.current_critical = None
        
        # Export Toolbar
        self._setup_export_toolbar()
        
        self._setup_sections()
        self.main_layout.addStretch()
        
        self.setWidget(self.content_widget)

    def _setup_export_toolbar(self):
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(0, 0, 0, 15)
        
        btn_style = f"background-color: {_THEME['card_bg']}; color: {_THEME['accent']}; border: 1px solid {_THEME['border']}; border-radius: 4px; padding: 6px 12px; font-weight: bold;"
        
        self.btn_export_pdf = QPushButton("Exportar PDF Técnico")
        self.btn_export_pdf.setStyleSheet(btn_style)
        self.btn_export_pdf.clicked.connect(self._export_pdf)
        
        self.btn_export_png = QPushButton("Exportar Gráficas (PNG/SVG)")
        self.btn_export_png.setStyleSheet(btn_style)
        self.btn_export_png.clicked.connect(self._export_png)
        
        self.btn_export_csv = QPushButton("Exportar Tablas (CSV)")
        self.btn_export_csv.setStyleSheet(btn_style)
        self.btn_export_csv.clicked.connect(self._export_csv)
        
        self.btn_export_pdf.setEnabled(False)
        self.btn_export_png.setEnabled(False)
        self.btn_export_csv.setEnabled(False)
        
        toolbar_layout.addWidget(self.btn_export_pdf)
        toolbar_layout.addWidget(self.btn_export_png)
        toolbar_layout.addWidget(self.btn_export_csv)
        toolbar_layout.addStretch()
        
        self.main_layout.addLayout(toolbar_layout)

    def _setup_sections(self):
        # 1. Resumen General
        self.summary_card = ReportCard("1. Información del Modelo")
        self.summary_label = QLabel("Esperando análisis...")
        self.summary_label.setStyleSheet(f"color: {_THEME['text_p']}; font-size: 13px;")
        self.summary_card.add_widget(self.summary_label)
        self.main_layout.addWidget(self.summary_card)
        
        # 2. Reacciones
        self.reactions_card = ReportCard("2. Reacciones en Apoyos")
        self.reactions_table = QTableWidget()
        self._format_table(self.reactions_table, ["Apoyo", "x (m)", "Horizontal (kN)", "Vertical (kN)", "Momento (kN·m)"])
        self.reactions_card.add_widget(self.reactions_table)
        self.main_layout.addWidget(self.reactions_card)
        
        # 3. Ecuaciones
        self.equations_card = ReportCard("3. Funciones por Tramos")
        self.equations_label = QLabel("Sin ecuaciones generadas.")
        self.equations_label.setWordWrap(True)
        self.equations_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.equations_label.setStyleSheet(f"color: {_THEME['text_h1']}; font-family: Consolas, monospace; font-size: 13px; line-height: 1.5;")
        self.equations_card.add_widget(self.equations_label)
        self.main_layout.addWidget(self.equations_card)
        
        # 4. Diagrama de Cortante
        self.shear_card = ReportCard("4. Diagrama de Fuerza Cortante V(x)")
        self.shear_graph = SingleGraphWidget("Fuerza Cortante", "V (kN)", _THEME["v_pos"], _THEME["v_neg"])
        self.shear_card.add_widget(self.shear_graph)
        self.main_layout.addWidget(self.shear_card)
        
        # 5. Diagrama de Momento
        self.moment_card = ReportCard("5. Diagrama de Momento Flector M(x)")
        self.moment_graph = SingleGraphWidget("Momento Flector", "M (kN·m)", _THEME["m_pos"], _THEME["m_neg"], invert_y=False)
        self.moment_card.add_widget(self.moment_graph)
        self.main_layout.addWidget(self.moment_card)
        
        # 6. Interpretación y Zonas Críticas
        self.critical_card = ReportCard("6. Valores Críticos e Interpretación")
        self.critical_table = QTableWidget()
        self._format_table(self.critical_table, ["Posición x (m)", "Tipo", "Valor", "Descripción"])
        self.critical_card.add_widget(self.critical_table)
        
        self.interpretation_label = QLabel("")
        self.interpretation_label.setWordWrap(True)
        self.interpretation_label.setStyleSheet(f"color: {_THEME['text_p']}; font-size: 13px; margin-top: 10px;")
        self.critical_card.add_widget(self.interpretation_label)
        self.main_layout.addWidget(self.critical_card)

    def _format_table(self, table: QTableWidget, headers: list[str]):
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        table.setFixedHeight(120)
        table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {_THEME['bg']};
                color: {_THEME['text_h1']};
                gridline-color: {_THEME['border']};
                border: 1px solid {_THEME['border']};
                border-radius: 4px;
            }}
            QHeaderView::section {{
                background-color: {_THEME['card_bg']};
                color: {_THEME['accent']};
                font-weight: bold;
                border: none;
                border-bottom: 1px solid {_THEME['border']};
                padding: 4px;
            }}
        """)

    # ── Actualizadores ────────────────────────────────────────────────

    def update_report(
        self,
        beam: BeamModel,
        solution: SolutionResult,
        forces: InternalForcesResult,
        equations: EquationsResult,
        critical: CriticalZoneReport
    ):
        """Actualiza todos los componentes del reporte a la vez."""
        self.current_beam = beam
        self.current_solution = solution
        self.current_forces = forces
        self.current_equations = equations
        self.current_critical = critical
        
        self.btn_export_pdf.setEnabled(True)
        self.btn_export_png.setEnabled(True)
        self.btn_export_csv.setEnabled(True)
        # 1. Resumen
        self.summary_label.setText(
            f"<b>Longitud total:</b> {beam.length:.2f} m<br>"
            f"<b>Apoyos:</b> {len(beam.supports)}<br>"
            f"<b>Cargas aplicadas:</b> {len(beam.loads)}<br>"
            f"<b>Estado:</b> Sistema isostático resuelto correctamente."
        )
        
        # 2. Reacciones
        self.reactions_table.setRowCount(0)
        support_dict = {s.name: s.position for s in beam.supports}
        for support_name, reactions in solution.reactions.items():
            pos_x = support_dict.get(support_name, 0.0)
            row = self.reactions_table.rowCount()
            self.reactions_table.insertRow(row)
            self.reactions_table.setItem(row, 0, QTableWidgetItem(support_name))
            self.reactions_table.setItem(row, 1, QTableWidgetItem(f"{pos_x:.3f}"))
            rx = reactions.get("Rx", 0.0)
            ry = reactions.get("Ry", 0.0)
            rm = reactions.get("M", 0.0)
            self.reactions_table.setItem(row, 2, QTableWidgetItem(f"{rx:.3f}"))
            self.reactions_table.setItem(row, 3, QTableWidgetItem(f"{ry:.3f}"))
            self.reactions_table.setItem(row, 4, QTableWidgetItem(f"{rm:.3f}"))
        self.reactions_table.setFixedHeight(40 + min(4, max(1, self.reactions_table.rowCount())) * 30)
            
        # 3. Ecuaciones
        eq_text = ""
        for inter in equations.intervals:
            eq_text += f"<b>TRAMO desde x = {inter.x_start:.2f} m hasta x = {inter.x_end:.2f} m</b><br>"
            eq_text += f"&nbsp;&nbsp;Fuerza Cortante: V(x) = {str(inter.V_expr).replace('**', '^').replace('*', '')}<br>"
            eq_text += f"&nbsp;&nbsp;Momento Flector: M(x) = {str(inter.M_expr).replace('**', '^').replace('*', '')}<br><br>"
        self.equations_label.setText(eq_text.strip() if eq_text else "Sin ecuaciones.")
        
        # 4 & 5. Diagramas
        # Extraer puntos críticos para gráficas
        v_pts = []
        m_pts = []
        for z in critical.zones:
            if "CORTANTE" in z.zone_type or "NULO" in z.zone_type:
                # Interpolamos o buscamos el valor exacto
                idx = np.argmin(np.abs(forces.x_vals - z.x_position))
                v_pts.append({"x": z.x_position, "y": forces.V_vals[idx], "label": z.zone_type})
            if "MOMENTO" in z.zone_type or "NULO" in z.zone_type:
                idx = np.argmin(np.abs(forces.x_vals - z.x_position))
                m_pts.append({"x": z.x_position, "y": forces.M_vals[idx], "label": z.zone_type})
                
        self.shear_graph.plot_data(forces.x_vals, forces.V_vals, v_pts)
        self.moment_graph.plot_data(forces.x_vals, forces.M_vals, m_pts)
        
        # 6. Zonas Críticas e Interpretación
        self.critical_table.setRowCount(0)
        for z in critical.zones:
            row = self.critical_table.rowCount()
            self.critical_table.insertRow(row)
            self.critical_table.setItem(row, 0, QTableWidgetItem(f"{z.x_position:.3f}"))
            self.critical_table.setItem(row, 1, QTableWidgetItem(z.zone_type))
            self.critical_table.setItem(row, 2, QTableWidgetItem(f"{z.value:.2f}"))
            self.critical_table.setItem(row, 3, QTableWidgetItem(z.description))
        self.critical_table.setFixedHeight(40 + min(6, max(1, self.critical_table.rowCount())) * 30)
        
        # Texto interpretativo
        interp = "<b>Interpretación Estructural:</b><br>"
        for msg in critical.messages:
            interp += f"• {msg}<br>"
            
        m_max = critical.max_values.get("M_abs_max", 0.0)
        if m_max > 0:
            interp += f"<br><i>El diseño a flexión estará gobernado por un momento de {m_max:.2f} kN·m.</i>"
        self.interpretation_label.setText(interp)

    def clear_report(self):
        self.summary_label.setText("Esperando análisis...")
        self.reactions_table.setRowCount(0)
        self.equations_label.setText("Sin ecuaciones generadas.")
        self.shear_graph.ax.clear()
        self.shear_graph.canvas.draw_idle()
        self.moment_graph.ax.clear()
        self.moment_graph.canvas.draw_idle()
        self.critical_table.setRowCount(0)
        self.interpretation_label.setText("")
        
        self.current_beam = None
        self.btn_export_pdf.setEnabled(False)
        self.btn_export_png.setEnabled(False)
        self.btn_export_csv.setEnabled(False)

    def _export_pdf(self):
        if not self.current_beam: return
        file_path, _ = QFileDialog.getSaveFileName(self, "Exportar PDF", "", "Archivos PDF (*.pdf)")
        if file_path:
            try:
                # Need to pass figures from the single graph widgets
                # Use light theme for PDF export
                self.shear_graph.figure.set_facecolor('white')
                self.shear_graph.ax.set_facecolor('white')
                self.shear_graph.ax.tick_params(colors='black')
                self.shear_graph.ax.xaxis.label.set_color('black')
                self.shear_graph.ax.yaxis.label.set_color('black')
                self.shear_graph.ax.title.set_color('black')
                
                self.moment_graph.figure.set_facecolor('white')
                self.moment_graph.ax.set_facecolor('white')
                self.moment_graph.ax.tick_params(colors='black')
                self.moment_graph.ax.xaxis.label.set_color('black')
                self.moment_graph.ax.yaxis.label.set_color('black')
                self.moment_graph.ax.title.set_color('black')
                
                ReportExporter.export_pdf(
                    file_path, self.current_beam, self.current_solution, 
                    self.current_forces, self.current_equations, self.current_critical,
                    self.shear_graph.figure, self.moment_graph.figure
                )
                
                # Restore dark theme
                self.shear_graph.figure.set_facecolor(_THEME["card_bg"])
                self.shear_graph.ax.set_facecolor(_THEME["card_bg"])
                self.shear_graph.ax.tick_params(colors=_THEME["text_p"])
                self.moment_graph.figure.set_facecolor(_THEME["card_bg"])
                self.moment_graph.ax.set_facecolor(_THEME["card_bg"])
                self.moment_graph.ax.tick_params(colors=_THEME["text_p"])
                
                QMessageBox.information(self, "Éxito", f"Reporte PDF exportado correctamente a:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al exportar PDF: {e}")

    def _export_png(self):
        if not self.current_beam: return
        file_path, filter_sel = QFileDialog.getSaveFileName(self, "Exportar Gráficas", "", "Imagen PNG (*.png);;Imagen SVG (*.svg)")
        if file_path:
            try:
                # Combine both figures or export separately. Exporting separately for simplicity:
                base, ext = os.path.splitext(file_path)
                shear_path = f"{base}_cortante{ext}"
                moment_path = f"{base}_momento{ext}"
                self.shear_graph.figure.savefig(shear_path, dpi=300, bbox_inches='tight')
                self.moment_graph.figure.savefig(moment_path, dpi=300, bbox_inches='tight')
                QMessageBox.information(self, "Éxito", f"Gráficas exportadas correctamente:\n{shear_path}\n{moment_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al exportar gráficas: {e}")

    def _export_csv(self):
        if not self.current_beam: return
        file_path, _ = QFileDialog.getSaveFileName(self, "Exportar Tablas CSV", "", "Archivos CSV (*.csv)")
        if file_path:
            try:
                ReportExporter.export_csv(
                    file_path, self.current_beam, self.current_solution, 
                    self.current_forces, self.current_equations, self.current_critical
                )
                QMessageBox.information(self, "Éxito", f"Tablas CSV exportadas correctamente a:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al exportar CSV: {e}")
