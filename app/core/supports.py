"""
Definiciones de tipos de apoyo para vigas.

Cada apoyo conoce sus grados de libertad restringidos, el número de
incógnitas de reacción que genera y almacena los valores de reacción
una vez resuelto el modelo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SupportType(Enum):
    """Tipos de apoyo disponibles.

    Cada valor indica las restricciones cinemáticas que impone el apoyo:

    * **PINNED** – restringe desplazamiento horizontal y vertical (2 incógnitas).
    * **ROLLER** – restringe solo desplazamiento vertical (1 incógnita).
    * **FIXED**  – restringe desplazamiento horizontal, vertical y rotación (3 incógnitas).
    """
    PINNED = "pinned"
    ROLLER = "roller"
    FIXED = "fixed"


# Información estática de cada tipo de apoyo
_SUPPORT_INFO: dict[SupportType, dict[str, Any]] = {
    SupportType.PINNED: {
        "num_unknowns": 2,
        "has_reaction_x": True,
        "has_reaction_y": True,
        "has_reaction_moment": False,
        "description_es": "Apoyo articulado (fijo)",
        "symbol": "△",
    },
    SupportType.ROLLER: {
        "num_unknowns": 1,
        "has_reaction_x": False,
        "has_reaction_y": True,
        "has_reaction_moment": False,
        "description_es": "Apoyo de rodillo",
        "symbol": "○",
    },
    SupportType.FIXED: {
        "num_unknowns": 3,
        "has_reaction_x": True,
        "has_reaction_y": True,
        "has_reaction_moment": True,
        "description_es": "Empotramiento",
        "symbol": "▐",
    },
}


@dataclass
class Support:
    """Representa un apoyo en la viga.

    Attributes:
        support_type: Tipo de apoyo (PINNED, ROLLER, FIXED).
        position: Posición *x* del apoyo a lo largo de la viga [unidades de longitud].
        name: Nombre descriptivo del apoyo (p. ej. ``"A"``, ``"B"``).
        reaction_x: Reacción horizontal resuelta (positiva → derecha).
        reaction_y: Reacción vertical resuelta (positiva → arriba).
        reaction_moment: Momento de reacción resuelto (positivo → antihorario).
    """
    support_type: SupportType
    position: float
    name: str = ""
    reaction_x: float | None = field(default=None, repr=False)
    reaction_y: float | None = field(default=None, repr=False)
    reaction_moment: float | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.position < 0:
            raise ValueError(
                f"La posición del apoyo debe ser ≥ 0, se recibió {self.position}"
            )
        if not self.name:
            self.name = f"Apoyo en x={self.position}"

    # -- Propiedades derivadas del tipo ---------------------------------

    @property
    def num_unknowns(self) -> int:
        """Número de incógnitas de reacción que genera este apoyo."""
        return _SUPPORT_INFO[self.support_type]["num_unknowns"]

    @property
    def has_reaction_x(self) -> bool:
        """Indica si el apoyo genera reacción horizontal."""
        return _SUPPORT_INFO[self.support_type]["has_reaction_x"]

    @property
    def has_reaction_y(self) -> bool:
        """Indica si el apoyo genera reacción vertical."""
        return _SUPPORT_INFO[self.support_type]["has_reaction_y"]

    @property
    def has_reaction_moment(self) -> bool:
        """Indica si el apoyo genera momento de reacción."""
        return _SUPPORT_INFO[self.support_type]["has_reaction_moment"]

    @property
    def description(self) -> str:
        """Descripción en español del tipo de apoyo."""
        return _SUPPORT_INFO[self.support_type]["description_es"]

    @property
    def symbol(self) -> str:
        """Símbolo representativo del apoyo."""
        return _SUPPORT_INFO[self.support_type]["symbol"]

    # -- Gestión de reacciones ------------------------------------------

    @property
    def is_solved(self) -> bool:
        """Indica si las reacciones de este apoyo han sido calculadas."""
        if self.has_reaction_y and self.reaction_y is None:
            return False
        if self.has_reaction_x and self.reaction_x is None:
            return False
        if self.has_reaction_moment and self.reaction_moment is None:
            return False
        return True

    def clear_reactions(self) -> None:
        """Limpia los valores de reacción (estado sin resolver)."""
        self.reaction_x = None
        self.reaction_y = None
        self.reaction_moment = None

    def get_reactions_summary(self) -> dict[str, float | None]:
        """Devuelve un resumen de las reacciones disponibles.

        Solo incluye las reacciones relevantes para el tipo de apoyo.
        """
        summary: dict[str, float | None] = {}
        if self.has_reaction_x:
            summary["Rx"] = self.reaction_x
        if self.has_reaction_y:
            summary["Ry"] = self.reaction_y
        if self.has_reaction_moment:
            summary["M"] = self.reaction_moment
        return summary

    # -- Serialización --------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serializa el apoyo a un diccionario para guardado de proyecto."""
        data: dict[str, Any] = {
            "support_type": self.support_type.value,
            "position": self.position,
            "name": self.name,
        }
        if self.reaction_x is not None:
            data["reaction_x"] = self.reaction_x
        if self.reaction_y is not None:
            data["reaction_y"] = self.reaction_y
        if self.reaction_moment is not None:
            data["reaction_moment"] = self.reaction_moment
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Support:
        """Reconstruye un ``Support`` desde un diccionario serializado.

        Args:
            data: Diccionario con las claves ``support_type``, ``position``,
                  ``name`` y opcionalmente ``reaction_x``, ``reaction_y``,
                  ``reaction_moment``.

        Returns:
            Instancia de ``Support``.
        """
        support_type = SupportType(data["support_type"])
        return cls(
            support_type=support_type,
            position=float(data["position"]),
            name=data.get("name", ""),
            reaction_x=data.get("reaction_x"),
            reaction_y=data.get("reaction_y"),
            reaction_moment=data.get("reaction_moment"),
        )

    def __str__(self) -> str:
        status = "resuelto" if self.is_solved else "sin resolver"
        return (
            f"{self.symbol} {self.name} ({self.description}) "
            f"en x = {self.position} [{status}]"
        )
