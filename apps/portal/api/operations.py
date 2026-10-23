"""API de Operativa: EVA, inversion, facturabilidad y capacidad."""

from typing import Any

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.checks import capability_permission
from apps.portal import views
from apps.portal.api.plain import plain

"""BKD.120.026 - API de Operativa
Son cifras del equipo o del portafolio completo: piden view_operations y
alcance total (con alcance limitado responden 403 antes de consultar fuentes).
Cada respuesta es {data, meta}; data conserva los nombres de los campos que ya
usa la pantalla y los datos que faltan llegan vacios, no como cero.
"""


class OperationsScreen(APIView):
    """Base: permiso comun y la forma {data, meta} de la respuesta."""

    permission_classes = [
        *APIView.permission_classes,
        capability_permission("view_operations", whole_portfolio=True),
    ]

    @staticmethod
    def body(data: dict[str, Any], **meta: Any) -> Response:
        """Respuesta {data, meta} con los datos ya convertidos a JSON."""
        return Response({"data": plain(data), "meta": plain(meta)})


class EvaScreenView(OperationsScreen):
    """EVA 1 y EVA 2: proyectos IXB y RaaS con su avance."""

    def get(self, request: Request) -> Response:
        """Proyectos IXB/RaaS con el error de la fuente, si lo hubo."""
        return self.body(views.eva2_data())


class Eva3ScreenView(OperationsScreen):
    """EVA 3: proyectos AER y T&M por Delivery Manager."""

    def get(self, request: Request) -> Response:
        """Proyectos AER/T&M y el promedio de dias para renovar."""
        return self.body(views.eva3_data())


class InvestmentScreenView(OperationsScreen):
    """Horas de inversion comercial y operativa de un mes."""

    def get(self, request: Request) -> Response:
        """Mes pedido (?mes=AAAA-MM o ?periodo=...); sin el, el actual."""
        month = views._facturability_month(request._request)
        return self.body(views.inversion_data(month))


class CapacityScreenView(OperationsScreen):
    """Asignaciones y capacidad base de un mes."""

    def get(self, request: Request) -> Response:
        """Mes, jornada y filtros opcionales como en la pantalla."""
        return self.body(views.capacidad_data(request._request))


class FacturabilityScreenView(OperationsScreen):
    """Facturabilidad del periodo: general, por especialidad o por recurso."""

    kind = "general"

    def get(self, request: Request) -> Response:
        """Periodo con ?periodo=anio|trimestre|mes y el filtro de roles."""
        django_request = request._request
        period = views._period(django_request)
        builders = {
            "general": views.facturabilidad_data,
            "especialidad": views.especialidad_data,
            "recurso": views.recurso_data,
        }
        data = builders[self.kind](django_request, period)
        return self.body(
            data,
            period={
                "kind": period.kind,
                "label": period.label,
                "year": period.year,
                "months": period.months,
                "end_month": period.end_month,
            },
        )


class FacturabilitySpecialtyView(FacturabilityScreenView):
    """Facturabilidad del periodo por especialidad."""

    kind = "especialidad"


class FacturabilityResourceView(FacturabilityScreenView):
    """Facturabilidad de cada persona."""

    kind = "recurso"
