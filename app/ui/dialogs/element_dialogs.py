"""
Diálogos para añadir elementos mediante entrada exacta por teclado.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, 
    QDoubleSpinBox, QDialogButtonBox, QLabel, QStackedWidget, QWidget, QHBoxLayout
)
from PyQt6.QtCore import Qt

class BaseElementDialog(QDialog):
    def __init__(self, title: str, beam_length: float, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.beam_length = beam_length
        self.setMinimumWidth(300)
        
        self.main_layout = QVBoxLayout(self)
        self.form_layout = QFormLayout()
        self.main_layout.addLayout(self.form_layout)
        
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.main_layout.addWidget(self.button_box)
        
    def _create_spinbox(self, max_val: float = 1e6, min_val: float = -1e6, decimals: int = 2) -> QDoubleSpinBox:
        sb = QDoubleSpinBox()
        sb.setRange(min_val, max_val)
        sb.setDecimals(decimals)
        return sb

class SupportDialog(BaseElementDialog):
    def __init__(self, beam_length: float, default_type: str = "pinned_support", parent=None):
        super().__init__("Añadir Apoyo", beam_length, parent)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Articulado (Pinned)", "Rodillo (Roller)", "Empotramiento (Fixed)"])
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        
        # (Default type logic moved to end of init)
        
        self.pos_combo = QComboBox()
        self.pos_combo.addItems(["Extremo Izquierdo (0 m)", f"Extremo Derecho ({beam_length:.2f} m)", "Personalizado..."])
        self.pos_combo.currentIndexChanged.connect(self._on_pos_combo_changed)
        
        self.pos_spin = self._create_spinbox(min_val=0, max_val=beam_length)
        self.pos_spin.setEnabled(False)
        self.pos_spin.setValue(0)
        
        pos_layout = QHBoxLayout()
        pos_layout.addWidget(self.pos_combo)
        pos_layout.addWidget(self.pos_spin)
        
        self.form_layout.addRow("Tipo:", self.type_combo)
        self.form_layout.addRow("Posición:", pos_layout)
        
        if "roller" in default_type:
            self.type_combo.setCurrentIndex(1)
        elif "fixed" in default_type:
            self.type_combo.setCurrentIndex(2)
        else:
            self.type_combo.setCurrentIndex(0)
        
    def _on_pos_combo_changed(self, idx):
        self.pos_spin.setEnabled(idx == 2)
        if idx == 0:
            self.pos_spin.setValue(0)
        elif idx == 1:
            self.pos_spin.setValue(self.beam_length)
            
    def _on_type_changed(self, idx):
        # Si es empotramiento, idealmente solo permitir extremos
        if idx == 2:
            if self.pos_combo.currentIndex() == 2: # Custom
                # Forzar a un extremo por estabilidad, aunque si el usuario quiere, lo dejamos pero con aviso
                pass

    def get_data(self) -> dict:
        t_idx = self.type_combo.currentIndex()
        types = ["pinned", "roller", "fixed"]
        return {
            "type": types[t_idx],
            "position": self.pos_spin.value()
        }
        
    def set_data(self, data: dict) -> None:
        if "type" in data:
            idx = ["pinned", "roller", "fixed"].index(data["type"])
            self.type_combo.setCurrentIndex(idx)
        if "position" in data:
            if data["position"] == 0:
                self.pos_combo.setCurrentIndex(0)
            elif abs(data["position"] - self.beam_length) < 1e-6:
                self.pos_combo.setCurrentIndex(1)
            else:
                self.pos_combo.setCurrentIndex(2)
                self.pos_spin.setValue(data["position"])

class PointLoadDialog(BaseElementDialog):
    def __init__(self, beam_length: float, parent=None):
        super().__init__("Añadir Carga Puntual", beam_length, parent)
        
        self.mag_spin = self._create_spinbox(min_val=0.01)
        self.mag_spin.setValue(10.0)
        
        self.dir_combo = QComboBox()
        self.dir_combo.addItems(["↓ Hacia abajo", "↑ Hacia arriba"])
        
        self.pos_spin = self._create_spinbox(min_val=0, max_val=beam_length)
        self.pos_spin.setValue(beam_length / 2)
        
        self.form_layout.addRow("Magnitud (kN):", self.mag_spin)
        self.form_layout.addRow("Dirección:", self.dir_combo)
        self.form_layout.addRow("Posición (m):", self.pos_spin)
        
    def get_data(self) -> dict:
        mag = self.mag_spin.value()
        if self.dir_combo.currentIndex() == 1:
            mag = -mag
        return {
            "type": "point_load",
            "magnitude": mag,
            "position": self.pos_spin.value()
        }
        
    def set_data(self, data: dict) -> None:
        if "magnitude" in data:
            mag = data["magnitude"]
            if mag < 0:
                self.dir_combo.setCurrentIndex(1)
                self.mag_spin.setValue(abs(mag))
            else:
                self.dir_combo.setCurrentIndex(0)
                self.mag_spin.setValue(mag)
        if "position" in data:
            self.pos_spin.setValue(data["position"])

class DistributedLoadDialog(BaseElementDialog):
    def __init__(self, beam_length: float, default_type: str = "distributed_load", parent=None):
        super().__init__("Añadir Carga Distribuida", beam_length, parent)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Uniforme", "Triangular", "Trapezoidal"])
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        
        # (Default type logic moved to end of init)
        
        self.start_spin = self._create_spinbox(min_val=0, max_val=beam_length)
        self.start_spin.setValue(0)
        
        self.end_spin = self._create_spinbox(min_val=0, max_val=beam_length)
        self.end_spin.setValue(beam_length)
        
        self.w1_spin = self._create_spinbox()
        self.w1_spin.setValue(10.0)
        
        self.w2_spin = self._create_spinbox()
        self.w2_spin.setValue(10.0)
        self.w2_spin.setEnabled(False) # For uniform initially
        
        self.form_layout.addRow("Tipo:", self.type_combo)
        self.form_layout.addRow("Inicio (m):", self.start_spin)
        self.form_layout.addRow("Fin (m):", self.end_spin)
        self.form_layout.addRow("Intensidad inicial (w1):", self.w1_spin)
        self.form_layout.addRow("Intensidad final (w2):", self.w2_spin)
        
        if "triangular" in default_type:
            self.type_combo.setCurrentIndex(1)
        elif "trapezoidal" in default_type:
            self.type_combo.setCurrentIndex(2)
        else:
            self.type_combo.setCurrentIndex(0)
        
    def _on_type_changed(self, idx):
        if idx == 0: # Uniform
            self.w2_spin.setEnabled(False)
            self.w2_spin.setValue(self.w1_spin.value())
        else:
            self.w2_spin.setEnabled(True)
            if idx == 1: # Triangular
                self.w1_spin.setValue(0)
                self.w2_spin.setValue(10)
                
    def get_data(self) -> dict:
        t_idx = self.type_combo.currentIndex()
        if t_idx == 0:
            return {
                "type": "distributed",
                "start": self.start_spin.value(),
                "end": self.end_spin.value(),
                "w": self.w1_spin.value()
            }
        elif t_idx == 1:
            return {
                "type": "triangular",
                "start": self.start_spin.value(),
                "end": self.end_spin.value(),
                "w_start": self.w1_spin.value(),
                "w_end": self.w2_spin.value()
            }
        else:
            return {
                "type": "trapezoidal",
                "start": self.start_spin.value(),
                "end": self.end_spin.value(),
                "w_start": self.w1_spin.value(),
                "w_end": self.w2_spin.value()
            }
            
    def set_data(self, data: dict) -> None:
        t = data.get("type", "distributed")
        if t == "distributed":
            self.type_combo.setCurrentIndex(0)
            self.w1_spin.setValue(data.get("w", 10.0))
        elif t == "triangular":
            self.type_combo.setCurrentIndex(1)
            self.w1_spin.setValue(data.get("w_start", 0))
            self.w2_spin.setValue(data.get("w_end", 10))
        elif t == "trapezoidal":
            self.type_combo.setCurrentIndex(2)
            self.w1_spin.setValue(data.get("w_start", 5))
            self.w2_spin.setValue(data.get("w_end", 15))
            
        if "start" in data:
            self.start_spin.setValue(data["start"])
        if "end" in data:
            self.end_spin.setValue(data["end"])

class MomentDialog(BaseElementDialog):
    def __init__(self, beam_length: float, parent=None):
        super().__init__("Añadir Momento", beam_length, parent)
        
        self.mag_spin = self._create_spinbox(min_val=0.01)
        self.mag_spin.setValue(20.0)
        
        self.dir_combo = QComboBox()
        self.dir_combo.addItems(["↺ Antihorario (+)", "↻ Horario (-)"])
        
        self.pos_spin = self._create_spinbox(min_val=0, max_val=beam_length)
        self.pos_spin.setValue(beam_length / 2)
        
        self.form_layout.addRow("Magnitud (kN·m):", self.mag_spin)
        self.form_layout.addRow("Sentido:", self.dir_combo)
        self.form_layout.addRow("Posición (m):", self.pos_spin)
        
    def get_data(self) -> dict:
        mag = self.mag_spin.value()
        if self.dir_combo.currentIndex() == 1:
            mag = -mag
        return {
            "type": "moment",
            "magnitude": mag,
            "position": self.pos_spin.value()
        }
        
    def set_data(self, data: dict) -> None:
        if "magnitude" in data:
            mag = data["magnitude"]
            if mag < 0:
                self.dir_combo.setCurrentIndex(1)
                self.mag_spin.setValue(abs(mag))
            else:
                self.dir_combo.setCurrentIndex(0)
                self.mag_spin.setValue(mag)
        if "position" in data:
            self.pos_spin.setValue(data["position"])

class InclinedLoadDialog(BaseElementDialog):
    def __init__(self, beam_length: float, parent=None):
        super().__init__("Añadir Carga Inclinada", beam_length, parent)
        
        self.mag_spin = self._create_spinbox(min_val=0.01)
        self.mag_spin.setValue(10.0)
        
        self.angle_spin = self._create_spinbox(min_val=-360, max_val=360)
        self.angle_spin.setValue(45.0)
        
        self.pos_spin = self._create_spinbox(min_val=0, max_val=beam_length)
        self.pos_spin.setValue(beam_length / 2)
        
        self.form_layout.addRow("Magnitud (kN):", self.mag_spin)
        self.form_layout.addRow("Ángulo (°):", self.angle_spin)
        self.form_layout.addRow("Posición (m):", self.pos_spin)
        
    def get_data(self) -> dict:
        return {
            "type": "inclined",
            "magnitude": self.mag_spin.value(),
            "angle": self.angle_spin.value(),
            "position": self.pos_spin.value()
        }
        
    def set_data(self, data: dict) -> None:
        if "magnitude" in data:
            self.mag_spin.setValue(data["magnitude"])
        if "angle" in data:
            self.angle_spin.setValue(data["angle"])
        if "position" in data:
            self.pos_spin.setValue(data["position"])
