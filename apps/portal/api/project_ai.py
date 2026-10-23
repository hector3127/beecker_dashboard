"""Lecturas de IA IXS: servicios anteriores, sin llamar al modelo."""

from collections.abc import Callable
from typing import Any

from rest_framework.views import APIView

from apps.access.checks import capability_permission
from apps.daily import ai_rpc, ixs_rpc
from apps.daily.services import ixs_ai, ixs_client, ixs_drive
from apps.daily.services.ixs_store import IxsStore, run_safely
from apps.portal.api.project_detail import ProjectRead


def history_read(
    action: Callable[[IxsStore, object], dict[str, Any]], project: str
) -> dict[str, Any]:
    """Mismo store y manejo de errores del registro RPC de IA."""
    return run_safely(lambda: action(ai_rpc.build_ixs_store(), project))


class ProjectClientReadView(ProjectRead):
    """Lectura compartida de cliente/acciones, antes ixsClienteAccionesLeer."""

    def load(self, project_id: str) -> dict[str, Any]:
        """Conserva la envoltura de las funciones de hojas IXS."""
        return run_safely(
            lambda: ixs_client.read_client_actions(
                ixs_rpc.build_store_sheets(), project_id
            )
        )


class ProjectAiAnalysisReadView(ProjectRead):
    """Último análisis guardado; no genera un análisis nuevo."""

    def load(self, project_id: str) -> dict[str, Any]:
        """Mismo servicio que ixsIAAnalisisLeer."""
        return history_read(ixs_ai.read_analysis, project_id)


class ProjectAiMemoryReadView(ProjectRead):
    """Cortes anteriores del proyecto."""

    def load(self, project_id: str) -> dict[str, Any]:
        """Mismo servicio que ixsIAMemoriaLeer."""
        return history_read(ixs_ai.read_memory, project_id)


class ProjectAiMinutesReadView(ProjectRead):
    """Minutas guardadas del proyecto."""

    def load(self, project_id: str) -> dict[str, Any]:
        """Mismo servicio que ixsIAMinutasLeer."""
        return history_read(ixs_ai.read_minutes, project_id)


class ProjectAiFoldersReadView(ProjectRead):
    """Configuración Drive: requiere integración como su RPC anterior."""

    permission_classes = [
        *APIView.permission_classes,
        capability_permission("manage_integrations", whole_portfolio=True),
    ]

    def load(self, project_id: str) -> dict[str, Any]:
        """Mismo servicio que ixsIADriveConfigLeer."""
        return history_read(ixs_drive.read_config, project_id)


class ProjectAiFilesReadView(ProjectRead):
    """Archivos de las carpetas conectadas; no consulta a Claude."""

    def load(self, project_id: str) -> dict[str, Any]:
        """Mismo servicio/contexto que ixsIADriveListar."""
        return run_safely(
            lambda: ixs_drive.list_files(
                ai_rpc.build_drive_context(), project_id
            )
        )
