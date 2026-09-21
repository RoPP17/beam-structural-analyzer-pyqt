"""
Panel de tabla para visualizar y gestionar elementos estructurales.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, 
    QPushButton, QHBoxLayout, QHeaderView, QLabel
)
from PyQt6.QtCore import pyqtSignal, Qt
from app.core.beam_model import BeamModel
from app.core.supports import SupportType
from app.core.loads import PointLoad, DistributedLoad, TriangularLoad, TrapezoidalLoad, MomentLoad, InclinedLoad

class ElementTablePanel(QWidget):
    # Signals to communicate with the controller
    edit_requested = pyqtSignal(str, int) # (group: 'support' or 'load', index)
    delete_requested = pyqtSignal(str, int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("elementTablePanel")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # Title
        title = QLabel("Lista de Elementos")
        title.setStyleSheet("font-weight: bold;")
        layout.addWidget(title)
        
        # Table
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Clase", "Tipo", "Pos/Inicio", "Magnitud/w", "Detalles", "Acciones"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)
        
    def update_table(self, beam: BeamModel) -> None:
        """Actualiza la tabla a partir del estado actual del modelo."""
        self.table.setRowCount(0)
        
        # Add supports
        for idx, sup in enumerate(beam.supports):
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            sup_types = {
                SupportType.PINNED: "Articulado",
                SupportType.ROLLER: "Rodillo",
                SupportType.FIXED: "Empotrado"
            }
            
            self.table.setItem(row, 0, QTableWidgetItem("Apoyo"))
            self.table.setItem(row, 1, QTableWidgetItem(sup_types.get(sup.support_type, "Desconocido")))
            self.table.setItem(row, 2, QTableWidgetItem(f"{sup.position:.2f} m"))
            self.table.setItem(row, 3, QTableWidgetItem("-"))
            self.table.setItem(row, 4, QTableWidgetItem(f"Nombre: {sup.name}"))
            
            self._add_action_buttons(row, "support", idx)
            
        # Add loads
        for idx, load in enumerate(beam.loads):
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            self.table.setItem(row, 0, QTableWidgetItem("Carga"))
            
            l_type = "Desconocida"
            pos_str = ""
            mag_str = ""
            detail_str = ""
            
            if isinstance(load, PointLoad):
                l_type = "Puntual"
                pos_str = f"{load.position:.2f} m"
                mag_str = f"{load.magnitude:.2f} kN"
            elif isinstance(load, MomentLoad):
                l_type = "Momento"
                pos_str = f"{load.position:.2f} m"
                mag_str = f"{load.magnitude:.2f} kN·m"
            elif isinstance(load, DistributedLoad) and not isinstance(load, (TriangularLoad, TrapezoidalLoad)):
                l_type = "Distr. Uniforme"
                pos_str = f"{load.start:.2f} - {load.end:.2f} m"
                mag_str = f"{load.w:.2f} kN/m"
            elif isinstance(load, TriangularLoad):
                l_type = "Distr. Triangular"
                pos_str = f"{load.start:.2f} - {load.end:.2f} m"
                mag_str = f"{load.w_start:.2f} ➔ {load.w_end:.2f} kN/m"
            elif isinstance(load, TrapezoidalLoad):
                l_type = "Distr. Trapezoidal"
                pos_str = f"{load.start:.2f} - {load.end:.2f} m"
                mag_str = f"{load.w_start:.2f} ➔ {load.w_end:.2f} kN/m"
            elif isinstance(load, InclinedLoad):
                l_type = "Inclinada"
                pos_str = f"{load.position:.2f} m"
                mag_str = f"{load.magnitude:.2f} kN"
                detail_str = f"Ángulo: {load.angle}°"
                
            self.table.setItem(row, 1, QTableWidgetItem(l_type))
            self.table.setItem(row, 2, QTableWidgetItem(pos_str))
            self.table.setItem(row, 3, QTableWidgetItem(mag_str))
            self.table.setItem(row, 4, QTableWidgetItem(detail_str))
            
            self._add_action_buttons(row, "load", idx)
            
    def _add_action_buttons(self, row: int, group: str, idx: int) -> None:
        widget = QWidget()
        hlayout = QHBoxLayout(widget)
        hlayout.setContentsMargins(0, 0, 0, 0)
        hlayout.setSpacing(4)
        
        btn_edit = QPushButton("✏️")
        btn_edit.setToolTip("Editar")
        btn_edit.setMaximumWidth(30)
        btn_edit.clicked.connect(lambda _, g=group, i=idx: self.edit_requested.emit(g, i))
        
        btn_del = QPushButton("❌")
        btn_del.setToolTip("Eliminar")
        btn_del.setMaximumWidth(30)
        btn_del.clicked.connect(lambda _, g=group, i=idx: self.delete_requested.emit(g, i))
        
        hlayout.addStretch()
        hlayout.addWidget(btn_edit)
        hlayout.addWidget(btn_del)
        hlayout.addStretch()
        
        self.table.setCellWidget(row, 5, widget)
