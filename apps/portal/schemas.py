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
    slug: str
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


@dataclass(frozen=True, slots=True)
class ProjectRow:
    """Renglon de la tabla de proyectos de un Delivery Manager."""

    project_id: str
    name: str
    client: str
    status_label: str
    status_code: str
    detail: str
    progress_percent: int
    etc_hours: int
    risk_label: str
    row_class: str
    client_slug: str = ""


@dataclass(frozen=True, slots=True)
class ShareRow:
    """Cuantos proyectos en ejecucion hay en cada estado."""

    label: str
    status_code: str
    color: str
    count: int
    percent: int


@dataclass(frozen=True, slots=True)
class ManagerDetail:
    """Detalle completo de un Delivery Manager."""

    name: str
    initials: str
    total: int
    in_progress: int
    paused: int
    health: HealthCount
    high_risk: int
    high_risk_note: str
    rows: tuple[ProjectRow, ...]
    shares: tuple[ShareRow, ...]


@dataclass(frozen=True, slots=True)
class AccountRow:
    """Renglon de la tabla de proyectos de una cuenta."""

    project_id: str
    name: str
    delivery_manager: str
    status_label: str
    status_code: str
    detail: str
    progress_percent: int
    row_class: str


@dataclass(frozen=True, slots=True)
class AccountDetail:
    """Detalle completo de una cuenta (cliente)."""

    name: str
    total: int
    in_progress: int
    paused: int
    health: HealthCount
    rows: tuple[AccountRow, ...]
    shares: tuple[ShareRow, ...]


@dataclass(frozen=True, slots=True)
class SuspendedRow:
    """Un proyecto suspendido."""

    project_id: str
    name: str
    client: str
    delivery_manager: str
    progress_percent: int
    etc_hours: int
    client_slug: str = ""


@dataclass(frozen=True, slots=True)
class SuspendedSummary:
    """Resumen de los proyectos suspendidos."""

    count: int
    by_manager: tuple[tuple[str, int], ...]
    etc_hours: int
    rows: tuple[SuspendedRow, ...]


@dataclass(frozen=True, slots=True)
class EvaProject:
    """Un proyecto AER o T&M vigente en MPB."""

    manager: str
    client: str
    project_id: str
    service: str
    fte: float
    role_fte: dict[str, float]
    name: str
    start: str
    end: str
    budget: float
    burn: float | None
    etc: float | None
    progress: float | None
    renewal_days: int | None
    etc_bad: bool
    progress_bad: bool
    renewal_bad: bool


@dataclass(frozen=True, slots=True)
class EvaManagerRow:
    """Proyectos por servicio y personas por rol de un Delivery Manager."""

    name: str
    services: tuple[int, ...]
    roles: tuple[float, ...]
    total_fte: float


@dataclass(frozen=True, slots=True)
class Eva1View:
    """Pantalla EVA 1 completa (AER y T&M)."""

    total_projects: int
    total_fte: float
    services: tuple[str, ...]
    roles: tuple[str, ...]
    managers: tuple[EvaManagerRow, ...]
    totals: EvaManagerRow
    projects: tuple[EvaProject, ...]


@dataclass(frozen=True, slots=True)
class StageCount:
    """Tareas de Azure DevOps de una etapa: total, cerradas y pendientes."""

    total: int
    closed: int
    pending: int
    alert: bool


@dataclass(frozen=True, slots=True)
class Eva2Project:
    """Un proyecto IXB o RaaS vigente."""

    manager: str
    project_id: str
    service: str
    name: str
    status: str
    status_code: str
    start: str
    end: str
    deviation_days: int | None
    budget: float
    burn: float
    etc: float
    progress: float
    progress_bad: bool
    stages: tuple[StageCount, ...]
    risks: int


@dataclass(frozen=True, slots=True)
class Eva2Row:
    """Fila de un pivote por Delivery Manager (cuenta por columna)."""

    name: str
    counts: tuple[int, ...]
    total: int


@dataclass(frozen=True, slots=True)
class Eva2View:
    """Pantalla EVA 2 completa (IXB y RaaS)."""

    total_projects: int
    suspended_count: int
    suspended_note: str
    services: tuple[str, ...]
    service_rows: tuple[Eva2Row, ...]
    service_totals: Eva2Row
    status_rows: tuple[Eva2Row, ...]
    status_totals: Eva2Row
    projects: tuple[Eva2Project, ...]
