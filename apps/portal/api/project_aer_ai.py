"""Fuentes guardadas de IA AER: no genera análisis ni llama al modelo."""

import json
from typing import Any

from rest_framework.views import APIView

from apps.access.checks import capability_permission
from apps.aer import ai_rpc
from apps.aer.services import ai_functions
from apps.daily.services.ixs_functions import fill_args
from apps.daily.services.ixs_store import run_safely
from apps.portal.api.project_detail import ProjectRead
from core.exceptions import InvalidRequestError

SOURCES = {
    "analisis": "obtenerUltimoAnalisisProyectoAER",
    "resumen": "obtenerUltimoResumenEjecutivoAER",
    "minutas": "listarMinutasIAProyectoAER",
    "config": "obtenerConfigCarpetaMinutasAER",
    "archivos": "buscarMinutasCarpetaAER",
}


def read(source: str, project: str, context: dict[str, Any]) -> dict[str, Any]:
    """Conserva firmas, proveedor y errores públicos de las lecturas RPC."""
    count, action, drive = ai_functions.FUNCTIONS[SOURCES[source]]
    args = (project, context) if source == "analisis" else (project,)
    return run_safely(
        lambda: action(ai_rpc.build_context(drive), fill_args(args, count))
    )


class AerAiReadView(ProjectRead):
    """view_operations y alcance total antes de consultar las fuentes."""

    source = ""

    def load(self, project_id: str) -> dict[str, Any]:
        """El contexto de comparación no sustituye el proyecto autorizado."""
        context: dict[str, Any] = {}
        if self.source == "analisis":
            try:
                context = json.loads(
                    self.request.query_params.get("contexto", "{}")
                )
            except (ValueError, TypeError) as error:
                raise InvalidRequestError(
                    "Contexto de IA no válido."
                ) from error
            if not isinstance(context, dict):
                raise InvalidRequestError("Envía un objeto de contexto de IA.")
        return read(self.source, project_id, context)


class AerAiConfigReadView(AerAiReadView):
    """manage_integrations, igual que obtenerConfigCarpetaMinutasAER."""

    permission_classes = [
        *APIView.permission_classes,
        capability_permission("manage_integrations", whole_portfolio=True),
    ]
