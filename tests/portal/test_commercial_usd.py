"""Regresiones de conversion USD y lectura del backlog A:U."""

from datetime import UTC, date, datetime
from unittest.mock import patch

from django.http import QueryDict

from apps.portal.services.commercial import commercial_rows
from apps.portal.services.commercial_rates import convert_usd, validate_rates
from apps.portal.services.commercial_view import build_commercial_context


def test_conversion_and_unavailable_currency():
    rates = {"USD": 1, "MXN": 20, "COP": 4000}
    assert convert_usd(20000, "USD", rates) == 20000
    assert convert_usd(40000, "MXN", rates) == 2000
    assert convert_usd(8000000, "COP", rates) == 2000
    assert convert_usd(40000, "", rates) is None
    assert convert_usd(None, "USD", rates) is None
    assert convert_usd(0, "USD", rates) == 0


def test_rejects_rates_from_other_month():
    payload = {
        "result": "success",
        "base_code": "USD",
        "rates": {"MXN": 20},
        "time_last_update_unix": datetime(2026, 9, 30, tzinfo=UTC).timestamp(),
    }
    try:
        validate_rates(payload, date(2026, 10, 12))
    except ValueError:
        pass
    else:
        raise AssertionError("Stale rates must not be used")
    payload["time_last_update_unix"] = datetime(
        2026, 10, 12, tzinfo=UTC
    ).timestamp()
    assert validate_rates(payload, date(2026, 10, 12))["rates"]["MXN"] == 20


def test_columns_a_to_u_and_missing_values():
    headers = [
        "Account Name",
        "Opportunity Name",
        "Delivery Manager",
        "Opportunity Stage",
        "Fecha de cierre - Diario",
        "Service Type",
        "Invoice Name",
        "Total Hours",
        "Duration_Service",
        "Valor",
        "Currency Opportunity",
        "Account",
        "Fecha inicio",
        "Stage",
        "CIO",
        "Calculadora",
        "Arq",
        "En tiempo",
        "Observaciones",
        "Estimaci\u00f3n",
        "Fecha \u00faltimo seguimiento",
    ]
    row = [
        "X",
        "O",
        "PM",
        "Discovery (Pipeline)",
        46307,
        "SaaS",
        "I",
        "(No value)",
        "12",
        20000,
        "USD",
        "A",
        46307,
        "Prospectos",
        "Si",
        "Si",
        "No",
        "Seguimiento",
        "Nota",
        "100",
        46307,
    ]
    item = commercial_rows([headers, row])["filas"][0]
    assert (
        item["fechaCierre"] == "2026-10-12"
        and item["fechaInicio"] == "2026-10-12"
    )
    assert item["seguimiento"] == "2026-10-12" and item["estimacion"] == "100"
    assert item["horas"] is None and item["monto"] == 20000


def test_totals_are_usd_and_missing_rates_excluded():
    headers = [
        "Account Name",
        "Opportunity Name",
        "Opportunity Stage",
        "Valor",
        "Currency Opportunity",
    ]
    data = [
        headers,
        ["X", "USD deal", "Discovery", 100, "USD"],
        ["X", "MXN deal", "Discovery", 2000, "MXN"],
        ["X", "Unknown deal", "Discovery", 500, ""],
    ]
    with (
        patch(
            "apps.portal.services.commercial_view.build_sheet_repository"
        ) as factory,
        patch(
            "apps.portal.services.commercial_view.load_rates",
            return_value={"rates": {"USD": 1, "MXN": 20}, "date": "2026-10-12"},
        ),
    ):
        factory.return_value.read_values.return_value = data
        context = build_commercial_context(QueryDict())
    assert context["open_usd"] == 200 and context["pending_usd"] == 1
