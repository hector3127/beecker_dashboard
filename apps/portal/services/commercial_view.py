"""Indicadores comerciales en USD y filtros de la hoja A:U."""

from collections import Counter
from typing import Any

import requests
from django.core.paginator import Paginator
from django.utils import timezone

from apps.portal.services.commercial import commercial_rows
from apps.portal.services.commercial_rates import convert_usd, load_rates
from core.exceptions import DashboardError
from core.sheets.factory import build_sheet_repository


def build_commercial_context(params: Any) -> Any:
    """Arma filtros, totales y paginas comerciales."""
    today = timezone.localdate()
    context: dict[str, Any] = {
        "active": "comercial",
        "loaded_at": timezone.localtime(),
        "error": "",
        "from_executive": (
            params.get("origen") == "business-overview"
            or params.get("desde") == "ejecutiva"
        ),
    }
    try:
        data = commercial_rows(
            build_sheet_repository().read_values("Backlog_Proyectos")
        )
    except (DashboardError, ValueError) as error:
        context["error"] = str(error)
        return context
    all_rows = data["filas"]
    fx: dict[str, Any] = {"rates": {"USD": 1}, "date": ""}
    fx_error = ""
    if any(
        row["moneda"].strip().upper() not in {"", "USD"} for row in all_rows
    ):
        try:
            fx = load_rates(today)
        except (
            requests.RequestException,
            ValueError,
            KeyError,
            TypeError,
            OverflowError,
        ):
            fx_error = (
                "No se obtuvo una cotizacion valida del mes actual; "
                "los importes de otras monedas quedan pendientes."
            )
    for row in all_rows:
        row["usd"] = convert_usd(row["monto"], row["moneda"], fx["rates"])
    account = params.get("cliente", "")
    stage = params.get("etapa", "")
    start = params.get("desde", "")
    if start == "ejecutiva":
        start = ""
    end = params.get("hasta", "")
    query = params.get("q", "").strip()
    rows = [
        row
        for row in all_rows
        if (not account or row["cuenta"] == account)
        and (not stage or row["etapa"] == stage)
        and (not start or row["fechaCierre"] and row["fechaCierre"] >= start)
        and (not end or row["fechaCierre"] and row["fechaCierre"] <= end)
        and (
            not query
            or query.casefold()
            in " ".join(
                [row["cuenta"], row["oportunidad"], row["manager"]]
            ).casefold()
        )
    ]
    if start and end and start > end:
        context["error"] = "La fecha inicial debe ser menor o igual a la final."
        rows = []
    opened = [row for row in rows if row["estado"] == "abierta"]
    won = [row for row in rows if row["estado"] == "ganada"]

    def sum_usd(items: Any) -> Any:
        known = [row["usd"] for row in items if row["usd"] is not None]
        return sum(known) if known else None

    def groups(items: Any, field: Any) -> Any:
        result = []
        for name, count in Counter(
            row[field] or "Sin dato" for row in items
        ).most_common():
            selected = [
                row for row in items if (row[field] or "Sin dato") == name
            ]
            result.append(
                {
                    "name": name,
                    "count": count,
                    "pct": round(count / len(items) * 100, 1),
                    "usd": sum_usd(selected),
                }
            )
        return result

    services = groups(rows, "servicio")
    colors = [
        "#ef51be",
        "#7046f8",
        "#a553f3",
        "#f9ba28",
        "#8bb6ff",
        "#c2b8df",
        "#dccff3",
    ]
    offset = 0
    stops = []
    for index, item in enumerate(services):
        item["color"] = colors[index % len(colors)]
        stops.append(f"{item['color']} {offset}% {offset + item['pct']}%")
        offset += item["pct"]
    from apps.portal.services.commercial_pipeline import (
        build_annual_unconfirmed,
        build_pipeline,
    )

    years = sorted(
        {int(r["fechaCierre"][:4]) for r in opened if r["fechaCierre"]}
        | {today.year}
    )
    try:
        pipeline_year = int(params.get("pipeline_year", today.year))
    except (ValueError, TypeError):
        pipeline_year = today.year
    if pipeline_year not in years:
        pipeline_year = today.year
    context["pipeline"] = build_pipeline(opened, pipeline_year)
    context["pipeline"]["sections"][1] = build_annual_unconfirmed(
        opened, sorted(set(years) | {today.year + 1})
    )
    context["pipeline_years"] = years
    context["pipeline_details"] = {}
    for section in context["pipeline"]["sections"]:
        for index, group in enumerate(section["rows"]):
            group["detail_key"] = section["key"] + "_" + str(index)
            context["pipeline_details"][group["detail_key"]] = {
                "account": group["account"],
                "service": group["service"],
                "title": section["title"],
                "total": group["total"],
                "rows": group["details"],
            }
        section["group_count"] = len(section["rows"])
        parameter = "pipeline_" + section["key"]
        section["row_page"] = Paginator(section["rows"], 10).get_page(
            params.get(parameter)
        )
        links = params.copy()
        links.pop(parameter, None)
        section["page_query"] = links.urlencode()
        section["page_parameter"] = parameter

    page = Paginator(rows, 15).get_page(params.get("pagina"))
    context.update(
        {
            "clients": sorted({r["cuenta"] for r in all_rows if r["cuenta"]}),
            "stages": sorted({r["etapa"] for r in all_rows if r["etapa"]}),
            "selected_client": account,
            "selected_stage": stage,
            "start": start,
            "end": end,
            "query": query,
            "won_usd": sum_usd(won),
            "open_usd": sum_usd(opened),
            "won_count": len(won),
            "open_count": len(opened),
            "count": len(rows),
            "clients_count": len({r["cuenta"] for r in opened if r["cuenta"]}),
            "pending_usd": sum(r["usd"] is None for r in rows),
            "stage_groups": groups(rows, "etapa"),
            "account_groups": groups(
                [r for r in opened if r["cuenta"]], "cuenta"
            ),
            "service_groups": services,
            "donut": ",".join(stops),
            "page": page,
            "fx_date": fx["date"],
            "fx_error": fx_error,
            "currencies": [
                {"code": c, "rate": fx["rates"].get(c)}
                for c in sorted(
                    {r["moneda"].strip().upper() for r in rows if r["moneda"]}
                )
            ],
            "missing_id": not data["tieneId"],
        }
    )
    filters = params.copy()
    filters.pop("pagina", None)
    context["filter_query"] = filters.urlencode()
    return context
