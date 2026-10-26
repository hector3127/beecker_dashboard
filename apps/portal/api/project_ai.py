"""Lecturas de IA IXS: servicios anteriores, sin llamar al modelo."""

from collections.abc import Callable
from typing import Any

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.checks import capability_permission
from apps.daily import ai_rpc, ixs_rpc
from apps.daily.services import ixs_ai, ixs_client, ixs_drive
from apps.daily.services.ixs_store import IxsStore, run_safely
from apps.portal.api.errors import error_response
from apps.portal.api.operations import OperationsScreen
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


@method_decorator(csrf_protect, name="dispatch")
class AiWrite(OperationsScreen):
    """Mismos servicios y permisos RPC; cuerpo explícito y CSRF obligatorio."""

    permission_classes = [
        *APIView.permission_classes,
        capability_permission("edit_operations", whole_portfolio=True),
    ]

    def perform(self, project: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Implementado por cada acción concreta."""
        raise NotImplementedError

    def post(self, request: Request, project_id: str) -> Response:
        """No permite reemplazar el proyecto autorizado desde el cuerpo."""
        payload = request.data
        if not isinstance(payload, dict):
            return error_response(400, "validation", "Envía un objeto JSON.")
        return self.body(run_safely(lambda: self.perform(project_id, payload)))


class AiAnalyze(AiWrite):
    """ixsIAAnalizar, solo por acción expresa del usuario."""

    def perform(self, project: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Conserva contexto y bandera de actualización."""
        return ixs_ai.analyze_project(
            ai_rpc.build_claude(),
            ai_rpc.build_ixs_store(),
            (project, payload.get("contexto"), payload.get("forzar")),
        )


class AiAsk(AiWrite):
    """ixsIAPreguntar."""

    def perform(self, project: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Conserva pregunta y contexto, sin modificar prompts."""
        return ixs_ai.ask_question(
            ai_rpc.build_claude(),
            (project, payload.get("contexto"), payload.get("pregunta")),
        )


class AiMemorySave(AiWrite):
    """ixsIAMemoriaActualizar."""

    def perform(self, project: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Mismo snapshot y análisis del servicio anterior."""
        return ixs_ai.save_memory(
            ai_rpc.build_ixs_store(),
            project,
            payload.get("snapshot"),
            payload.get("analisis"),
        )


class AiMinuteSave(AiWrite):
    """ixsIAMinutaGuardar."""

    def perform(self, project: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Conserva tema, fecha y contenido editable."""
        return ixs_ai.save_minute(
            ai_rpc.build_ixs_store(),
            (
                project,
                payload.get("tema"),
                payload.get("fecha"),
                payload.get("contenido"),
            ),
        )


class AiFolderSave(AiWrite):
    """Configuración Drive, con la capacidad de integración original."""

    permission_classes = [
        *APIView.permission_classes,
        capability_permission("manage_integrations", whole_portfolio=True),
    ]

    def perform(self, project: str, payload: dict[str, Any]) -> dict[str, Any]:
        """IxsIADriveConfigGuardar."""
        return ixs_drive.save_folder(
            ai_rpc.build_drive_context(),
            project,
            payload.get("url"),
            payload.get("tipo"),
        )


class AiFolderRemove(AiFolderSave):
    """ixsIADriveConfigQuitar."""

    def perform(self, project: str, payload: dict[str, Any]) -> dict[str, Any]:
        """No modifica el identificador de carpeta."""
        return ixs_drive.remove_folder(
            ai_rpc.build_ixs_store(),
            project,
            payload.get("carpeta"),
            payload.get("tipo"),
        )


class AiDocumentRead(AiWrite):
    """Lectura de documento con view_operations, como el RPC original."""

    permission_classes = [
        *APIView.permission_classes,
        capability_permission("view_operations", whole_portfolio=True),
    ]

    def perform(self, project: str, payload: dict[str, Any]) -> dict[str, Any]:
        """ixsIADriveLeerDocumento; valida pertenencia en el mismo servicio."""
        return ixs_drive.read_document(
            ai_rpc.build_drive_context(), project, payload.get("archivo")
        )


class AiDriveMinute(AiWrite):
    """ixsIADriveGenerarMinuta."""

    def perform(self, project: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Mismos archivos, tema, fecha y notas; no guarda el borrador."""
        return ixs_drive.generate_minute(
            ai_rpc.build_claude(),
            ai_rpc.build_drive_context(),
            (
                project,
                payload.get("archivos"),
                payload.get("tema"),
                payload.get("fecha"),
                payload.get("notas"),
            ),
        )


class AiActionSave(AiWrite):
    """Acción revisada por el usuario desde una recomendación IA."""

    def perform(self, project: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Mismo servicio de Cliente/Acciones con proyecto fijado por ruta."""
        return ixs_client.save_record(
            ixs_rpc.build_store_sheets(),
            "accion",
            {**payload, "ID_Proyecto": project},
        )
