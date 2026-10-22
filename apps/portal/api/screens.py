"""Resumen de datos de cada pantalla: una peticion por pantalla."""

from django.utils import timezone
from rest_framework.exceptions import ParseError, PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.checks import capability_permission, scope_for
from apps.portal import views
from apps.portal.api.serializers import (
    billing_screen,
    eva4_screen,
    operativa_screen,
)
from apps.portal.services import eva4

"""BKD.120.016 - Pantallas de la API v1
Cada vista valida el permiso, aplica el alcance de la persona y entrega el
contrato de su pantalla. La logica de negocio vive en portal/services.
"""


class Eva4ScreenView(APIView):
    """EVA-04: procesos activos, renovaciones y clientes de un mes."""

    permission_classes = [
        *APIView.permission_classes,
        capability_permission("view_operations"),
    ]

    def get(self, request: Request) -> Response:
        """Resumen del mes pedido (?mes=AAAA-MM); sin mes, el actual."""
        month = request.query_params.get("mes")
        report = eva4.load_eva4(month) if month else eva4.load_eva4()
        report = eva4.restrict(report, scope_for(request), timezone.localdate())
        body = eva4_screen(report)
        body["meta"]["generated_at"] = timezone.now().isoformat()
        return Response(body)


# Bloques de Operativa que se refrescan por separado; "" es la base
# (proyectos y estados). La logica sigue en views mientras se migra.
OPERATIVA_BLOCKS = {"", "eva3", "inversion", "capacidad", "eva4"}


class OperativaView(APIView):
    """Operativa: el ultimo corte guardado, sin consultar las fuentes."""

    permission_classes = [
        *APIView.permission_classes,
        capability_permission("view_operations"),
    ]

    def get(self, request: Request) -> Response:
        """Corte guardado para los filtros ?servicio= y ?cuenta=."""
        context = views.operativa_context(request)
        return Response(
            operativa_screen(
                context,
                unrestricted=scope_for(request).unrestricted,
                snapshot=True,
            )
        )


class OperativaBlockView(APIView):
    """Operativa: refresca la base o un bloque (?bloque=)."""

    permission_classes = OperativaView.permission_classes

    def get(self, request: Request) -> Response:
        """Calcula el bloque y devuelve el contexto actualizado."""
        if request.query_params.get("bloque", "") not in OPERATIVA_BLOCKS:
            raise ParseError("Bloque no válido.")
        context = views.operativa_block_context(request)
        return Response(
            operativa_screen(
                context, unrestricted=scope_for(request).unrestricted
            )
        )


class OperativaBillingView(APIView):
    """Operativa: facturabilidad global por mes (cifras del equipo)."""

    permission_classes = OperativaView.permission_classes

    def get(self, request: Request) -> Response:
        """Resumen mensual; ?actualizar=1 vuelve a leer las fuentes."""
        if not scope_for(request).unrestricted:
            # Es del equipo completo: no se puede recortar por cuenta.
            raise PermissionDenied("No tienes acceso a esta información.")
        summary = views.operations_summary_data(
            request.query_params.get("actualizar") == "1"
        )
        return Response(billing_screen(summary))
