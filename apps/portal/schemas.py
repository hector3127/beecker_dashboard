"""Estructuras de datos de las vistas nuevas del portal."""

from dataclasses import dataclass

"""BKD.120.003 - Modelos del portal
Estructuras inmutables que viajan entre los servicios de lectura, los
resumenes y las plantillas.
"""


@dataclass(frozen=True, slots=True)
class ProjectView:
    """Un proyecto del portafolio tal como lo muestran las pantallas."""

    project_id: str
    name: str
    client: str
    delivery_manager: str
    service: str
    status_category: str
    health: str
    risk_level: str
    progress_percent: int
    delay_days: int
    budget_hours: float
    burn_hours: float
    etc_hours: float


@dataclass(frozen=True, slots=True)
class HoursSummary:
    """Horas planeadas, usadas y por terminar de los proyectos."""

    budget_hours: int
    burn_hours: int
    etc_hours: int
    progress_percent: int


@dataclass(frozen=True, slots=True)
class PeriodLabel:
    """Trimestre en curso con sus fechas ya escritas para mostrar."""

    start: str
    end: str


@dataclass(frozen=True, slots=True)
class HealthCount:
    """Proyectos en ejecucion separados por salud."""

    on_time: int
    at_risk: int
    critical: int

    @property
    def total(self) -> int:
        """Total de proyectos contados."""
        return self.on_time + self.at_risk + self.critical


@dataclass(frozen=True, slots=True)
class PortfolioSummary:
    """Totales del portafolio para las tarjetas de Operativa."""

    in_progress: int
    paused: int
    health: HealthCount
    on_time_percent: int


@dataclass(frozen=True, slots=True)
class DeliveryManagerSummary:
    """Resumen de un Delivery Manager para su tarjeta."""

    name: str
    initials: str
    in_progress: int
    paused: int
    health: HealthCount
    high_risk: int
    on_time_width: float
    at_risk_width: float
    critical_width: float


@dataclass(frozen=True, slots=True)
class DonutSegment:
    """Un arco de la dona de salud del portafolio."""

    label: str
    count: int
    percent: int
    color: str
    dash: float
    gap: float
    offset: float


@dataclass(frozen=True, slots=True)
class DecisionItem:
    """Proyecto que requiere una decision de la direccion."""

    project_id: str
    name: str
    delivery_manager: str
    client: str
    is_critical: bool
    reason: str
    action: str
