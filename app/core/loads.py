"""
Definiciones de todos los tipos de carga aplicables a una viga.

Incluye cargas puntuales, distribuidas uniformes, triangulares,
trapezoidales, momentos concentrados y cargas inclinadas.  Cada tipo
implementa el cálculo de resultante, posición de la resultante,
momento respecto a un punto y descomposición en componentes.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class LoadType(Enum):
    """Tipos de carga disponibles."""
    POINT = "point"
    DISTRIBUTED_UNIFORM = "distributed_uniform"
    TRIANGULAR = "triangular"
    TRAPEZOIDAL = "trapezoidal"
    MOMENT = "moment"
    INCLINED = "inclined"


# ======================================================================
# Clase base abstracta
# ======================================================================

@dataclass
class Load(ABC):
    """Clase base abstracta para todas las cargas.

    Convención de signos:
    - Magnitud de carga ingresada como positiva por el usuario.
    - La carga actúa **hacia abajo** (negativa en eje Y) salvo que
      se especifique lo contrario mediante ángulo.
    - Momentos concentrados positivos: sentido antihorario.

    Attributes:
        name: Nombre descriptivo de la carga.
    """
    name: str = ""

    @property
    @abstractmethod
    def load_type(self) -> LoadType:
        """Tipo de carga."""

    @abstractmethod
    def resultant_force(self) -> float:
        """Fuerza resultante vertical (positiva ↑) de esta carga."""

    @abstractmethod
    def resultant_position(self) -> float:
        """Posición *x* donde actúa la resultante de la carga."""

    @abstractmethod
    def get_fy(self) -> float:
        """Componente vertical de la resultante (positiva ↑)."""

    @abstractmethod
    def get_fx(self) -> float:
        """Componente horizontal de la resultante (positiva →)."""

    def moment_about(self, point: float) -> float:
        """Momento que genera esta carga respecto a un punto *x*.

        Positivo = antihorario.

        Args:
            point: Coordenada *x* del punto de referencia.

        Returns:
            Momento resultante respecto al punto.
        """
        fy = self.get_fy()
        x_r = self.resultant_position()
        # Fuerza vertical positiva a la derecha del punto → momento antihorario (positivo)
        return fy * (x_r - point)

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """Serializa la carga a diccionario."""

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Load:
        """Fábrica que reconstruye cualquier carga desde su diccionario.

        Args:
            data: Diccionario con clave ``load_type`` y los parámetros
                  de la carga específica.

        Returns:
            Instancia de la subclase correspondiente.
        """
        lt = LoadType(data["load_type"])
        builders: dict[LoadType, type[Load]] = {
            LoadType.POINT: PointLoad,
            LoadType.DISTRIBUTED_UNIFORM: DistributedLoad,
            LoadType.TRIANGULAR: TriangularLoad,
            LoadType.TRAPEZOIDAL: TrapezoidalLoad,
            LoadType.MOMENT: MomentLoad,
            LoadType.INCLINED: InclinedLoad,
        }
        cls = builders[lt]
        return cls._from_dict_impl(data)  # type: ignore[attr-defined]

    @classmethod
    @abstractmethod
    def _from_dict_impl(cls, data: dict[str, Any]) -> Load:
        """Implementación de deserialización específica de cada subclase."""


# ======================================================================
# Carga puntual
# ======================================================================

@dataclass
class PointLoad(Load):
    """Carga puntual vertical.

    Attributes:
        position: Posición *x* sobre la viga.
        magnitude: Magnitud de la carga (valor positivo = carga hacia abajo).
        angle: Ángulo respecto a la horizontal en grados.
                90° = vertical hacia abajo (por defecto).
    """
    position: float = 0.0
    magnitude: float = 0.0
    angle: float = 90.0

    @property
    def load_type(self) -> LoadType:
        return LoadType.POINT

    def get_fy(self) -> float:
        """Componente vertical: negativa (hacia abajo)."""
        return -self.magnitude * math.sin(math.radians(self.angle))

    def get_fx(self) -> float:
        """Componente horizontal."""
        return self.magnitude * math.cos(math.radians(self.angle))

    def resultant_force(self) -> float:
        return self.get_fy()

    def resultant_position(self) -> float:
        return self.position

    def to_dict(self) -> dict[str, Any]:
        return {
            "load_type": self.load_type.value,
            "name": self.name,
            "position": self.position,
            "magnitude": self.magnitude,
            "angle": self.angle,
        }

    @classmethod
    def _from_dict_impl(cls, data: dict[str, Any]) -> PointLoad:
        return cls(
            name=data.get("name", ""),
            position=float(data["position"]),
            magnitude=float(data["magnitude"]),
            angle=float(data.get("angle", 90.0)),
        )


# ======================================================================
# Carga distribuida uniforme
# ======================================================================

@dataclass
class DistributedLoad(Load):
    """Carga distribuida uniforme.

    Attributes:
        start: Inicio del tramo cargado.
        end: Fin del tramo cargado.
        w: Intensidad de la carga (positiva = hacia abajo) [fuerza/longitud].
    """
    start: float = 0.0
    end: float = 0.0
    w: float = 0.0

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError(
                f"El extremo final ({self.end}) debe ser ≥ al inicio ({self.start})."
            )

    @property
    def load_type(self) -> LoadType:
        return LoadType.DISTRIBUTED_UNIFORM

    @property
    def length(self) -> float:
        """Longitud del tramo cargado."""
        return self.end - self.start

    def get_fy(self) -> float:
        """Resultante vertical: w * L hacia abajo (negativa)."""
        return -self.w * self.length

    def get_fx(self) -> float:
        return 0.0

    def resultant_force(self) -> float:
        return self.get_fy()

    def resultant_position(self) -> float:
        """Actúa en el centro del tramo."""
        return (self.start + self.end) / 2.0

    def intensity_at(self, x: float) -> float:
        """Intensidad de la carga en la posición *x*.

        Devuelve la intensidad como valor positivo dentro del tramo,
        0 fuera de él.
        """
        if self.start <= x <= self.end:
            return self.w
        return 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "load_type": self.load_type.value,
            "name": self.name,
            "start": self.start,
            "end": self.end,
            "w": self.w,
        }

    @classmethod
    def _from_dict_impl(cls, data: dict[str, Any]) -> DistributedLoad:
        return cls(
            name=data.get("name", ""),
            start=float(data["start"]),
            end=float(data["end"]),
            w=float(data["w"]),
        )


# ======================================================================
# Carga triangular
# ======================================================================

@dataclass
class TriangularLoad(Load):
    """Carga distribuida con variación lineal (triangular).

    Attributes:
        start: Inicio del tramo.
        end: Fin del tramo.
        w_start: Intensidad al inicio (positiva = abajo).
        w_end: Intensidad al final (positiva = abajo).
    """
    start: float = 0.0
    end: float = 0.0
    w_start: float = 0.0
    w_end: float = 0.0

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError(
                f"El extremo final ({self.end}) debe ser ≥ al inicio ({self.start})."
            )

    @property
    def load_type(self) -> LoadType:
        return LoadType.TRIANGULAR

    @property
    def length(self) -> float:
        return self.end - self.start

    def get_fy(self) -> float:
        """Resultante vertical del trapecio/triángulo (negativa = abajo)."""
        L = self.length
        return -(self.w_start + self.w_end) * L / 2.0

    def get_fx(self) -> float:
        return 0.0

    def resultant_force(self) -> float:
        return self.get_fy()

    def resultant_position(self) -> float:
        """Posición de la resultante según la distribución lineal.

        Para una distribución lineal de w_start a w_end, la resultante
        se descompone en un rectángulo + triángulo y se obtiene el centroide.
        """
        L = self.length
        if L == 0:
            return self.start

        total = self.w_start + self.w_end
        if abs(total) < 1e-15:
            return (self.start + self.end) / 2.0

        # Centroide de distribución lineal:
        # x_bar = start + L * (w_start + 2*w_end) / (3*(w_start + w_end))
        x_bar = self.start + L * (self.w_start + 2.0 * self.w_end) / (3.0 * total)
        return x_bar

    def intensity_at(self, x: float) -> float:
        """Intensidad de la carga en la posición *x* (interpolación lineal)."""
        if x < self.start or x > self.end:
            return 0.0
        L = self.length
        if L == 0:
            return self.w_start
        t = (x - self.start) / L
        return self.w_start + (self.w_end - self.w_start) * t

    def moment_about(self, point: float) -> float:
        """Momento respecto a un punto, calculado por integración directa.

        Para mayor precisión con distribuciones lineales se integra
        analíticamente en vez de usar la resultante puntual.
        """
        L = self.length
        if L == 0:
            return 0.0

        # ∫ w(x)·(x - point) dx  con  w(x) = w_start + (w_end - w_start)*(x - start)/L
        # La integral con signo negativo (carga abajo):
        # M = -∫_{start}^{end} [w_start + slope*(x-start)] * (x - point) dx
        slope = (self.w_end - self.w_start) / L
        a = self.start
        b = self.end

        # Expandir: integral de [w_start + slope*(x-a)] * (x - point) dx
        # = integral de [w_start*(x-point) + slope*(x-a)*(x-point)] dx

        def _antideriv(x: float) -> float:
            xp = x - point
            xa = x - a
            # w_start * (x - point) → w_start * ((x-point)^2/2)
            t1 = self.w_start * (xp ** 2) / 2.0
            # slope * (x - a) * (x - point)
            # = slope * (x^2 - (a+point)*x + a*point)
            # Integral: slope * (x^3/3 - (a+point)*x^2/2 + a*point*x)
            t2 = slope * (x ** 3 / 3.0 - (a + point) * x ** 2 / 2.0 + a * point * x)
            return t1 + t2

        return -(_antideriv(b) - _antideriv(a))

    def to_dict(self) -> dict[str, Any]:
        return {
            "load_type": self.load_type.value,
            "name": self.name,
            "start": self.start,
            "end": self.end,
            "w_start": self.w_start,
            "w_end": self.w_end,
        }

    @classmethod
    def _from_dict_impl(cls, data: dict[str, Any]) -> TriangularLoad:
        return cls(
            name=data.get("name", ""),
            start=float(data["start"]),
            end=float(data["end"]),
            w_start=float(data["w_start"]),
            w_end=float(data["w_end"]),
        )


# ======================================================================
# Carga trapezoidal (alias generalizado de la triangular)
# ======================================================================

@dataclass
class TrapezoidalLoad(Load):
    """Carga distribuida trapezoidal (caso general de variación lineal).

    Internamente idéntica a ``TriangularLoad`` pero con nombre
    semántico distinto.

    Attributes:
        start: Inicio del tramo.
        end: Fin del tramo.
        w_start: Intensidad al inicio (positiva = abajo).
        w_end: Intensidad al final (positiva = abajo).
    """
    start: float = 0.0
    end: float = 0.0
    w_start: float = 0.0
    w_end: float = 0.0

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError(
                f"El extremo final ({self.end}) debe ser ≥ al inicio ({self.start})."
            )

    @property
    def load_type(self) -> LoadType:
        return LoadType.TRAPEZOIDAL

    @property
    def length(self) -> float:
        return self.end - self.start

    def get_fy(self) -> float:
        L = self.length
        return -(self.w_start + self.w_end) * L / 2.0

    def get_fx(self) -> float:
        return 0.0

    def resultant_force(self) -> float:
        return self.get_fy()

    def resultant_position(self) -> float:
        L = self.length
        if L == 0:
            return self.start
        total = self.w_start + self.w_end
        if abs(total) < 1e-15:
            return (self.start + self.end) / 2.0
        return self.start + L * (self.w_start + 2.0 * self.w_end) / (3.0 * total)

    def intensity_at(self, x: float) -> float:
        """Intensidad de la carga en la posición *x* (interpolación lineal)."""
        if x < self.start or x > self.end:
            return 0.0
        L = self.length
        if L == 0:
            return self.w_start
        t = (x - self.start) / L
        return self.w_start + (self.w_end - self.w_start) * t

    def moment_about(self, point: float) -> float:
        """Momento respecto a un punto por integración analítica."""
        L = self.length
        if L == 0:
            return 0.0

        slope = (self.w_end - self.w_start) / L
        a = self.start
        b = self.end

        def _antideriv(x: float) -> float:
            xp = x - point
            t1 = self.w_start * (xp ** 2) / 2.0
            t2 = slope * (x ** 3 / 3.0 - (a + point) * x ** 2 / 2.0 + a * point * x)
            return t1 + t2

        return -(_antideriv(b) - _antideriv(a))

    def to_dict(self) -> dict[str, Any]:
        return {
            "load_type": self.load_type.value,
            "name": self.name,
            "start": self.start,
            "end": self.end,
            "w_start": self.w_start,
            "w_end": self.w_end,
        }

    @classmethod
    def _from_dict_impl(cls, data: dict[str, Any]) -> TrapezoidalLoad:
        return cls(
            name=data.get("name", ""),
            start=float(data["start"]),
            end=float(data["end"]),
            w_start=float(data["w_start"]),
            w_end=float(data["w_end"]),
        )


# ======================================================================
# Momento concentrado
# ======================================================================

@dataclass
class MomentLoad(Load):
    """Momento concentrado aplicado sobre la viga.

    Convención: positivo = antihorario (sagging).

    Attributes:
        position: Posición *x* sobre la viga.
        magnitude: Magnitud del momento (positivo = antihorario).
    """
    position: float = 0.0
    magnitude: float = 0.0

    @property
    def load_type(self) -> LoadType:
        return LoadType.MOMENT

    def get_fy(self) -> float:
        return 0.0

    def get_fx(self) -> float:
        return 0.0

    def resultant_force(self) -> float:
        return 0.0

    def resultant_position(self) -> float:
        return self.position

    def moment_about(self, point: float) -> float:
        """Un momento concentrado contribuye directamente, sin brazo de palanca.

        El momento aplicado antihorario se suma directamente.
        """
        # Momento concentrado se transfiere directamente a cualquier punto
        # (no depende de la distancia).
        return self.magnitude

    def to_dict(self) -> dict[str, Any]:
        return {
            "load_type": self.load_type.value,
            "name": self.name,
            "position": self.position,
            "magnitude": self.magnitude,
        }

    @classmethod
    def _from_dict_impl(cls, data: dict[str, Any]) -> MomentLoad:
        return cls(
            name=data.get("name", ""),
            position=float(data["position"]),
            magnitude=float(data["magnitude"]),
        )


# ======================================================================
# Carga inclinada
# ======================================================================

@dataclass
class InclinedLoad(Load):
    """Carga puntual inclinada con ángulo arbitrario.

    Attributes:
        position: Posición *x* sobre la viga.
        magnitude: Magnitud total de la carga.
        angle: Ángulo respecto a la horizontal en grados
               (0° = horizontal derecha, 90° = vertical abajo,
               270° = vertical arriba).
    """
    position: float = 0.0
    magnitude: float = 0.0
    angle: float = 45.0

    @property
    def load_type(self) -> LoadType:
        return LoadType.INCLINED

    def get_fy(self) -> float:
        """Componente vertical (negativa = abajo)."""
        return -self.magnitude * math.sin(math.radians(self.angle))

    def get_fx(self) -> float:
        """Componente horizontal (positiva = derecha)."""
        return self.magnitude * math.cos(math.radians(self.angle))

    def resultant_force(self) -> float:
        return self.get_fy()

    def resultant_position(self) -> float:
        return self.position

    def to_dict(self) -> dict[str, Any]:
        return {
            "load_type": self.load_type.value,
            "name": self.name,
            "position": self.position,
            "magnitude": self.magnitude,
            "angle": self.angle,
        }

    @classmethod
    def _from_dict_impl(cls, data: dict[str, Any]) -> InclinedLoad:
        return cls(
            name=data.get("name", ""),
            position=float(data["position"]),
            magnitude=float(data["magnitude"]),
            angle=float(data.get("angle", 45.0)),
        )


# ======================================================================
# Utilidades
# ======================================================================

def get_distributed_fy_up_to(load: Load, x: float) -> float:
    """Calcula la componente vertical de una carga distribuida desde su
    inicio hasta la posición *x* (para el método de secciones).

    Para cargas puntuales o momentos retorna 0 (se manejan aparte).

    Args:
        load: Carga a evaluar.
        x: Posición de corte.

    Returns:
        Fuerza vertical acumulada (negativa = abajo).
    """
    if isinstance(load, (DistributedLoad, TriangularLoad, TrapezoidalLoad)):
        a = load.start
        b = load.end
        if x <= a:
            return 0.0
        x_eff = min(x, b)
        L_seg = x_eff - a

        if isinstance(load, DistributedLoad):
            return -load.w * L_seg
        else:
            # Variación lineal: w(t) = w_start + (w_end - w_start) * (t - a) / (b - a)
            L_total = b - a
            if L_total == 0:
                return 0.0
            w_at_x = load.w_start + (load.w_end - load.w_start) * L_seg / L_total
            return -(load.w_start + w_at_x) * L_seg / 2.0

    return 0.0


def get_distributed_moment_up_to(load: Load, x: float, cut: float) -> float:
    """Calcula el momento respecto a *cut* de la porción de carga distribuida
    entre el inicio de la carga y la posición *x*.

    Args:
        load: Carga distribuida.
        x: Posición hasta la cual integrar.
        cut: Punto respecto al cual calcular el momento.

    Returns:
        Momento (positivo = antihorario).
    """
    if isinstance(load, DistributedLoad):
        a = load.start
        b = load.end
        if x <= a:
            return 0.0
        x_eff = min(x, b)
        L_seg = x_eff - a
        fy = -load.w * L_seg
        x_centroid = a + L_seg / 2.0
        return fy * (cut - x_centroid)

    if isinstance(load, (TriangularLoad, TrapezoidalLoad)):
        a = load.start
        b = load.end
        if x <= a:
            return 0.0
        x_eff = min(x, b)
        L_seg = x_eff - a
        L_total = b - a
        if L_total == 0:
            return 0.0

        w_a = load.w_start
        slope = (load.w_end - load.w_start) / L_total

        # Descomponer en rectángulo + triángulo
        w_at_x = w_a + slope * L_seg

        # Parte rectangular: w_a * L_seg, centroide en a + L_seg/2
        rect_fy = -w_a * L_seg
        rect_xc = a + L_seg / 2.0

        # Parte triangular: (w_at_x - w_a) * L_seg / 2, centroide en a + 2*L_seg/3
        tri_fy = -(w_at_x - w_a) * L_seg / 2.0
        tri_xc = a + 2.0 * L_seg / 3.0

        return rect_fy * (cut - rect_xc) + tri_fy * (cut - tri_xc)

    return 0.0
