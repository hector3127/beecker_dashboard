"""Account monthly hours and CSV export share the same authorization."""

import csv
from datetime import date
from io import StringIO
from typing import Any

from django.http import HttpResponse
from django.utils import timezone
from django.utils.text import slugify
from rest_framework.exceptions import ParseError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.checks import capability_permission
from apps.portal.api.account import _client
from apps.portal.services.account_hours import (
    load_account_hours,
    select_account_projects,
)


def csv_report(data: dict[str, Any]) -> str:
    """Spreadsheet-friendly CSV with safe text cells."""
    output = StringIO(newline="")
    writer = csv.writer(output)

    def safe(text: str) -> str:
        return (
            "'" + text
            if text.lstrip().startswith(("=", "+", "-", "@"))
            else text
        )

    writer.writerow(
        [
            "Cuenta",
            safe(data["client"]),
            "Año",
            data["year"],
            "Corte",
            data["cutoff"],
            "Desde",
            data.get("start", ""),
        ]
    )
    writer.writerow(
        [
            "Proyecto",
            "Nombre",
            *[m["key"] for m in data["months"]],
            "Total conocido (h)",
            "Estado",
            "Observación",
        ]
    )
    for row in data["projects"]:
        writer.writerow(
            [
                safe(row["id"]),
                safe(row["name"]),
                *[
                    c["hours"] if c["hours"] is not None else "Pendiente"
                    for c in row["cells"]
                ],
                row["known_hours"],
                "Parcial" if row["partial"] else "Completo",
                safe(row["issue"]),
            ]
        )
    writer.writerow(
        [
            "Total conocido",
            "",
            *[
                t["hours"] if t["hours"] is not None else "Pendiente"
                for t in data["totals"]
            ],
            data["known_hours"],
            "Parcial" if data["partial"] else "Completo",
        ]
    )
    writer.writerow(
        [
            "Nota",
            "Horas por fecha de trabajo. El mes actual es parcial. "
            "Pendiente no significa cero; los totales parciales "
            "suman solo datos conocidos.",
        ]
    )
    return "\ufeff" + output.getvalue()


class AccountHoursView(APIView):
    """Monthly account hours; ?descargar=csv exports exactly the same report."""

    permission_classes = [
        *APIView.permission_classes,
        capability_permission("view_operations"),
    ]

    def get(self, request: Request) -> Response | HttpResponse:
        """Authorize before reading sources, including exports."""
        client = _client(request)
        try:
            start_text = request.query_params.get("desde", "")
            end_text = request.query_params.get("hasta", "")
            if bool(start_text) != bool(end_text):
                raise ValueError("Indica ambas fechas.")
            start = date.fromisoformat(start_text) if start_text else None
            end = date.fromisoformat(end_text) if end_text else None
            if start and end and (end < start or (end - start).days > 1096):
                raise ValueError("Rango inválido.")
            year = int(
                start.year
                if start
                else request.query_params.get("anio", timezone.localdate().year)
            )
            if not 2000 <= year <= timezone.localdate().year:
                raise ValueError(
                    "Selecciona un año entre 2000 y el año actual."
                )
            data = load_account_hours(client, year, start=start, end=end)
            data = select_account_projects(
                data, request.query_params.getlist("proyecto")
            )
        except (ValueError, TypeError) as error:
            raise ParseError(
                "Revisa los proyectos y el periodo: fechas válidas, "
                "inicio anterior al fin, hasta tres años y sin inicio futuro."
            ) from error
        if request.query_params.get("descargar") == "csv":
            response = HttpResponse(
                csv_report(data), content_type="text/csv; charset=utf-8"
            )
            response["Content-Disposition"] = (
                f'attachment; filename="horas-{slugify(client)}-'
                f'{data["start"]}-{data["end"]}.csv"'
            )
            return response
        return Response(
            {"data": data, "meta": {"source": "Clockify sincronizado"}}
        )
