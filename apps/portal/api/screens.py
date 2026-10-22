"""Resumen de datos de cada pantalla: una peticion por pantalla."""

import json
from typing import Any

from django.utils import timezone
from rest_framework.exceptions import NotFound, ParseError, PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.checks import capability_permission, scope_for
from apps.portal import views
from apps.portal.api.errors import error_response
from apps.portal.api.serializers import (
    billing_screen,
    eva4_screen,
    executive_screen,
    manager_screen,
    margins_screen,
    operativa_screen,
)
from apps.portal.services import eva4
from apps.portal.services import executive_screen as executive_data
from apps.portal.services.executive_period import applied, bounds, parse
from apps.portal.services.margins_screen import load_margins

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


class MarginsScreenView(APIView):
    """Comparativa de margenes vendido y real por oportunidad."""

    permission_classes = [
        *APIView.permission_classes,
        capability_permission("view_costs"),
    ]

    def get(self, request: Request) -> Response:
        """Periodo (?periodo=...) y cuenta (?nombre=) opcionales."""
        query = request.query_params
        try:
            period = parse(query) if "periodo" in query else None
        except (ValueError, TypeError, OverflowError) as error:
            raise ParseError(str(error)) from error
        account = query.get("nombre", "").strip()
        scope = scope_for(request)
        if account and not scope.allows_account(account):
            raise NotFound("No existe esa cuenta.")
        with applied(period):
            result = load_margins(account, scope)
        return Response(margins_screen(result, account))


class MarginsRefreshView(APIView):
    """Prepara los costos del periodo sin esperar a las fuentes."""

    permission_classes = MarginsScreenView.permission_classes

    @staticmethod
    def _state(status: dict[str, Any]) -> Response:
        from apps.portal.services.financial_cache import (
            cached_financial_snapshot,
        )

        cut = bool(cached_financial_snapshot().get("loaded_at"))
        return Response(
            {
                "data": {
                    "state": status.get("state"),
                    "has_financial_cut": cut,
                }
            }
        )

    def get(self, request: Request) -> Response:
        """Estado de la preparacion en curso."""
        from apps.portal.services.executive_refresh import refresh_status

        return self._state(refresh_status())

    def post(self, request: Request) -> Response:
        """Inicia la preparacion; responde de inmediato."""
        from apps.portal.services.executive_refresh import request_refresh

        return self._state(request_refresh(force=True))


class ProjectCostView(APIView):
    """Personas, bandas y tarifas de un Project ID dentro de una cuenta."""

    permission_classes = MarginsScreenView.permission_classes

    def get(self, request: Request) -> Response:
        """Desglose de ?id= para la cuenta ?nombre=, con el periodo activo."""
        if not request.query_params.get("id"):
            raise ParseError("Falta el Project ID.")
        response = views.costos_revenue(request._request)
        payload = json.loads(response.content)
        if response.status_code >= 400:
            codes = {401: "unauthenticated", 403: "forbidden", 404: "not_found"}
            return error_response(
                response.status_code,
                codes.get(response.status_code, "upstream"),
                str(payload.get("error", "No se pudo consultar el detalle.")),
            )
        return Response({"data": payload, "meta": {}})


MANAGER_STAGES = {"base", "inv", "horas"}


class ManagerScreenView(APIView):
    """Delivery Manager: proyectos primero; inversion y horas por separado."""

    permission_classes = OperativaView.permission_classes

    def get(self, request: Request, slug: str) -> Response:
        """Hasta el paso ?bloque= (base, inv u horas); sin el, solo la base."""
        stage = request.query_params.get("bloque", "base")
        if stage not in MANAGER_STAGES:
            raise ParseError("Bloque no válido.")
        scope = scope_for(request)
        try:
            base, extra, hours = views.dm_state(slug, stage, scope)
        except views.ManagerUnavailableError as error:
            return error_response(502, "upstream", str(error))
        rows = views.dm_rows(base, extra)
        return Response(manager_screen(base, extra, hours, rows))


class ExecutiveScreenView(APIView):
    """Business Overview: el ultimo corte preparado, sin consultar fuentes."""

    permission_classes = [
        *APIView.permission_classes,
        capability_permission("view_executive"),
    ]

    def get(self, request: Request) -> Response:
        """Corte del periodo (?periodo=...) o del ejercicio en curso."""
        from apps.portal.services.executive_operations import (
            cached_operations_snapshot,
        )
        from apps.portal.services.financial_cache import (
            cached_financial_snapshot,
        )

        query = request.query_params
        try:
            period = parse(query) if "periodo" in query else None
        except (ValueError, TypeError, OverflowError) as error:
            raise ParseError(str(error)) from error
        scope = scope_for(request)
        with applied(period):
            financial = cached_financial_snapshot()
            operations = cached_operations_snapshot()
            chosen = bounds()
        figures = executive_data.company_figures(financial, operations, scope)
        accounts = executive_data.visible_accounts(financial, scope)
        meta = {
            "loaded_at": financial.get("loaded_at"),
            "start": chosen[0].isoformat(),
            "end": chosen[1].isoformat(),
            "scope": scope.kind,
            "blocks": {
                "financial": bool(financial.get("loaded_at")),
                "operations": operations.get("projects") is not None,
                "commercial": bool(financial.get("commercial")),
                "accounts": accounts is not None,
            },
        }
        return Response(executive_screen(figures, accounts, meta))
