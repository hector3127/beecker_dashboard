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
    """Inversión acumulada por tags de proyectos activos EVA 1 y EVA 3."""

    def get(self, request: Request) -> Response:
        """Acumulado completo; los parámetros mensuales no lo recortan."""
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


class FacturabilityAuditView(OperationsScreen):
    """Consulta de personas y proyectos del mes, sin guardar cambios."""

    def get(self, request: Request) -> Response:
        """Valida el mes y aplica las áreas elegidas por el usuario."""
        from datetime import date

        from rest_framework.exceptions import ValidationError

        from apps.portal.services.facturability import role_key
        from apps.portal.services.facturability_audit import audit_month

        month = request.query_params.get("mes", "")
        try:
            day = date.fromisoformat(f"{month}-01")
            if len(month) != 7 or not 2000 <= day.year <= 2100:
                raise ValueError
        except ValueError as error:
            raise ValidationError(
                "Selecciona un mes válido (AAAA-MM)."
            ) from error
        roles = (
            frozenset(
                role_key(value) for value in request.query_params.getlist("rol")
            )
            if request.query_params.get("roles") == "1"
            else frozenset({"dev", "qa", "arq", "ba", "sm"})
        )
        data = audit_month(month, roles)
        data["can_edit"] = capability_permission(
            "edit_operations", whole_portfolio=True
        )().has_permission(request, self)
        if request.query_params.get("roles") == "1":
            data["published_summary"] = None
        return self.body(data)


class FacturabilityCorrectionView(OperationsScreen):
    """Guarda una corrección del desglose mensual."""

    permission_classes = [
        *OperationsScreen.permission_classes,
        capability_permission("edit_operations", whole_portfolio=True),
    ]

    def post(self, request: Request) -> Response:
        """Valida el cambio, guarda la revisión e invalida los resúmenes."""
        from datetime import date

        from django.core.cache import cache
        from rest_framework import serializers
        from rest_framework.exceptions import ValidationError

        from apps.portal.constants import FACTURABILITY_CACHE_PREFIX
        from apps.portal.services.facturability_corrections import (
            save_correction,
        )

        class Correction(serializers.Serializer):
            month = serializers.RegexField(r"^20[0-9]{2}-(0[1-9]|1[0-2])$")
            kind = serializers.ChoiceField(choices=("capacity", "project"))
            action = serializers.ChoiceField(
                choices=("save", "delete", "reset")
            )
            person = serializers.CharField(max_length=255)
            role = serializers.CharField(max_length=80, required=False)
            project = serializers.CharField(max_length=255, required=False)
            service = serializers.CharField(max_length=80, required=False)
            billable = serializers.BooleanField(required=False)
            hours = serializers.DecimalField(
                max_digits=9, decimal_places=4, min_value=0, required=False
            )
            target = serializers.ListField(
                required=False, min_length=5, max_length=5
            )

        serializer = Correction(data=request.data)
        serializer.is_valid(raise_exception=True)
        change = dict(serializer.validated_data)
        month = change.pop("month")
        target = change.get("target")
        if target and (
            not all(isinstance(x, str) for x in target[:4])
            or not isinstance(target[4], bool)
        ):
            raise ValidationError("Identificador de registro inválido.")
        if change["kind"] == "capacity":
            if change["action"] != "reset" and (
                change["action"] != "save" or "hours" not in change
            ):
                raise ValidationError("Indica las horas estimadas.")
        elif change["action"] == "reset":
            raise ValidationError("Solo se puede restablecer la capacidad.")
        elif change["action"] == "delete":
            if not target:
                raise ValidationError(
                    "Selecciona el registro que deseas eliminar."
                )
        elif (
            not {"role", "project", "service", "billable", "hours"}
            <= change.keys()
        ):
            raise ValidationError("Completa los datos del registro.")
        if "hours" in change:
            change["hours"] = float(change["hours"])
        try:
            save_correction(
                date.fromisoformat(month + "-01"),
                change,
                request.user.get_username()
                if request.user.is_authenticated
                else "",
            )
        except ValueError as error:
            raise ValidationError(str(error)) from error
        cache.delete_many(
            [
                FACTURABILITY_CACHE_PREFIX + month,
                views._operations_summary_key(),
                views._operations_summary_key() + ":fresh",
            ]
        )
        return self.body({"ok": True})
