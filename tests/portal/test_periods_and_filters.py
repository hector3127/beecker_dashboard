"""Periodo del trimestre y filtros de Operativa."""

from datetime import date

import pytest

from apps.portal.services.filters import (
    filter_projects,
    list_clients,
    list_services,
)
from apps.portal.services.periods import current_quarter, format_date
from tests.portal.builders import make_project


@pytest.mark.parametrize(
    ("today", "start", "end"),
    [
        (date(2026, 10, 12), "01-oct-2026", "31-dic-2026"),
        (date(2026, 8, 3), "01-jul-2026", "30-sep-2026"),
        (date(2026, 2, 28), "01-ene-2026", "31-mar-2026"),
        (date(2026, 5, 1), "01-abr-2026", "30-jun-2026"),
    ],
)
def test_current_quarter(today, start, end):
    period = current_quarter(today)

    assert (period.start, period.end) == (start, end)


def test_format_date():
    assert format_date(date(2026, 7, 1)) == "01-jul-2026"


def sample_projects():
    return [
        make_project(project_id="1", client="ACME", service="AER"),
        make_project(project_id="2", client="Globex", service="T&M"),
        make_project(project_id="3", client="ACME", service=""),
    ]


def test_filter_without_values_returns_everything():
    assert len(filter_projects(sample_projects(), "", "")) == 3


def test_filter_by_service_and_client():
    projects = sample_projects()

    assert [p.project_id for p in filter_projects(projects, "AER", "")] == ["1"]
    assert [p.project_id for p in filter_projects(projects, "", "ACME")] == [
        "1",
        "3",
    ]
    assert filter_projects(projects, "T&M", "ACME") == []


def test_lists_are_sorted_distinct_and_non_empty():
    projects = sample_projects()

    assert list_services(projects) == ["AER", "T&M"]
    assert list_clients(projects) == ["ACME", "Globex"]
