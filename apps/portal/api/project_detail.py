"""Detalle: servicios originales y permisos de lecturas y acciones migradas."""

from typing import Any

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.checks import capability_permission
from apps.aer import rpc as aer
from apps.aer.services import dashboard
from apps.azure_devops.rpc import get_project_raid
from apps.clockify import project_rpc
from apps.daily import ai_rpc, ixs_rpc
from apps.daily import rpc as daily
from apps.daily.ixs_rpc import build_store_sheets, get_ixs_panel
from apps.daily.services import bee_com, claude_assist
from apps.daily.services.ixs_planning import (
    delete_plan,
    read_plan,
    read_resources,
    save_plan,
    save_resource,
)
from apps.daily.services.ixs_store import run_safely
from apps.dashboard.rpc import get_available_filters
from apps.ejecutivo import write_rpc as milestones
from apps.ejecutivo.rpc import get_executive_dashboard
from apps.portal.api.errors import error_response
from apps.portal.api.operations import OperationsScreen
from core.exceptions import DashboardError
from core.sheets.factory import build_sheet_repository


def aer_dashboard(project_id: str) -> dict[str, Any]:
    """Construye getDashboardAERTYMProyecto sin transporte RPC."""

    def load() -> dict[str, Any]:
        store = aer.build_store()
        return dashboard.build_dashboard(
            store, project_id, aer.build_hours(store)
        )

    return run_safely(load)


class ProjectRead(OperationsScreen):
    """Conserva el permiso y alcance total exigidos por estas lecturas RPC.

    Los datos ejecutivos todavía incluyen bloques de todo el portafolio.
    No se abre acceso limitado hasta poder recortarlos en sus servicios.
    """

    def load(self, project_id: str) -> dict[str, Any]:
        """Carga del servicio concreto, definida en cada endpoint."""
        raise NotImplementedError

    def get(self, request: Request, project_id: str = "") -> Response:
        """Contrato original en {data, meta}, con errores públicos estables."""
        try:
            return self.body(self.load(project_id))
        except DashboardError as error:
            return error_response(
                error.http_status, error.code, error.build_message()
            )


class ProjectFiltersView(ProjectRead):
    """Metadatos para reconocer el servicio del proyecto antes de cargarlo."""

    def load(self, project_id: str) -> dict[str, Any]:
        """Lee los mismos metadatos de servicio y cliente."""
        return get_available_filters()


class ProjectExecutiveView(ProjectRead):
    """Dashboard IXB, SaaS, RaaS y vista ejecutiva anterior."""

    def load(self, project_id: str) -> dict[str, Any]:
        """Invoca el servicio ejecutivo existente con el ID exacto."""
        return get_executive_dashboard(project_id)


class ProjectRaidRegistryView(ProjectRead):
    """Registro RAID del proyecto en Azure DevOps (pestaña Gestión RAID)."""

    def load(self, project_id: str) -> dict[str, Any]:
        """Mismo servicio que ixsRaidListarProyecto; forzar=1 omite la caché."""
        force = self.request.query_params.get("forzar") == "1"

        return ixs_rpc.list_raid(project_id, force)


class ProjectAerView(ProjectRead):
    """Dashboard AER/T&M, sin cambiar sus horas ni sus reglas de salud."""

    def load(self, project_id: str) -> dict[str, Any]:
        """Construye AER/T&M con las fuentes y manejo de errores existentes."""
        return aer_dashboard(project_id)


def tasks_dashboard(project_id: str) -> dict[str, Any]:
    """Mismo resumen de tasks, tags y rango de Clockify del RPC anterior."""
    return run_safely(
        lambda: project_rpc.tasks_summary(build_sheet_repository(), project_id)
    )


def stages_dashboard(project_id: str) -> dict[str, Any]:
    """Mismas fases históricas y suspensiones del proyecto."""
    return run_safely(
        lambda: project_rpc.project_stages(build_sheet_repository(), project_id)
    )


def resources_dashboard(project_id: str) -> dict[str, Any]:
    """Misma lectura de asignaciones y estados por proyecto."""
    return run_safely(lambda: read_resources(build_store_sheets(), project_id))


class ProjectRaidView(ProjectRead):
    """RAID diferido del ejecutivo, sin ampliar alcance respecto al RPC."""

    def load(self, project_id: str) -> dict[str, Any]:
        """Invoca el servicio de Azure y pendientes existente."""
        return get_project_raid(project_id)


class ProjectTasksView(ProjectRead):
    """Horas por task e inversión, sin otro recálculo de consumos."""

    def load(self, project_id: str) -> dict[str, Any]:
        """Entrega el mismo resumen de Clockify."""
        return tasks_dashboard(project_id)


def records_dashboard(project_id: str) -> dict[str, Any]:
    """Mismos registros detallados, rango y etiquetas del RPC de Clockify."""
    return run_safely(
        lambda: project_rpc.project_entries(
            build_sheet_repository(), project_id
        )
    )


class ProjectRecordsView(ProjectRead):
    """Registros del proyecto con el alcance total del transporte anterior."""

    def load(self, project_id: str) -> dict[str, Any]:
        """Invoca el servicio existente sin filtrar ni recalcular horas."""
        return records_dashboard(project_id)


class ProjectStagesView(ProjectRead):
    """Histórico diferido para completar la línea de tiempo."""

    def load(self, project_id: str) -> dict[str, Any]:
        """Entrega las etapas del ID exacto, incluidos CR y sprints."""
        return stages_dashboard(project_id)


class ProjectResourcesView(ProjectRead):
    """Estado de las asignaciones del proyecto, solo lectura."""

    def load(self, project_id: str) -> dict[str, Any]:
        """Entrega los mismos estados de recursos que ixsRecursosLeer."""
        return resources_dashboard(project_id)


def planning_dashboard(project_id: str) -> dict[str, Any]:
    """Mismas vacaciones y compromisos de ixsPlanLeer."""
    return run_safely(lambda: read_plan(build_store_sheets(), project_id))


class ProjectPlanningView(ProjectRead):
    """Planeación con el mismo alcance que el transporte anterior."""

    def load(self, project_id: str) -> dict[str, Any]:
        """Consulta la fuente existente sin recalcular hitos."""
        return planning_dashboard(project_id)


class ProjectPlanningAzureView(ProjectRead):
    """Panel diferido de Planeación, sin forzar refresco de Azure."""

    def load(self, project_id: str) -> dict[str, Any]:
        """Mismo panel, caché y filtro To Be / Change Request."""
        return get_ixs_panel(project_id, False)


class ProjectAzureView(ProjectRead):
    """Panel Azure de la pestaña, con actualización explícita de su caché."""

    def load(self, project_id: str) -> dict[str, Any]:
        """Mismo servicio y parámetro que obtenerPanelAzureProyectoIXS."""
        return get_ixs_panel(
            project_id, self.request.query_params.get("forzar") == "1"
        )


def save_plan_dashboard(
    plan_type: str, payload: dict[str, Any]
) -> dict[str, Any]:
    """Conserva el servicio y las validaciones de ixsPlanGuardar."""
    return run_safely(
        lambda: save_plan(build_store_sheets(), plan_type, payload)
    )


def delete_plan_dashboard(
    plan_type: str, project_id: str, uid: object
) -> dict[str, Any]:
    """Conserva el borrado por tipo, proyecto y UID de ixsPlanEliminar."""
    return run_safely(
        lambda: delete_plan(build_store_sheets(), plan_type, project_id, uid)
    )


@method_decorator(csrf_protect, name="dispatch")
class ProjectPlanningWriteView(OperationsScreen):
    """Edición de planeación con alcance total y CSRF, igual que Recursos."""

    permission_classes = [
        *APIView.permission_classes,
        capability_permission("edit_operations", whole_portfolio=True),
    ]

    def perform(
        self, plan_type: str, project_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Guarda con el proyecto autorizado en la ruta."""
        return save_plan_dashboard(
            plan_type, {**payload, "idProyecto": project_id}
        )

    def post(
        self, request: Request, project_id: str, plan_type: str
    ) -> Response:
        """Delega las reglas de negocio al mismo servicio anterior."""
        if not isinstance(request.data, dict):
            return error_response(400, "validation", "Envía un objeto JSON.")
        try:
            return self.body(self.perform(plan_type, project_id, request.data))
        except DashboardError as error:
            return error_response(
                error.http_status, error.code, error.build_message()
            )


class ProjectPlanningDeleteView(ProjectPlanningWriteView):
    """Borrado por POST; hereda permiso, alcance y protección CSRF."""

    def perform(
        self, plan_type: str, project_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Un UID ajeno sigue rechazándose dentro del servicio existente."""
        return delete_plan_dashboard(plan_type, project_id, payload.get("uid"))


def save_resource_dashboard(payload: dict[str, Any]) -> dict[str, Any]:
    """Mismo guardado y validaciones de ixsRecursosGuardar."""
    return run_safely(lambda: save_resource(build_store_sheets(), payload))


@method_decorator(csrf_protect, name="dispatch")
class ProjectResourceSaveView(OperationsScreen):
    """Escritura con edit_operations, alcance total y CSRF obligatorio."""

    permission_classes = [
        *APIView.permission_classes,
        capability_permission("edit_operations", whole_portfolio=True),
    ]

    def post(self, request: Request, project_id: str) -> Response:
        """Guarda sobre el ID de la ruta, con el servicio anterior."""
        if not isinstance(request.data, dict):
            return error_response(400, "validation", "Envía un objeto JSON.")
        payload = {**request.data, "idProyecto": project_id}
        try:
            return self.body(save_resource_dashboard(payload))
        except DashboardError as error:
            return error_response(
                error.http_status, error.code, error.build_message()
            )


@method_decorator(csrf_protect, name="dispatch")
class WorkItemProgressView(OperationsScreen):
    """Mismo alcance global que el RPC: no implica pertenencia a una cuenta."""

    permission_classes = [
        *APIView.permission_classes,
        capability_permission("edit_operations", whole_portfolio=True),
    ]

    def perform(
        self, work_item_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Mismo guardado en WorkItems_Avance y mismas validaciones."""
        return daily.save_work_item_progress(
            work_item_id, payload.get("campo"), payload.get("valor")
        )

    def post(self, request: Request, work_item_id: int) -> Response:
        """El ID de la ruta prevalece; sin reglas nuevas de negocio."""
        if not isinstance(request.data, dict):
            return error_response(400, "validation", "Envía un objeto JSON.")
        try:
            return self.body(self.perform(work_item_id, request.data))
        except DashboardError as error:
            return error_response(
                error.http_status, error.code, error.build_message()
            )


class WorkItemCommentView(WorkItemProgressView):
    """Comentario con el mismo servicio fechado y CSRF heredado."""

    def perform(
        self, work_item_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Conserva conexión, proyecto activo y fecha local del servicio."""
        return daily.add_comment(work_item_id, payload.get("comentario"))


class ProjectMilestoneTypesView(OperationsScreen):
    """Tipos de hito ya usados en la hoja Proyectos (lectura global)."""

    def get(self, request: Request) -> Response:
        """Mismo servicio que obtenerTiposHitosExistentes."""
        return self.body({"tipos": milestones.get_milestone_types()})


@method_decorator(csrf_protect, name="dispatch")
class ProjectMilestoneWriteView(OperationsScreen):
    """Escritura de hitos: edit_operations, alcance total y CSRF."""

    permission_classes = [
        *APIView.permission_classes,
        capability_permission("edit_operations", whole_portfolio=True),
    ]

    def perform(
        self, project_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Servicio concreto, definido en cada endpoint."""
        raise NotImplementedError

    def post(self, request: Request, project_id: str = "") -> Response:
        """El ID de la ruta prevalece; las reglas siguen en el servicio."""
        if not isinstance(request.data, dict):
            return error_response(400, "validation", "Envía un objeto JSON.")
        try:
            return self.body(self.perform(project_id, request.data))
        except DashboardError as error:
            return error_response(
                error.http_status, error.code, error.build_message()
            )


class ProjectMilestoneSaveView(ProjectMilestoneWriteView):
    """Alta de varios hitos en un lote (guardarHitosAdicionalesLote)."""

    def perform(
        self, project_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Lista de {tipo, fechaISO, observacion}."""
        return milestones.save_milestone_batch(project_id, payload.get("hitos"))


class ProjectMilestoneEditView(ProjectMilestoneWriteView):
    """Cambio de fecha y observación de una entrada (editarHitoAdicional)."""

    def perform(
        self, project_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """La entrada se identifica por tipo e índice, como antes."""
        return milestones.edit_milestone_entry(
            project_id,
            payload.get("tipo"),
            payload.get("indice"),
            payload.get("fechaISO"),
            payload.get("observacion"),
        )


class ProjectMilestoneDeleteView(ProjectMilestoneWriteView):
    """Borrado de una entrada por tipo e índice (eliminarHitoAdicional)."""

    def perform(
        self, project_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Mismo servicio, con el proyecto de la ruta."""
        return milestones.delete_milestone_entry(
            project_id, payload.get("tipo"), payload.get("indice")
        )


class RaidFieldTypesView(ProjectRead):
    """Opciones de los campos principales del tipo RAID elegido."""

    def load(self, project_id: str) -> dict[str, Any]:
        """Mismo servicio que ixsRaidCamposTipo."""
        return ixs_rpc.raid_field_types(
            project_id, self.request.query_params.get("tipo", "")
        )


class RaidCreationOptionsView(ProjectRead):
    """Iteraciones, usuarios, relacionados y campos para el alta."""

    def load(self, project_id: str) -> dict[str, Any]:
        """Mismo servicio que ixsRaidAltaOpciones."""
        return ixs_rpc.raid_creation_options(
            project_id, self.request.query_params.get("tipo", "")
        )


@method_decorator(csrf_protect, name="dispatch")
class RaidPromptView(ProjectRead):
    """Prompt vigente del tipo RAID; guardarlo pide manage_integrations."""

    def get_permissions(self) -> list[Any]:
        """Leer pide operación; guardar, manage_integrations (como el RPC)."""
        if self.request.method == "POST":
            return [
                *(p() for p in APIView.permission_classes),
                capability_permission(
                    "manage_integrations", whole_portfolio=True
                )(),
            ]

        return super().get_permissions()

    def load(self, project_id: str) -> dict[str, Any]:
        """Mismo servicio que ixsRaidObtenerPrompt."""
        return claude_assist.read_raid_prompt(
            ai_rpc.build_claude(), self.request.query_params.get("tipo", "")
        )

    def post(self, request: Request, project_id: str = "") -> Response:
        """Mismo servicio que ixsRaidGuardarPrompt (vacío = estándar)."""
        if not isinstance(request.data, dict):
            return error_response(400, "validation", "Envía un objeto JSON.")
        try:
            return self.body(
                claude_assist.save_raid_prompt(
                    ai_rpc.build_claude(),
                    request.data.get("tipo"),
                    request.data.get("prompt"),
                )
            )
        except DashboardError as error:
            return error_response(
                error.http_status, error.code, error.build_message()
            )


class RaidSuggestView(ProjectMilestoneWriteView):
    """Sugerencia de Claude para el formulario RAID (nada se publica)."""

    def perform(
        self, project_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Mismo servicio que ixsRaidSugerirClaude."""
        return claude_assist.suggest_raid(
            ai_rpc.build_claude(),
            payload.get("tipo"),
            payload.get("descripcion"),
        )


class RaidCreateView(ProjectMilestoneWriteView):
    """Crea el Risk, Issue u Opportunity en Azure DevOps."""

    def perform(
        self, project_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """El proyecto de la ruta prevalece; el servicio valida el resto."""
        return ixs_rpc.create_raid_record(
            project_id, payload.get("tipo"), payload.get("datos")
        )


def communications_dashboard() -> dict[str, Any]:
    """Mismos comunicados de beeComListar (son del portafolio)."""
    return run_safely(lambda: bee_com.list_communications(build_store_sheets()))


class ProjectCommunicationsView(ProjectRead):
    """Centro de Comunicación de IXB/SaaS/RaaS."""

    def load(self, project_id: str) -> dict[str, Any]:
        """Lista global; la pantalla filtra por el proyecto abierto."""
        return communications_dashboard()


class ProjectCommunicationSaveView(ProjectMilestoneWriteView):
    """Publica o edita un comunicado (edit_operations, alcance total, CSRF)."""

    def perform(
        self, project_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Mismo guardado y validaciones de beeComGuardar."""
        return run_safely(
            lambda: bee_com.save_communication(build_store_sheets(), payload)
        )
