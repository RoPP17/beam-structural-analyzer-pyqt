"""
Sistema de conversión de unidades para análisis estructural.

Soporta unidades de longitud, fuerza, momento y carga distribuida
con conversión automática entre sistemas métrico e imperial.
"""

from __future__ import annotations

from enum import Enum
from typing import Final


class UnitCategory(Enum):
    """Categorías de unidades disponibles."""
    LENGTH = "length"
    FORCE = "force"
    MOMENT = "moment"
    DISTRIBUTED_LOAD = "distributed_load"
    STRESS = "stress"


class LengthUnit(Enum):
    """Unidades de longitud."""
    M = "m"
    CM = "cm"
    MM = "mm"
    FT = "ft"
    IN = "in"


class ForceUnit(Enum):
    """Unidades de fuerza."""
    N = "N"
    KN = "kN"
    LB = "lb"
    KGF = "kgf"


class MomentUnit(Enum):
    """Unidades de momento."""
    N_M = "N·m"
    KN_M = "kN·m"
    LB_FT = "lb·ft"


class DistributedLoadUnit(Enum):
    """Unidades de carga distribuida."""
    N_PER_M = "N/m"
    KN_PER_M = "kN/m"
    LB_PER_FT = "lb/ft"


class StressUnit(Enum):
    """Unidades de esfuerzo / presión."""
    PA = "Pa"
    KPA = "kPa"
    MPA = "MPa"
    GPA = "GPa"
    PSI = "psi"


# ---------------------------------------------------------------------------
# Factores de conversión a unidades SI base (m, N, N·m, N/m, Pa)
# ---------------------------------------------------------------------------

_LENGTH_TO_M: Final[dict[str, float]] = {
    "m": 1.0,
    "cm": 0.01,
    "mm": 0.001,
    "ft": 0.3048,
    "in": 0.0254,
}

_FORCE_TO_N: Final[dict[str, float]] = {
    "N": 1.0,
    "kN": 1_000.0,
    "lb": 4.4482216152605,
    "kgf": 9.80665,
}

_MOMENT_TO_NM: Final[dict[str, float]] = {
    "N·m": 1.0,
    "kN·m": 1_000.0,
    "lb·ft": 1.3558179483314,
}

_DISTRIBUTED_TO_NPM: Final[dict[str, float]] = {
    "N/m": 1.0,
    "kN/m": 1_000.0,
    "lb/ft": 14.593902937206,
}

_STRESS_TO_PA: Final[dict[str, float]] = {
    "Pa": 1.0,
    "kPa": 1_000.0,
    "MPa": 1_000_000.0,
    "GPa": 1_000_000_000.0,
    "psi": 6_894.757293168,
}

_CONVERSION_TABLES: Final[dict[str, dict[str, float]]] = {
    UnitCategory.LENGTH.value: _LENGTH_TO_M,
    UnitCategory.FORCE.value: _FORCE_TO_N,
    UnitCategory.MOMENT.value: _MOMENT_TO_NM,
    UnitCategory.DISTRIBUTED_LOAD.value: _DISTRIBUTED_TO_NPM,
    UnitCategory.STRESS.value: _STRESS_TO_PA,
}

# Map every unit string to its category for auto-detection
_UNIT_TO_CATEGORY: Final[dict[str, str]] = {}
for _cat, _table in _CONVERSION_TABLES.items():
    for _u in _table:
        _UNIT_TO_CATEGORY[_u] = _cat


def _resolve_unit_label(unit: str | LengthUnit | ForceUnit | MomentUnit
                        | DistributedLoadUnit | StressUnit) -> str:
    """Devuelve la etiqueta de texto de cualquier especificador de unidad."""
    if isinstance(unit, Enum):
        return unit.value
    return unit


def detect_category(unit: str | Enum) -> UnitCategory:
    """Detecta la categoría de una unidad dada.

    Args:
        unit: Etiqueta de unidad o enumerador.

    Returns:
        La categoría a la que pertenece la unidad.

    Raises:
        ValueError: Si la unidad no es reconocida.
    """
    label = _resolve_unit_label(unit)
    cat_value = _UNIT_TO_CATEGORY.get(label)
    if cat_value is None:
        raise ValueError(f"Unidad desconocida: '{label}'")
    return UnitCategory(cat_value)


def convert(value: float,
            from_unit: str | Enum,
            to_unit: str | Enum) -> float:
    """Convierte un valor de una unidad a otra dentro de la misma categoría.

    Args:
        value: Valor numérico a convertir.
        from_unit: Unidad de origen.
        to_unit: Unidad de destino.

    Returns:
        Valor convertido.

    Raises:
        ValueError: Si las unidades no pertenecen a la misma categoría
                    o no son reconocidas.
    """
    from_label = _resolve_unit_label(from_unit)
    to_label = _resolve_unit_label(to_unit)

    if from_label == to_label:
        return value

    from_cat = _UNIT_TO_CATEGORY.get(from_label)
    to_cat = _UNIT_TO_CATEGORY.get(to_label)

    if from_cat is None:
        raise ValueError(f"Unidad de origen desconocida: '{from_label}'")
    if to_cat is None:
        raise ValueError(f"Unidad de destino desconocida: '{to_label}'")
    if from_cat != to_cat:
        raise ValueError(
            f"Las unidades '{from_label}' y '{to_label}' pertenecen a "
            f"categorías distintas ({from_cat}, {to_cat}) y no se pueden "
            f"convertir entre sí."
        )

    table = _CONVERSION_TABLES[from_cat]
    base_value = value * table[from_label]
    return base_value / table[to_label]


def convert_to_si(value: float, unit: str | Enum) -> float:
    """Convierte un valor a la unidad base SI de su categoría.

    Args:
        value: Valor numérico.
        unit: Unidad actual.

    Returns:
        Valor en unidad SI base (m, N, N·m, N/m, Pa).
    """
    label = _resolve_unit_label(unit)
    cat = _UNIT_TO_CATEGORY.get(label)
    if cat is None:
        raise ValueError(f"Unidad desconocida: '{label}'")
    return value * _CONVERSION_TABLES[cat][label]


def convert_from_si(value: float, unit: str | Enum) -> float:
    """Convierte un valor desde la unidad base SI a la unidad indicada.

    Args:
        value: Valor en unidad SI base.
        unit: Unidad de destino.

    Returns:
        Valor convertido.
    """
    label = _resolve_unit_label(unit)
    cat = _UNIT_TO_CATEGORY.get(label)
    if cat is None:
        raise ValueError(f"Unidad desconocida: '{label}'")
    return value / _CONVERSION_TABLES[cat][label]


# ---------------------------------------------------------------------------
# Formateo de valores para la interfaz gráfica
# ---------------------------------------------------------------------------

# Decimales por defecto según categoría
_DEFAULT_DECIMALS: Final[dict[str, int]] = {
    UnitCategory.LENGTH.value: 3,
    UnitCategory.FORCE.value: 2,
    UnitCategory.MOMENT.value: 2,
    UnitCategory.DISTRIBUTED_LOAD.value: 2,
    UnitCategory.STRESS.value: 2,
}


def format_value(value: float,
                 unit: str | Enum,
                 decimals: int | None = None,
                 include_unit: bool = True) -> str:
    """Formatea un valor numérico con su unidad para mostrar en la interfaz.

    Args:
        value: Valor numérico.
        unit: Unidad asociada al valor.
        decimals: Número de decimales (``None`` usa el valor por defecto).
        include_unit: Si se incluye la etiqueta de la unidad.

    Returns:
        Cadena formateada, p. ej. ``"12.50 kN"`` o ``"12.50"``.
    """
    label = _resolve_unit_label(unit)
    if decimals is None:
        cat = _UNIT_TO_CATEGORY.get(label)
        decimals = _DEFAULT_DECIMALS.get(cat, 3) if cat else 3

    formatted = f"{value:,.{decimals}f}"
    if include_unit:
        return f"{formatted} {label}"
    return formatted


# ---------------------------------------------------------------------------
# Clase de estado de sistema de unidades
# ---------------------------------------------------------------------------

class UnitSystem:
    """Estado actual del sistema de unidades utilizado en la aplicación.

    Permite definir qué unidad de cada categoría se emplea para la
    entrada/salida de datos, y convertir valores de forma transparente.
    """

    def __init__(
        self,
        length: LengthUnit = LengthUnit.M,
        force: ForceUnit = ForceUnit.KN,
        moment: MomentUnit = MomentUnit.KN_M,
        distributed_load: DistributedLoadUnit = DistributedLoadUnit.KN_PER_M,
        stress: StressUnit = StressUnit.MPA,
    ) -> None:
        self.length: LengthUnit = length
        self.force: ForceUnit = force
        self.moment: MomentUnit = moment
        self.distributed_load: DistributedLoadUnit = distributed_load
        self.stress: StressUnit = stress

    # -- Acceso rápido por categoría -----------------------------------

    def unit_for(self, category: UnitCategory) -> Enum:
        """Devuelve la unidad configurada para la categoría indicada."""
        mapping: dict[UnitCategory, Enum] = {
            UnitCategory.LENGTH: self.length,
            UnitCategory.FORCE: self.force,
            UnitCategory.MOMENT: self.moment,
            UnitCategory.DISTRIBUTED_LOAD: self.distributed_load,
            UnitCategory.STRESS: self.stress,
        }
        result = mapping.get(category)
        if result is None:
            raise ValueError(f"Categoría no soportada: {category}")
        return result

    def label_for(self, category: UnitCategory) -> str:
        """Devuelve la etiqueta de texto de la unidad configurada."""
        return self.unit_for(category).value

    # -- Conversión con respecto al sistema actual ---------------------

    def to_si(self, value: float, category: UnitCategory) -> float:
        """Convierte *value* (en la unidad actual) a SI base."""
        return convert_to_si(value, self.unit_for(category))

    def from_si(self, value: float, category: UnitCategory) -> float:
        """Convierte *value* (en SI base) a la unidad actual."""
        return convert_from_si(value, self.unit_for(category))

    def format(self, value: float, category: UnitCategory,
               decimals: int | None = None) -> str:
        """Formatea un valor (ya en la unidad actual) para la UI."""
        return format_value(value, self.unit_for(category), decimals)

    # -- Presets --------------------------------------------------------

    @classmethod
    def metric_kn(cls) -> UnitSystem:
        """Sistema métrico con fuerzas en kN (por defecto)."""
        return cls(
            length=LengthUnit.M,
            force=ForceUnit.KN,
            moment=MomentUnit.KN_M,
            distributed_load=DistributedLoadUnit.KN_PER_M,
            stress=StressUnit.MPA,
        )

    @classmethod
    def metric_n(cls) -> UnitSystem:
        """Sistema métrico con fuerzas en N."""
        return cls(
            length=LengthUnit.M,
            force=ForceUnit.N,
            moment=MomentUnit.N_M,
            distributed_load=DistributedLoadUnit.N_PER_M,
            stress=StressUnit.PA,
        )

    @classmethod
    def imperial(cls) -> UnitSystem:
        """Sistema imperial (lb, ft)."""
        return cls(
            length=LengthUnit.FT,
            force=ForceUnit.LB,
            moment=MomentUnit.LB_FT,
            distributed_load=DistributedLoadUnit.LB_PER_FT,
            stress=StressUnit.PSI,
        )

    # -- Serialización --------------------------------------------------

    def to_dict(self) -> dict[str, str]:
        """Serializa el estado del sistema de unidades a diccionario."""
        return {
            "length": self.length.value,
            "force": self.force.value,
            "moment": self.moment.value,
            "distributed_load": self.distributed_load.value,
            "stress": self.stress.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> UnitSystem:
        """Reconstruye un ``UnitSystem`` desde un diccionario serializado."""
        # Helper to find enum member by value
        def _find(enum_cls: type[Enum], value: str) -> Enum:
            for member in enum_cls:
                if member.value == value:
                    return member
            raise ValueError(f"Valor '{value}' no encontrado en {enum_cls.__name__}")

        return cls(
            length=_find(LengthUnit, data.get("length", "m")),          # type: ignore[arg-type]
            force=_find(ForceUnit, data.get("force", "kN")),            # type: ignore[arg-type]
            moment=_find(MomentUnit, data.get("moment", "kN·m")),      # type: ignore[arg-type]
            distributed_load=_find(                                     # type: ignore[arg-type]
                DistributedLoadUnit, data.get("distributed_load", "kN/m")
            ),
            stress=_find(StressUnit, data.get("stress", "MPa")),       # type: ignore[arg-type]
        )

    def __repr__(self) -> str:
        return (
            f"UnitSystem(length={self.length.value}, force={self.force.value}, "
            f"moment={self.moment.value}, distributed_load={self.distributed_load.value}, "
            f"stress={self.stress.value})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, UnitSystem):
            return NotImplemented
        return self.to_dict() == other.to_dict()
