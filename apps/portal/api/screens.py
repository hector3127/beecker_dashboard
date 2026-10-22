"""Resumen de datos de cada pantalla: una peticion por pantalla."""

from django.utils import timezone
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.checks import capability_permission, scope_for
from apps.portal.api.serializers import eva4_screen
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
