"""
Paleta de colores para BeamAnalyzer.

Proporciona temas claro y oscuro con colores semánticos
para todos los elementos estructurales de la aplicación.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import ClassVar

from PyQt6.QtGui import QColor


class Theme(Enum):
    """Enumeración de temas disponibles."""
    DARK = auto()
    LIGHT = auto()


@dataclass(frozen=True, slots=True)
class ColorPalette:
    """Definición inmutable de una paleta de colores completa."""

    # ── Fondos ──────────────────────────────────────────────
    bg_primary: str
    bg_secondary: str
    bg_tertiary: str
    border: str

    # ── Texto ───────────────────────────────────────────────
    text_primary: str
    text_secondary: str

    # ── Acentos ─────────────────────────────────────────────
    accent_blue: str
    accent_green: str
    accent_red: str
    accent_orange: str
    accent_purple: str

    # ── Elementos estructurales ─────────────────────────────
    beam_color: str
    support_color: str
    load_color: str
    moment_color: str
    distributed_color: str

    # ── Diagramas ───────────────────────────────────────────
    shear_positive: str
    shear_negative: str
    moment_positive: str
    moment_negative: str

    # ── Utilidades de canvas ────────────────────────────────
    grid_color: str
    dimension_color: str
    critical_zone: str


# ── Paletas predefinidas ────────────────────────────────────
DARK_PALETTE = ColorPalette(
    bg_primary='#0d1117',
    bg_secondary='#161b22',
    bg_tertiary='#21262d',
    border='#30363d',
    text_primary='#e6edf3',
    text_secondary='#8b949e',
    accent_blue='#58a6ff',
    accent_green='#3fb950',
    accent_red='#f85149',
    accent_orange='#d29922',
    accent_purple='#bc8cff',
    beam_color='#58a6ff',
    support_color='#d29922',
    load_color='#f85149',
    moment_color='#bc8cff',
    distributed_color='#3fb950',
    shear_positive='#58a6ff',
    shear_negative='#f85149',
    moment_positive='#3fb950',
    moment_negative='#d29922',
    grid_color='#21262d',
    dimension_color='#8b949e',
    critical_zone='#ff7b72',
)

LIGHT_PALETTE = ColorPalette(
    bg_primary='#ffffff',
    bg_secondary='#f6f8fa',
    bg_tertiary='#eaeef2',
    border='#d0d7de',
    text_primary='#1f2328',
    text_secondary='#656d76',
    accent_blue='#0969da',
    accent_green='#1a7f37',
    accent_red='#cf222e',
    accent_orange='#9a6700',
    accent_purple='#8250df',
    beam_color='#0969da',
    support_color='#9a6700',
    load_color='#cf222e',
    moment_color='#8250df',
    distributed_color='#1a7f37',
    shear_positive='#0969da',
    shear_negative='#cf222e',
    moment_positive='#1a7f37',
    moment_negative='#9a6700',
    grid_color='#eaeef2',
    dimension_color='#656d76',
    critical_zone='#ff8182',
)


class ThemeColors:
    """
    Gestor centralizado de colores de la aplicación.

    Mantiene el tema activo y proporciona acceso a colores
    como instancias de ``QColor``.  Se utiliza como singleton
    a través de la instancia global ``theme_colors``.

    Ejemplo de uso::

        from app.render.colors import theme_colors
        color = theme_colors.get_color('beam_color')
        pen = QPen(color, 2)
    """

    _PALETTES: ClassVar[dict[Theme, ColorPalette]] = {
        Theme.DARK: DARK_PALETTE,
        Theme.LIGHT: LIGHT_PALETTE,
    }

    def __init__(self, theme: Theme = Theme.DARK) -> None:
        self._theme: Theme = theme
        self._palette: ColorPalette = self._PALETTES[theme]
        self._cache: dict[str, QColor] = {}

    # ── Propiedades ─────────────────────────────────────────

    @property
    def theme(self) -> Theme:
        """Tema activo actual."""
        return self._theme

    @property
    def palette(self) -> ColorPalette:
        """Paleta de colores activa."""
        return self._palette

    @property
    def is_dark(self) -> bool:
        """``True`` si el tema activo es oscuro."""
        return self._theme is Theme.DARK

    # ── Acceso a colores ────────────────────────────────────

    def get_color(self, name: str) -> QColor:
        """
        Devuelve un ``QColor`` para el nombre de color indicado.

        Args:
            name: Nombre del atributo de color en la paleta (p.ej. ``'beam_color'``).

        Returns:
            Instancia de ``QColor`` con el valor del color solicitado.

        Raises:
            AttributeError: Si el nombre de color no existe en la paleta.
        """
        cached = self._cache.get(name)
        if cached is not None:
            return cached

        hex_value: str = getattr(self._palette, name)
        color = QColor(hex_value)
        self._cache[name] = color
        return color

    def get_color_with_alpha(self, name: str, alpha: int) -> QColor:
        """
        Devuelve un ``QColor`` con transparencia personalizada.

        Args:
            name: Nombre del atributo de color.
            alpha: Valor de alfa (0-255, donde 255 es opaco).

        Returns:
            Nueva instancia de ``QColor`` con el alfa aplicado.
        """
        color = QColor(self.get_color(name))
        color.setAlpha(max(0, min(255, alpha)))
        return color

    def get_hex(self, name: str) -> str:
        """
        Devuelve el valor hexadecimal del color.

        Args:
            name: Nombre del atributo de color.

        Returns:
            Cadena hexadecimal (p.ej. ``'#58a6ff'``).
        """
        return str(getattr(self._palette, name))

    # ── Cambio de tema ──────────────────────────────────────

    def set_theme(self, theme: Theme) -> None:
        """
        Cambia el tema activo.

        Limpia la caché de colores y establece la nueva paleta.

        Args:
            theme: Nuevo tema a aplicar.
        """
        if theme is self._theme:
            return
        self._theme = theme
        self._palette = self._PALETTES[theme]
        self._cache.clear()

    def toggle_theme(self) -> Theme:
        """
        Alterna entre tema oscuro y claro.

        Returns:
            El nuevo tema activo tras la alternancia.
        """
        new_theme = Theme.LIGHT if self._theme is Theme.DARK else Theme.DARK
        self.set_theme(new_theme)
        return new_theme

    # ── Acceso directo a colores frecuentes ─────────────────

    @property
    def beam(self) -> QColor:
        """Color de la viga."""
        return self.get_color('beam_color')

    @property
    def support(self) -> QColor:
        """Color de los apoyos."""
        return self.get_color('support_color')

    @property
    def load(self) -> QColor:
        """Color de las cargas puntuales."""
        return self.get_color('load_color')

    @property
    def moment(self) -> QColor:
        """Color de los momentos."""
        return self.get_color('moment_color')

    @property
    def distributed(self) -> QColor:
        """Color de las cargas distribuidas."""
        return self.get_color('distributed_color')

    @property
    def text(self) -> QColor:
        """Color de texto principal."""
        return self.get_color('text_primary')

    @property
    def text_dim(self) -> QColor:
        """Color de texto secundario."""
        return self.get_color('text_secondary')

    @property
    def background(self) -> QColor:
        """Color de fondo principal."""
        return self.get_color('bg_primary')

    @property
    def grid(self) -> QColor:
        """Color de la rejilla."""
        return self.get_color('grid_color')

    @property
    def dimension(self) -> QColor:
        """Color de las líneas de cota."""
        return self.get_color('dimension_color')

    def __repr__(self) -> str:
        return f"ThemeColors(theme={self._theme.name})"


# ── Instancia global (singleton de facto) ───────────────────
theme_colors = ThemeColors(Theme.DARK)
