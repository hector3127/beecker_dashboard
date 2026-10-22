"""API de acuerdos y pendientes: consulta, alta y cambios con permisos."""

from typing import Any

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.checks import capability_by_method, resolve
from apps.portal.api.errors import error_response
from apps.portal.services import agreements

"""BKD.120.018 - API de acuerdos
Consultar pide view_agreements (o edit_agreements); crear y cambiar pide
edit_agreements. Un acuerdo fuera del alcance responde 404 como si no
existiera; una cuenta fuera del alcance al crear o mover responde 403.
Cada registro trae las acciones que la persona puede hacer sobre el.
"""

AgreementPermission = capability_by_method(
    agreements.READ_CAPABILITIES, agreements.WRITE_CAPABILITIES
)

NOT_FOUND = "El registro no existe."
FORBIDDEN_ACCOUNT = "No tienes acceso a esa cuenta."


def _item(row: dict[str, Any], can_edit: bool) -> dict[str, Any]:
    return {**row, "actions": {"edit": can_edit, "change_status": can_edit}}


def _known(data: Any) -> dict[str, Any] | None:
    """Solo los campos editables; None si el cuerpo no es un objeto."""
    if not isinstance(data, dict):
        return None
    return {name: data[name] for name in agreements.EDITABLE if name in data}


class AgreementListView(APIView):
    """Lista los acuerdos del alcance y crea uno nuevo."""

    permission_classes = [*APIView.permission_classes, AgreementPermission]

    def get(self, request: Request) -> Response:
        """Acuerdos visibles (?account= y ?pending_only=1 los acotan)."""
        access = resolve(request)
        rows = agreements.visible_agreements(
            access.scope,
            request.query_params.get("account", "").strip(),
            request.query_params.get("pending_only") == "1",
        )
        can_edit = agreements.may(access, write=True)
        return Response(
            {
                "data": {
                    "items": [_item(row, can_edit) for row in rows],
                    "can_edit": can_edit,
                },
                "meta": {},
            }
        )

    def post(self, request: Request) -> Response:
        """Crea un acuerdo o pendiente en una cuenta del alcance."""
        access = resolve(request)
        values = _known(request.data)
        if values is None:
            return error_response(400, "validation", "Envía un objeto JSON.")
        try:
            saved = agreements.save_agreement(
                access.scope, agreements.with_defaults(values)
            )
        except agreements.InvalidAgreementError as error:
            return error_response(
                400, "validation", str(error), fields=error.errors
            )
        except agreements.OutOfScopeError:
            return error_response(403, "forbidden", FORBIDDEN_ACCOUNT)
        row = agreements.agreement_row(saved.pk)
        return Response({"data": _item(row, True), "meta": {}}, status=201)


class AgreementDetailView(APIView):
    """Cambia un acuerdo: el estado solo, o cualquiera de sus campos."""

    permission_classes = AgreementListView.permission_classes

    def patch(self, request: Request, pk: int) -> Response:
        """Edicion parcial; con solo {"status": ...} no toca nada mas."""
        access = resolve(request)
        agreement = agreements.find_agreement(access.scope, pk)
        if agreement is None:
            return error_response(404, "not_found", NOT_FOUND)
        changes = _known(request.data)
        if not changes:
            return error_response(400, "validation", "Indica qué cambiar.")
        try:
            if set(changes) == {"status"}:
                agreements.change_status(agreement, str(changes["status"]))
            else:
                agreements.save_agreement(
                    access.scope,
                    {**agreements.current_values(agreement), **changes},
                    agreement,
                )
        except agreements.InvalidStatusError:
            return error_response(
                400,
                "validation",
                "Estado no válido.",
                fields={"status": ["Estado no válido."]},
            )
        except agreements.InvalidAgreementError as error:
            return error_response(
                400, "validation", str(error), fields=error.errors
            )
        except agreements.OutOfScopeError:
            return error_response(403, "forbidden", FORBIDDEN_ACCOUNT)
        row = agreements.agreement_row(agreement.pk)
        return Response({"data": _item(row, True), "meta": {}})
