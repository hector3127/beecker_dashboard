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
class TimeCost:
    """T y C: promedio de desviacion en dias y promedio de avance."""

    time_days: float | None = None
    cost_percent: float | None = None


NO_TIME_COST = TimeCost()


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
    time_cost: TimeCost = NO_TIME_COST


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
    time_cost: TimeCost = NO_TIME_COST


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
    cost_percent: float | None = None


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
    time_cost: TimeCost = NO_TIME_COST


@dataclass(frozen=True, slots=True)
class CapacityFilters:
    """Filtros de la pantalla de Capacidad instalada."""

    month: str
    workday_hours: float
    search: str = ""
    technology: str = ""
    concept: str = ""


@dataclass(frozen=True, slots=True)
class CapacityRow:
    """Una asignacion de un recurso a un proyecto o concepto."""

    resource: str
    band: str
    concept: str
    technology: str
    manager: str
    project_id: str
    project: str
    daily_hours: float
    estimated_hours: float
    has_rule: bool
    chargeable: bool
    billable: bool
    affects_capacity: bool


@dataclass(frozen=True, slots=True)
class CapacityView:
    """Pantalla de Capacidad instalada para un mes."""

    month: str
    month_label: str
    workdays: int
    workday_hours: float
    resources: int
    base_hours: float
    assigned_daily_hours: float
    over_workday: int
    rows: tuple[CapacityRow, ...]
    technologies: tuple[str, ...]
    concepts: tuple[str, ...]
    band_notice: str
    band_column: str


@dataclass(frozen=True, slots=True)
class ProjectRisk:
    """Un riesgo abierto del proyecto."""

    description: str
    impact: str
    probability: str


@dataclass(frozen=True, slots=True)
class TeamRole:
    """Personas y horas registradas de un rol del proyecto."""

    role: str
    people: int
    hours: int


@dataclass(frozen=True, slots=True)
class TimelineEvent:
    """Un hito del historial del proyecto."""

    date_text: str
    title: str
    text: str
    done: bool


@dataclass(frozen=True, slots=True)
class BarValue:
    """Una barra de la comparacion presupuesto contra avance."""

    label: str
    percent_text: str
    width: float
    color: str


@dataclass(frozen=True, slots=True)
class ProjectPage:
    """Pantalla completa de un proyecto."""

    project_id: str
    name: str
    client: str
    delivery_manager: str
    client_slug: str
    end_date: str
    status_label: str
    status_code: str
    decision: DecisionItem | None
    budget_used: int
    budget_hours: int
    burn_hours: int
    progress: int
    etc_hours: int
    bars: tuple[BarValue, ...]
    marker_left: float
    summary: str
    risks: tuple[ProjectRisk, ...]
    team: tuple[TeamRole, ...]
    events: tuple[TimelineEvent, ...]


@dataclass(frozen=True, slots=True)
class ProjectGroup:
    """Proyectos de un Delivery Manager para las listas agrupadas."""

    name: str
    slug: str
    summary: str
    rows: tuple[ProjectRow, ...]


@dataclass(frozen=True, slots=True)
class AccountRank:
    """Una cuenta en el ranking por salud de sus proyectos."""

    name: str
    slug: str
    in_progress: int
    health: HealthCount
    on_time_percent: int


@dataclass(frozen=True, slots=True)
class KpiManagerRow:
    """Un Delivery Manager en la tabla de KPIs."""

    name: str
    slug: str
    total: int
    health: HealthCount
    on_time_percent: int
    time_cost: TimeCost


@dataclass(frozen=True, slots=True)
class KpiView:
    """Pantalla KPIs de Delivery Managers (corte actual)."""

    rows: tuple[KpiManagerRow, ...]
    totals: KpiManagerRow
    best: KpiManagerRow | None
    worst: KpiManagerRow | None


@dataclass(frozen=True, slots=True)
class EvaCard:
    """Cifras reales de una tarjeta EVA en Operativa."""

    available: bool
    total_projects: int = 0
    time_cost: TimeCost = NO_TIME_COST


@dataclass(frozen=True, slots=True)
class MonthFacturability:
    """Facturabilidad de un mes: trabajo fijo, variable y libre."""

    month: str
    label: str
    short_label: str
    person_hours: float
    capacity: float
    fixed_hours: float
    fixed_percent: float | None
    fixed_hc: int
    variable_capacity: float
    variable_hours: float
    variable_percent: float | None
    variable_hc: int
    service_hours: tuple[float, ...]
    free_hours: float
    free_fte: int
    global_percent: float | None
    bar_height: float = 0.0
    error: str = ""


@dataclass(frozen=True, slots=True)
class SpecialtyRow:
    """Facturabilidad de una especialidad (ROL de Bandas/rol)."""

    name: str
    headcount: int
    capacity: float
    fixed_hours: float
    fixed_percent: float | None
    variable_hours: float
    variable_percent: float | None
    free_fte: int


@dataclass(frozen=True, slots=True)
class ResourceRow:
    """Facturabilidad mensual de una persona."""

    name: str
    role: str
    percents: tuple[float | None, ...]
    average: float | None


@dataclass(frozen=True, slots=True)
class InvestmentRow:
    """Horas de inversion comercial y operativa de un grupo."""

    name: str
    commercial: float
    operational: float

    @property
    def total(self) -> float:
        """Comercial mas operativa."""
        return self.commercial + self.operational


@dataclass(frozen=True, slots=True)
class HoursBar:
    """Una barra horizontal de horas."""

    label: str
    hours: float
    width: float


@dataclass(frozen=True, slots=True)
class InvestmentView:
    """Pantalla de inversion operativa y comercial de un mes."""

    month: str
    label: str
    totals: InvestmentRow
    by_area: tuple[InvestmentRow, ...]
    commercial_by_type: tuple[HoursBar, ...]
    operational_by_project: tuple[HoursBar, ...]
