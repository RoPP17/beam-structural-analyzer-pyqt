"""
Panel de diagramas V/M (y deflexión) para BeamAnalyzer.

Embebe gráficos Matplotlib dentro de PyQt6 para mostrar los diagramas
de fuerza cortante, momento flector y (opcionalmente) deflexión.
"""

from __future__ import annotations

from typing import Optional, Sequence

import matplotlib
import numpy as np
from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar,
)
from matplotlib.figure import Figure
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

# Usar el backend Qt antes de cualquier importación de pyplot
matplotlib.use("QtAgg")


# ── Constantes de estilo (tema oscuro por defecto) ──────────────

_DARK_STYLE: dict[str, str] = {
    "bg": "#0d1117",
    "fg": "#e6edf3",
    "grid": "#21262d",
    "axis": "#30363d",
    "v_pos": "#58a6ff",
    "v_neg": "#f85149",
    "m_pos": "#3fb950",
    "m_neg": "#f0883e",
    "deflection": "#d2a8ff",
    "baseline": "#484f58",
    "marker": "#e6edf3",
}

_LIGHT_STYLE: dict[str, str] = {
    "bg": "#ffffff",
    "fg": "#24292f",
    "grid": "#e1e4e8",
    "axis": "#d0d7de",
    "v_pos": "#0969da",
    "v_neg": "#cf222e",
    "m_pos": "#1a7f37",
    "m_neg": "#bf8700",
    "deflection": "#8250df",
    "baseline": "#afb8c1",
    "marker": "#24292f",
}


class DiagramPanel(QWidget):
    """Panel inferior con diagramas de cortante, momento y deflexión.

    Utiliza Matplotlib embebido para renderizado de alta calidad con
    interacción de zoom/pan y lectura de coordenadas en tiempo real.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("diagramContainer")

        self._style = _DARK_STYLE
        self._show_deflection = False

        self._setup_ui()
        self._setup_figure()
        self._connect_events()

    # ── Construcción de la interfaz ─────────────────────────────

    def _setup_ui(self) -> None:
        """Crea el layout principal con canvas, toolbar y controles."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Barra de controles superior
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(4, 0, 4, 0)

        self._deflection_check = QCheckBox("Mostrar Deflexión")
        self._deflection_check.setChecked(False)
        self._deflection_check.toggled.connect(self._on_deflection_toggled)
        controls_layout.addWidget(self._deflection_check)

        controls_layout.addStretch()

        self._coord_label = QLabel("x = —, y = —")
        self._coord_label.setObjectName("secondaryLabel")
        self._coord_label.setStyleSheet("font-family: monospace; font-size: 12px;")
        controls_layout.addWidget(self._coord_label)

        layout.addLayout(controls_layout)

        # Figura Matplotlib
        self._figure = Figure(tight_layout=True)
        self._canvas = FigureCanvas(self._figure)
        self._canvas.setMinimumHeight(250)
        layout.addWidget(self._canvas, stretch=1)

        # Barra de navegación Matplotlib
        self._toolbar = NavigationToolbar(self._canvas, self)
        layout.addWidget(self._toolbar)

    def _setup_figure(self) -> None:
        """Inicializa los ejes de la figura."""
        self._figure.clear()
        s = self._style
        self._figure.set_facecolor(s["bg"])

        if self._show_deflection:
            self._ax_v = self._figure.add_subplot(3, 1, 1)
            self._ax_m = self._figure.add_subplot(3, 1, 2)
            self._ax_d = self._figure.add_subplot(3, 1, 3)
            axes = [self._ax_v, self._ax_m, self._ax_d]
        else:
            self._ax_v = self._figure.add_subplot(2, 1, 1)
            self._ax_m = self._figure.add_subplot(2, 1, 2)
            self._ax_d = None
            axes = [self._ax_v, self._ax_m]

        for ax in axes:
            ax.set_facecolor(s["bg"])
            ax.tick_params(colors=s["fg"], labelsize=9)
            ax.spines["bottom"].set_color(s["axis"])
            ax.spines["left"].set_color(s["axis"])
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.grid(True, color=s["grid"], linewidth=0.5, alpha=0.7)

        # Títulos y etiquetas
        self._ax_v.set_title(
            "Diagrama de Fuerza Cortante",
            color=s["fg"], fontsize=11, fontweight="bold", pad=8,
        )
        self._ax_v.set_ylabel("Fuerza Cortante (kN)", color=s["fg"], fontsize=10)

        self._ax_m.set_title(
            "Diagrama de Momento Flector",
            color=s["fg"], fontsize=11, fontweight="bold", pad=8,
        )
        self._ax_m.set_ylabel("Momento Flector (kN·m)", color=s["fg"], fontsize=10)
        self._ax_m.set_xlabel("Posición (m)", color=s["fg"], fontsize=10)
        # Convención: eje y normal para momento (invertido respecto a versión previa)
        # self._ax_m.invert_yaxis()

        if self._ax_d is not None:
            self._ax_d.set_title(
                "Deflexión",
                color=s["fg"], fontsize=11, fontweight="bold", pad=8,
            )
            self._ax_d.set_ylabel("Deflexión (mm)", color=s["fg"], fontsize=10)
            self._ax_d.set_xlabel("Posición (m)", color=s["fg"], fontsize=10)
            # Quitar xlabel del momento si hay deflexión
            self._ax_m.set_xlabel("")

        self._figure.tight_layout(pad=2.0)
        self._canvas.draw_idle()

    def _connect_events(self) -> None:
        """Conecta el evento de movimiento del ratón sobre el canvas."""
        self._canvas.mpl_connect("motion_notify_event", self._on_mouse_move)

    # ── Eventos ─────────────────────────────────────────────────

    def _on_mouse_move(self, event: matplotlib.backend_bases.MouseEvent) -> None:
        """Actualiza la etiqueta de coordenadas al mover el ratón."""
        if event.inaxes is not None and event.xdata is not None:
            ax = event.inaxes
            if ax is self._ax_v:
                self._coord_label.setText(
                    f"x = {event.xdata:.3f} m,  V = {event.ydata:.3f} kN"
                )
            elif ax is self._ax_m:
                self._coord_label.setText(
                    f"x = {event.xdata:.3f} m,  M = {event.ydata:.3f} kN·m"
                )
            elif ax is self._ax_d:
                self._coord_label.setText(
                    f"x = {event.xdata:.3f} m,  δ = {event.ydata:.4f} mm"
                )
        else:
            self._coord_label.setText("x = —, y = —")

    def _on_deflection_toggled(self, checked: bool) -> None:
        """Re-crea los ejes al activar/desactivar deflexión."""
        self._show_deflection = checked
        self._setup_figure()

    # ── API pública ─────────────────────────────────────────────

    def update_diagrams(
        self,
        x_vals: Sequence[float] | np.ndarray,
        v_vals: Sequence[float] | np.ndarray,
        m_vals: Sequence[float] | np.ndarray,
        critical_points: Optional[
            list[dict[str, float | str]]
        ] = None,
    ) -> None:
        """Actualiza los diagramas de cortante y momento.

        Args:
            x_vals: Coordenadas x a lo largo de la viga.
            v_vals: Valores de fuerza cortante correspondientes.
            m_vals: Valores de momento flector correspondientes.
            critical_points: Lista de diccionarios con claves
                ``"x"``, ``"v"``, ``"m"`` y opcionalmente ``"label"``.
        """
        x = np.asarray(x_vals, dtype=float)
        v = np.asarray(v_vals, dtype=float)
        m = np.asarray(m_vals, dtype=float)
        s = self._style

        # ── Cortante ────────────────────────────────────────────
        self._ax_v.clear()
        self._apply_axis_style(self._ax_v)
        self._ax_v.set_title(
            "Diagrama de Fuerza Cortante",
            color=s["fg"], fontsize=11, fontweight="bold", pad=8,
        )
        self._ax_v.set_ylabel("Fuerza Cortante (kN)", color=s["fg"], fontsize=10)

        # Línea base
        self._ax_v.axhline(y=0, color=s["baseline"], linewidth=0.8, zorder=1)

        # Curva
        self._ax_v.plot(x, v, color=s["v_pos"], linewidth=1.5, zorder=3)

        # Relleno coloreado
        v_pos = np.where(v >= 0, v, 0)
        v_neg = np.where(v <= 0, v, 0)
        self._ax_v.fill_between(
            x, v_pos, 0, alpha=0.20, color=s["v_pos"], zorder=2,
        )
        self._ax_v.fill_between(
            x, v_neg, 0, alpha=0.20, color=s["v_neg"], zorder=2,
        )

        # ── Momento ─────────────────────────────────────────────
        self._ax_m.clear()
        self._apply_axis_style(self._ax_m)
        self._ax_m.set_title(
            "Diagrama de Momento Flector",
            color=s["fg"], fontsize=11, fontweight="bold", pad=8,
        )
        self._ax_m.set_ylabel("Momento Flector (kN·m)", color=s["fg"], fontsize=10)
        if not self._show_deflection:
            self._ax_m.set_xlabel("Posición (m)", color=s["fg"], fontsize=10)
        # self._ax_m.invert_yaxis()

        self._ax_m.axhline(y=0, color=s["baseline"], linewidth=0.8, zorder=1)
        self._ax_m.plot(x, m, color=s["m_pos"], linewidth=1.5, zorder=3)

        m_pos = np.where(m >= 0, m, 0)
        m_neg = np.where(m <= 0, m, 0)
        self._ax_m.fill_between(
            x, m_pos, 0, alpha=0.20, color=s["m_pos"], zorder=2,
        )
        self._ax_m.fill_between(
            x, m_neg, 0, alpha=0.20, color=s["m_neg"], zorder=2,
        )

        # ── Puntos críticos ─────────────────────────────────────
        if critical_points:
            x_range = x[-1] - x[0] if len(x) > 1 and x[-1] != x[0] else 1.0
            x_threshold = x_range * 0.04  # Umbral de cercanía en X

            v_placed = []
            m_placed = []

            for pt in critical_points:
                px = float(pt["x"])
                pv = float(pt.get("v", 0.0))
                pm = float(pt.get("m", 0.0))
                label = str(pt.get("label", ""))

                # Marcadores en cortante
                self._ax_v.plot(
                    px, pv, "o",
                    color=s["marker"], markersize=5, zorder=5,
                )
                
                dy = 15 if pv >= 0 else -15
                for (lx, ldy) in v_placed:
                    if abs(px - lx) < x_threshold and ((dy > 0) == (ldy > 0)):
                        if abs(dy - ldy) < 15:
                            dy = ldy + (15 if dy > 0 else -15)
                v_placed.append((px, dy))
                
                v_va = "bottom" if dy >= 0 else "top"
                v_props = dict(arrowstyle="-", color=s["fg"], lw=0.5, alpha=0.5) if abs(dy) > 20 else None
                
                self._ax_v.annotate(
                    f"{pv:.2f}",
                    (px, pv),
                    textcoords="offset points",
                    xytext=(0, dy),
                    fontsize=8,
                    color=s["fg"],
                    zorder=5,
                    ha="center",
                    va=v_va,
                    bbox=dict(boxstyle="round,pad=0.2", facecolor=s["bg"], edgecolor='none', alpha=0.7),
                    arrowprops=v_props
                )

                # Marcadores en momento
                self._ax_m.plot(
                    px, pm, "o",
                    color=s["marker"], markersize=5, zorder=5,
                )
                annotation_text = f"{pm:.2f}"
                if label:
                    annotation_text = f"{label}: {annotation_text}"
                
                # Eje Y normal: pm >= 0 va hacia arriba
                m_dy = 15 if pm >= 0 else -15
                for (lx, ldy) in m_placed:
                    if abs(px - lx) < x_threshold and ((m_dy > 0) == (ldy > 0)):
                        if abs(m_dy - ldy) < 15:
                            m_dy = ldy + (15 if m_dy > 0 else -15)
                m_placed.append((px, m_dy))
                
                m_va = "bottom" if m_dy >= 0 else "top"
                m_props = dict(arrowstyle="-", color=s["fg"], lw=0.5, alpha=0.5) if abs(m_dy) > 20 else None
                
                self._ax_m.annotate(
                    annotation_text,
                    (px, pm),
                    textcoords="offset points",
                    xytext=(0, m_dy),
                    fontsize=8,
                    color=s["fg"],
                    zorder=5,
                    ha="center",
                    va=m_va,
                    bbox=dict(boxstyle="round,pad=0.2", facecolor=s["bg"], edgecolor='none', alpha=0.7),
                    arrowprops=m_props
                )

        # Ampliar márgenes del eje Y para evitar recortes de etiquetas
        v_min, v_max = self._ax_v.get_ylim()
        v_range = v_max - v_min
        if v_range > 0:
            self._ax_v.set_ylim(v_min - v_range * 0.35, v_max + v_range * 0.35)

        m_min, m_max = self._ax_m.get_ylim()
        m_range = m_max - m_min
        if m_range > 0:
            self._ax_m.set_ylim(m_min - m_range * 0.35, m_max + m_range * 0.35)

        self._figure.tight_layout(pad=2.0)
        self._canvas.draw_idle()

    def update_deflection(
        self,
        x_vals: Sequence[float] | np.ndarray,
        y_vals: Sequence[float] | np.ndarray,
    ) -> None:
        """Actualiza el diagrama de deflexión (tercer subplot).

        Args:
            x_vals: Coordenadas x a lo largo de la viga.
            y_vals: Valores de deflexión (positivo hacia arriba).
        """
        if self._ax_d is None:
            return

        x = np.asarray(x_vals, dtype=float)
        y = np.asarray(y_vals, dtype=float)
        s = self._style

        self._ax_d.clear()
        self._apply_axis_style(self._ax_d)
        self._ax_d.set_title(
            "Deflexión",
            color=s["fg"], fontsize=11, fontweight="bold", pad=8,
        )
        self._ax_d.set_ylabel("Deflexión (mm)", color=s["fg"], fontsize=10)
        self._ax_d.set_xlabel("Posición (m)", color=s["fg"], fontsize=10)

        self._ax_d.axhline(y=0, color=s["baseline"], linewidth=0.8, zorder=1)
        self._ax_d.plot(x, y, color=s["deflection"], linewidth=1.5, zorder=3)
        self._ax_d.fill_between(
            x, y, 0, alpha=0.15, color=s["deflection"], zorder=2,
        )

        # Deflexión máxima
        if len(y) > 0:
            idx_max = int(np.argmax(np.abs(y)))
            self._ax_d.plot(
                x[idx_max], y[idx_max], "o",
                color=s["marker"], markersize=5, zorder=5,
            )
            self._ax_d.annotate(
                f"δ_max = {y[idx_max]:.4f} mm",
                (x[idx_max], y[idx_max]),
                textcoords="offset points",
                xytext=(8, 10),
                fontsize=8,
                color=s["fg"],
                zorder=5,
            )

        self._figure.tight_layout(pad=2.0)
        self._canvas.draw_idle()

    def clear_diagrams(self) -> None:
        """Limpia todos los diagramas y restablece los ejes."""
        self._setup_figure()

    def set_theme(self, dark: bool = True) -> None:
        """Cambia el tema de colores de los diagramas.

        Args:
            dark: ``True`` para tema oscuro, ``False`` para tema claro.
        """
        self._style = _DARK_STYLE if dark else _LIGHT_STYLE
        self._setup_figure()

    # ── Utilidades internas ─────────────────────────────────────

    def _apply_axis_style(self, ax: matplotlib.axes.Axes) -> None:
        """Aplica el estilo de tema a un eje individual."""
        s = self._style
        ax.set_facecolor(s["bg"])
        ax.tick_params(colors=s["fg"], labelsize=9)
        ax.spines["bottom"].set_color(s["axis"])
        ax.spines["left"].set_color(s["axis"])
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(True, color=s["grid"], linewidth=0.5, alpha=0.7)
