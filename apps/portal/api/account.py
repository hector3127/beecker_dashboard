"""API de la cuenta: resumen, horas por lote y finanzas."""

from rest_framework.exceptions import NotFound, ParseError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.checks import (
    capability_by_method,
    capability_permission,
    resolve,
)
from apps.portal.api.serializers import (
    account_consumption,
    account_finance,
    account_screen,
)
from apps.portal.services import account_screen as account_data
from apps.portal.services.executive_period import applied, parse

"""BKD.120.023 - API de la cuenta
Leer una cuenta pide view_operations o view_agreements; sus finanzas piden
view_costs. Una cuenta fuera del alcance responde 404 como si no existiera.
"""

AccountPermission = capability_by_method(
    ("view_operations", "view_agreements"), ("view_operations",)
)


def _client(request: Request) -> str:
    """La cuenta pedida, ya comprobada contra el alcance de la persona."""
    client = request.query_params.get("nombre", "").strip()
    if not client:
        raise ParseError("Falta el nombre de la cuenta.")
    if not resolve(request).scope.allows_account(client):
        raise NotFound("No existe esa cuenta.")
    return client


class AccountScreenView(APIView):
    """Proyectos, ROC y backlog de una cuenta."""

    permission_classes = [*APIView.permission_classes, AccountPermission]

    def get(self, request: Request) -> Response:
        """Resumen de ?nombre=; si no se pudo leer, available=false."""
        client = _client(request)
        result = account_data.load_account(client)
        return Response(account_screen(result, client))


class AccountConsumptionView(APIView):
    """Horas de Clockify de un lote de proyectos pendientes."""

    permission_classes = AccountScreenView.permission_classes

    def get(self, request: Request) -> Response:
        """Lote desde ?offset= para los ?pending_id= indicados."""
        client = _client(request)
        result = account_data.load_consumption(
            client,
            request.query_params.get("offset", 0),
            request.query_params.getlist("pending_id") or None,
        )
        return Response(account_consumption(result))


class AccountFinanceView(APIView):
    """Facturacion, margen y cobranza de la cuenta."""

    permission_classes = [
        *APIView.permission_classes,
        capability_permission("view_costs"),
    ]

    def get(self, request: Request) -> Response:
        """Cifras de la cuenta en el periodo (?periodo=...) o el ejercicio."""
        from apps.portal.services.account_profitability import (
            load_account_profitability,
        )
        from core.utils.text import normalize_name

        client = _client(request)
        query = request.query_params
        try:
            period = parse(query) if "periodo" in query else None
        except (ValueError, TypeError, OverflowError) as error:
            raise ParseError(str(error)) from error
        with applied(period):
            accounts = load_account_profitability()["accounts"]
        account = next(
            (
                a
                for a in accounts
                if normalize_name(a["name"]) == normalize_name(client)
            ),
            None,
        )
        return Response(account_finance(account))
