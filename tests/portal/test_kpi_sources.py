"""KPIs consultan contratos MPB y bloques independientes del historico."""

from datetime import date, datetime
from unittest.mock import Mock

from django.core.cache import cache
from django.test import override_settings

from apps.portal.services import kpi_history_loader
from apps.portal.services.kpi_history import HistorySources, build_kpi_history
from apps.portal.services.kpi_sources import KpiSheetReader, load_kpi_sources
from core.time_entries.models import TimeEntry, TimeEntryBatch
from tests.fakes import InMemorySheetRepository

MPB = [
    "CLIENTE",
    "ID",
    "NOMBRE",
    "SERVICE",
    "INICIO",
    "FIN",
    "ESTATUS",
    "Delivery Manager",
    "HORAS",
]
LEFT = [
    "Delivery Manager",
    "Account",
    "Project ID",
    "Service",
    "Project Name",
    "",
    "Status",
    "Start",
    "Finish",
    "",
]
RIGHT = [
    "Delivery Manager",
    "Client",
    "Project ID",
    "Service",
    "Project Name",
    "Stage",
    "Actual Start",
    "Actual Finish",
    "Budget",
]
TODAY = date(2026, 10, 14)


class SourceOnlyReader(InMemorySheetRepository):
    def read_values(self, name):
        assert name != "Proyectos", "A KPI must never read Proyectos"
        return super().read_values(name)

    def read_as_objects(self, name):
        assert name != "Proyectos", "A KPI must never read Proyectos"
        return super().read_as_objects(name)


def reader():
    return SourceOnlyReader(
        {
            "MPB": [
                MPB,
                [
                    "ACME",
                    "AER.001",
                    "MPB name",
                    "AER",
                    "2026-01-01",
                    "2026-12-31",
                    "En progreso",
                    "MPB DM",
                    100,
                ],
            ],
            "Historico_Proyectos": [
                LEFT + RIGHT,
                [
                    "Stage DM",
                    "ACME",
                    "IXB.001_CR",
                    "IXB",
                    "History name",
                    "",
                    "Discovery",
                    "2026-01-01",
                    "2026-01-10",
                    "",
                    "Wrong DM",
                    "Other",
                    "OTHER.001",
                    "IXB",
                    "Other project",
                    "Development",
                    "2027-01-01",
                    "",
                    9999,
                ],
                [
                    "Stage DM",
                    "ACME",
                    "IXB.001_CR",
                    "IXB",
                    "History name",
                    "",
                    "Development",
                    "2026-01-11",
                    "2026-03-01",
                    "",
                    "History DM",
                    "ACME",
                    "IXB.001_CR",
                    "IXB",
                    "History name",
                    "Development",
                    "2026-01-01",
                    "",
                    200,
                ],
                [
                    "Stage DM",
                    "ACME",
                    "IXB.001_CR",
                    "IXB",
                    "History name",
                    "",
                    "Completed",
                    "2026-03-15",
                    "2026-03-15",
                    "",
                ],
                [
                    "Wrong",
                    "ACME",
                    "AER.001",
                    "AER",
                    "Wrong MPB",
                    "",
                    "Development",
                    "2026-01-01",
                    "",
                    "",
                ],
            ],
            "Riesgos": [["ID_Proyecto", "Impacto", "Estado"]],
        }
    )


def test_history_uses_only_a_to_i_and_ignores_right_block():
    sources = load_kpi_sources(reader(), TODAY)
    january = {p.project_id: p for p in sources.at(date(2026, 1, 31))}
    assert set(january) == {"AER.001", "IXB.001_CR"}
    assert january["AER.001"].budget_hours == 100
    assert january["AER.001"].display_name == "MPB name"
    assert sources.managers["AER.001"] == "MPB DM"
    assert january["IXB.001_CR"].budget_hours == 0
    assert january["IXB.001_CR"].display_name == "History name"
    assert sources.managers["IXB.001_CR"] == "Stage DM"
    assert "OTHER.001" not in sources.events
    assert all("Budget" not in row for row in sources.metadata.values())
    assert {p.project_id for p in sources.at(date(2026, 3, 31))} == {"AER.001"}
    scoped = KpiSheetReader(reader(), list(january.values()))
    assert len(scoped.read_values("Proyectos")) == 3


def test_missing_history_budget_is_not_reported_as_zero_progress():
    r = reader()
    r.sheets["Historico_Proyectos"][2][-1] = ""
    sources = load_kpi_sources(r, TODAY)
    history = build_kpi_history(
        HistorySources([], [], [], sources.managers, sources.at),
        datetime(2026, 10, 14),
        2026,
    )
    row = next(r for r in history.months[0].view.rows if r.name == "Stage DM")
    assert row.total == 1
    assert row.time_cost.cost_percent is None


def test_budget_from_j_is_shared_by_project_id_without_using_right_block():
    r = reader()
    rows = r.sheets["Historico_Proyectos"]
    rows[0][9] = "Budget  (Hrs)"
    # El presupuesto puede estar en la primera etapa y no repetirse debajo.
    rows[1][9] = 400
    rows[2][9] = ""
    sources = load_kpi_sources(r, TODAY)
    january = {p.project_id: p for p in sources.at(date(2026, 1, 31))}
    assert january["IXB.001_CR"].budget_hours == 400
    assert sources.managers["IXB.001_CR"] == "Stage DM"
    assert "OTHER.001" not in sources.events
    hours = TimeEntry(
        entry_id="one",
        project_id="IXB.001_CR",
        resource_name="Ana",
        entry_date=datetime(2026, 1, 20),
        duration_hours=100,
        costing_rate=0,
        is_billable=True,
    )
    history = build_kpi_history(
        HistorySources([], [hours], [], sources.managers, sources.at),
        datetime(2026, 10, 14),
        2026,
    )
    row = next(r for r in history.months[0].view.rows if r.name == "Stage DM")
    assert row.time_cost.cost_percent == 25


@override_settings(TIME_ENTRY_SOURCE="sheet")
def test_loader_reads_only_source_catalog_and_caches_it(monkeypatch):
    cache.clear()
    r = InMemorySheetRepository(
        {
            **reader().sheets,
            "Proyectos": [
                ["ID_Proyecto", "Servicio", "Budget_Hrs"],
                ["IXB.001_CR", "IXB", 200],
            ],
        }
    )
    monkeypatch.setattr(kpi_history_loader, "build_sheet_repository", lambda: r)
    provider = Mock()
    provider.load_time_entries.return_value = TimeEntryBatch(entries=())
    factory = Mock(return_value=provider)
    monkeypatch.setattr(
        kpi_history_loader, "build_time_entry_provider", factory
    )
    result = kpi_history_loader.load_kpi_history(2026)
    assert not result.error
    assert result.history is not None
    catalog = factory.call_args.args[0].read_as_objects("Proyectos")
    assert {r["ID_Proyecto"] for r in catalog} == {"IXB.001_CR"}
    kpi_history_loader.load_kpi_history(2026)
    provider.load_time_entries.assert_called_once()
    cache.clear()


@override_settings(TIME_ENTRY_SOURCE="clockify")
def test_clockify_uses_source_ids_and_preserves_exact_cr(monkeypatch):
    cache.clear()
    r = InMemorySheetRepository(
        {
            **reader().sheets,
            "Proyectos": [
                ["ID_Proyecto", "Servicio", "Budget_Hrs"],
                ["IXB.001_CR", "IXB", 200],
            ],
        }
    )
    monkeypatch.setattr(kpi_history_loader, "build_sheet_repository", lambda: r)
    calls = []

    def factory(scoped):
        assert {
            row["ID_Proyecto"] for row in scoped.read_as_objects("Proyectos")
        } == {"IXB.001_CR"}
        loader = Mock()

        def hours(pid, period):
            calls.append((pid, period))
            return []

        loader.load_project.side_effect = hours
        return loader

    monkeypatch.setattr(kpi_history_loader, "build_clockify_loader", factory)
    result = kpi_history_loader.load_kpi_history(2026)
    assert not result.error
    assert {pid for pid, _ in calls} == {"IXB.001_CR"}
    assert all(period[0] == date(2026, 1, 1) for _, period in calls)
    kpi_history_loader.load_kpi_history(2026)
    assert len(calls) == 1
    cache.clear()


@override_settings(TIME_ENTRY_SOURCE="clockify")
def test_overdue_finish_does_not_truncate_clockify_hours(monkeypatch):
    cache.clear()
    r = InMemorySheetRepository(
        {
            **reader().sheets,
            "Proyectos": [
                ["ID_Proyecto", "Servicio", "Budget_Hrs"],
                ["IXB.001_CR", "IXB", 200],
            ],
        }
    )
    # La etapa anterior trae una fecha fin anterior a Discovery.
    r.sheets["Historico_Proyectos"][2][6] = "Deployment"
    r.sheets["Historico_Proyectos"][2][8] = "2025-12-01"
    r.sheets["Historico_Proyectos"].pop(3)  # Sin cierre que corrija el fin.
    monkeypatch.setattr(kpi_history_loader, "build_sheet_repository", lambda: r)
    loader = Mock()
    loader.load_project.return_value = []
    monkeypatch.setattr(
        kpi_history_loader, "build_clockify_loader", lambda _: loader
    )
    result = kpi_history_loader.load_kpi_history(2026)
    assert result.history is not None
    assert result.error == ""
    assert result.notice == ""
    row = next(
        r for r in result.history.months[0].view.rows if r.name == "Stage DM"
    )
    assert row.time_cost.cost_percent == 0
    assert row.time_cost.time_days == 0
    assert loader.load_project.call_count == 1
    assert kpi_history_loader.load_kpi_history(2026).notice == result.notice
    cache.clear()


def test_operational_block_ignores_old_estimates_and_ends_at_cancelled():
    r = reader()
    stages = [
        ("Discovery EST", "2025-02-25", "2025-03-10"),
        ("Deployment EST", "2025-04-16", "2025-05-18"),
        ("Discovery OP", "2026-02-25", "2026-04-02"),
        ("Suspendido", "2026-04-02", "2026-10-14"),
        ("Discovery OP", "2026-04-16", "2026-04-23"),
        ("Development", "2026-04-24", "2026-05-29"),
        ("Cancelled", "2026-06-01", "2026-06-22"),
        ("Deployment EST", "2027-01-01", "2027-12-31"),
    ]
    r.sheets["Historico_Proyectos"] = [LEFT + RIGHT] + [
        ["DM", "ACME", "MME.002", "IXB", "Proyecto", "", status, start, end, ""]
        for status, start, end in stages
    ]
    sources = load_kpi_sources(r, TODAY)
    assert {p.project_id for p in sources.at(date(2025, 4, 30))} == set()
    february = {p.project_id: p for p in sources.at(date(2026, 2, 28))}
    project = february["MME.002"]
    assert project.start_date == datetime(2026, 2, 25)
    assert project.end_date == datetime(2026, 6, 22)
    assert "MME.002" not in {
        p.project_id for p in sources.at(date(2026, 4, 10))
    }
    assert "MME.002" in {p.project_id for p in sources.at(date(2026, 5, 31))}
    assert "MME.002" not in {
        p.project_id for p in sources.at(date(2026, 6, 30))
    }
