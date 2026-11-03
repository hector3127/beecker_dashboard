"""Contexto de KPIs de DM sin petición HTTP, reloj ni base de datos."""

import ast
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from apps.portal.services.kpi_dm_store import StoredKpiCut
from apps.portal.services.kpi_eva import eva_manager_view
from apps.portal.services.kpi_history import build_kpi_history
from apps.portal.services.kpi_history_loader import KpiHistoryLoad
from apps.portal.services.kpi_screen import (
    KpiQuery,
    KpiQueryError,
    KpiSources,
    build_kpi_context,
)
from tests.portal.test_kpi_history import NOW
from tests.portal.test_kpi_history import sources as history_sources

TODAY = date(2026, 10, 28)

ROWS = [
    {
        "idProyecto": "A",
        "deliveryManager": "Ana",
        "desviacionDias": -1,
        "budget": 100,
        "avance": 150,
    },
    {
        "idProyecto": "B",
        "deliveryManager": "Beto",
        "desviacionDias": 0,
        "budget": 100,
        "avance": 100,
    },
]


class Lecturas:
    def __init__(self, latest=TODAY, observed=True):
        self.history_years = []
        self.cuts = []
        self.latest = latest
        self.observed = observed

    def history(self, year):
        self.history_years.append(year)
        return KpiHistoryLoad(build_kpi_history(history_sources(), NOW, year))

    def load_cut(self, cut):
        self.cuts.append(cut)
        observation = (
            SimpleNamespace(period=SimpleNamespace(status="open"))
            if self.observed
            else None
        )
        return StoredKpiCut(eva_manager_view(ROWS), observation)

    def sources(self):
        return KpiSources(
            load_history=self.history,
            latest_cut=lambda: self.latest,
            load_cut=self.load_cut,
            monthly_cut=lambda month: month.replace(day=15),
        )


def build(query=None, lecturas=None, today=TODAY):
    lecturas = lecturas or Lecturas()
    return build_kpi_context(
        query or KpiQuery(), today, lecturas.sources()
    ), lecturas


def test_opens_on_the_latest_saved_cut_and_the_current_year():
    context, lecturas = build()

    assert context["kpi_filters"]["cut"] == "2026-10-28"
    assert context["kpi_filters"]["history_year"] == 2026
    assert context["kpi_filters"]["chart_year"] == 2026
    assert context["cut_label"] == "28/10/2026"
    assert context["cut_is_current"] is True
    assert context["kpi_storage"] == {
        "latest_cut": "2026-10-28",
        "selected_status": "open",
    }
    assert lecturas.history_years == [2026]


def test_without_a_saved_cut_it_falls_back_to_today():
    context, lecturas = build(lecturas=Lecturas(latest=None))

    assert context["kpi_filters"]["cut"] == "2026-10-28"
    assert context["kpi_storage"]["latest_cut"] is None


def test_a_month_uses_the_monthly_cut():
    context, lecturas = build(KpiQuery(month="2026-09"))

    assert context["kpi_filters"]["month"] == "2026-09"
    assert context["kpi_filters"]["cut"] == "2026-09-15"
    assert lecturas.cuts == [date(2026, 9, 15)]


def test_the_chart_year_is_read_only_when_it_differs():
    same, lecturas_same = build(KpiQuery(history_year="2026"))
    other, lecturas_other = build(
        KpiQuery(history_year="2026", chart_year="2025")
    )

    assert lecturas_same.history_years == [2026]
    assert lecturas_other.history_years == [2026, 2025]
    assert other["kpi_filters"]["chart_year"] == 2025


def test_the_year_alias_is_used_when_there_is_no_history_year():
    context, _ = build(KpiQuery(year="2025"))

    assert context["kpi_filters"]["history_year"] == 2025
    assert context["kpi_filters"]["chart_year"] == 2025


def test_selected_managers_filter_every_panel_and_keep_the_roster():
    context, _ = build(KpiQuery(managers=("Ana",)))

    assert [row.name for row in context["kpis"].rows] == ["Ana"]
    assert context["kpi_filters"]["selected_managers"] == ["Ana"]
    assert "Beto" in context["kpi_filters"]["managers"]
    assert [row["name"] for row in context["chart"]["series"]] == ["Ana"]
    assert [row.name for row in context["month_matrix"].rows] == ["Ana"]


def test_an_empty_selection_keeps_every_manager():
    everyone, _ = build()
    none, _ = build(KpiQuery(managers=()))

    assert [row.name for row in everyone["kpis"].rows] == [
        row.name for row in none["kpis"].rows
    ]


def test_a_missing_observation_is_said_in_the_notice():
    context, _ = build(lecturas=Lecturas(observed=False))

    assert context["cut_available"] is False
    assert context["kpi_storage"]["selected_status"] == "missing"
    assert (
        "No hay una captura KPI guardada para 28/10/2026"
        in (context["history_notice"])
    )


def test_a_failed_history_leaves_the_matrices_out():
    lecturas = Lecturas()
    lecturas.history = lambda year: KpiHistoryLoad(None, error="Sin red.")

    context, _ = build(lecturas=lecturas)

    assert context["history_error"] == "Sin red."
    assert "month_matrix" not in context
    assert "quarter_matrix" not in context
    assert "chart" not in context


def test_the_picker_keeps_the_extra_params():
    context, _ = build(KpiQuery(params={"dm": ["Ana"]}))

    assert all("dm=Ana" in link.href for link in context["picker"].years)


@pytest.mark.parametrize(
    "query",
    [
        KpiQuery(month="2026-11"),
        KpiQuery(month="2020-12"),
        KpiQuery(month="no-es-mes"),
        KpiQuery(cut="2026-11-01"),
        KpiQuery(cut="no-es-fecha"),
        KpiQuery(history_year="2027"),
        KpiQuery(history_year="2020"),
        KpiQuery(history_year="abc"),
        KpiQuery(chart_year="2027"),
    ],
)
def test_an_invalid_query_raises_one_clear_error(query):
    with pytest.raises(KpiQueryError) as error:
        build(query)

    assert "fecha de corte no futura y un año válido" in str(error.value)


def test_the_module_does_not_depend_on_the_request_the_clock_or_drf():
    source = Path("apps/portal/services/kpi_screen.py").read_text(
        encoding="utf-8"
    )
    imported = {
        node.module
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.module
    }

    assert (
        not {
            "django.http",
            "django.utils",
            "django.conf",
            "rest_framework.exceptions",
        }
        & imported
    )
