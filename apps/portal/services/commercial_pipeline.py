"""Horas abiertas por mes de cierre; probabilidad pendiente de conectar."""

from datetime import date
from typing import Any

from apps.portal.services.commercial import normalize

MONTHS = (
    "Ene",
    "Feb",
    "Mar",
    "Abr",
    "May",
    "Jun",
    "Jul",
    "Ago",
    "Sep",
    "Oct",
    "Nov",
    "Dic",
)


def build_pipeline(rows: Any, year: Any) -> Any:
    """Agrupa oportunidades abiertas por mes y probabilidad."""
    sections: list[dict[str, Any]] = [
        {
            "key": "confirmed",
            "title": "Oportunidades de alta probabilidad",
            "subtitle": "Probabilidad de 70% o más · sin firma",
            "rows": [],
        },
        {
            "key": "unconfirmed",
            "title": "Oportunidades en desarrollo",
            "subtitle": "Probabilidad menor de 70%",
            "rows": [],
        },
        {
            "key": "pending",
            "title": "Probabilidad pendiente",
            "subtitle": "Sin clasificación hasta conectar la nueva hoja",
            "rows": [],
        },
    ]
    buckets = {s["key"]: s for s in sections}
    grouped: dict[str, dict[tuple[str, str], dict[str, Any]]] = {
        key: {} for key in buckets
    }
    missing_date = missing_hours = 0
    for row in rows:
        if row.get("estado") != "abierta":
            continue
        try:
            closing = date.fromisoformat(row.get("fechaCierre") or "")
        except (ValueError, TypeError):
            missing_date += 1
            continue
        if closing.year != year:
            continue
        hours = row.get("horas")
        if hours is None:
            missing_hours += 1
        probability = row.get("probabilidad")
        key = (
            "pending"
            if probability is None
            else "confirmed"
            if probability >= 70
            else "unconfirmed"
        )
        account = str(row.get("cuenta") or "Sin cuenta").strip()
        service = str(row.get("servicio") or "Sin servicio").strip()
        group_key = (normalize(account), normalize(service))
        group = grouped[key].setdefault(
            group_key,
            {
                "account": account,
                "service": service,
                "cells": [0.0] * 12,
                "total": 0.0,
                "probabilities": set(),
                "records": 0,
                "missing_hours": 0,
                "details": [],
            },
        )
        group["details"].append(dict(row))
        group["records"] += 1
        if hours is not None:
            group["cells"][closing.month - 1] += hours
            group["total"] += hours
        else:
            group["missing_hours"] += 1
        if probability is not None:
            group["probabilities"].add(probability)
    for section in sections:
        section["rows"] = sorted(
            (r for r in grouped[section["key"]].values() if r["total"] > 0),
            key=lambda r: (normalize(r["account"]), normalize(r["service"])),
        )
        section["records"] = sum(r["records"] for r in section["rows"])
        for group in section["rows"]:
            probabilities = sorted(group.pop("probabilities"))
            group["probability_color"] = (
                "purple"
                if probabilities and probabilities[0] >= 90
                else "green"
                if probabilities and probabilities[0] >= 80
                else "amber"
            )
            group["probability_label"] = (
                "Pendiente"
                if not probabilities
                else f"{probabilities[0]:g}%"
                if len(probabilities) == 1
                else f"{probabilities[0]:g}% - {probabilities[-1]:g}%"
            )
        section["totals"] = [
            sum(r["cells"][m] or 0 for r in section["rows"]) for m in range(12)
        ]
        section["total"] = sum(section["totals"])
    return {
        "year": year,
        "months": MONTHS,
        "sections": sections,
        "missing_date": missing_date,
        "missing_hours": missing_hours,
        "dummy": any(r.get("probabilidadFicticia") for r in rows),
    }


def build_annual_unconfirmed(rows: Any, years: Any) -> Any:
    """Consolida horas no confirmadas por cuenta, servicio y ano."""
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    for index, year in enumerate(years):
        for row in build_pipeline(rows, year)["sections"][1]["rows"]:
            key = (normalize(row["account"]), normalize(row["service"]))
            group = groups.setdefault(
                key,
                {
                    "account": row["account"],
                    "service": row["service"],
                    "cells": [0.0] * len(years),
                    "total": 0.0,
                    "records": 0,
                    "details": [],
                    "probability_color": "amber",
                },
            )
            group["cells"][index] += row["total"]
            group["total"] += row["total"]
            group["records"] += row["records"]
            group["details"].extend(row["details"])
    for group in groups.values():
        probabilities = sorted(
            {
                row["probabilidad"]
                for row in group["details"]
                if row.get("probabilidad") is not None
            }
        )
        group["probability_label"] = (
            f"{probabilities[0]:g}%"
            if len(probabilities) == 1
            else f"{probabilities[0]:g}% - {probabilities[-1]:g}%"
        )
    result = sorted(
        groups.values(),
        key=lambda r: (normalize(r["account"]), normalize(r["service"])),
    )
    return {
        "key": "unconfirmed",
        "title": "Oportunidades en desarrollo",
        "subtitle": "Probabilidad menor de 70%",
        "rows": result,
        "years": years,
        "annual": True,
        "totals": [
            sum(r["cells"][i] for r in result) for i in range(len(years))
        ],
        "total": sum(r["total"] for r in result),
        "records": sum(r["records"] for r in result),
    }


def group_services(rows: Any) -> Any:
    """All accounts stay inside their service; totals keep original units."""
    grouped: dict[Any, Any] = {}
    for row in rows:
        name = row["service"] or "Sin servicio"
        group = grouped.setdefault(
            name,
            {
                "service": name,
                "rows": [],
                "total": 0,
                "cells": [0.0] * len(row["cells"]),
            },
        )
        group["rows"].append(row)
        group["total"] += row["total"]
        for index, value in enumerate(row["cells"]):
            group["cells"][index] += value or 0
    for group in grouped.values():
        probabilities = sorted(
            {
                detail["probabilidad"]
                for row in group["rows"]
                for detail in row.get("details", [])
                if detail.get("probabilidad") is not None
            }
        )
        group["probability_label"] = (
            "Pendiente"
            if not probabilities
            else f"{probabilities[0]:g}%"
            if len(probabilities) == 1
            else f"{probabilities[0]:g}% - {probabilities[-1]:g}%"
        )
    return [grouped[name] for name in sorted(grouped)]
