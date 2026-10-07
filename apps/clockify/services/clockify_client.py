"""Cliente HTTP de las APIs de Clockify."""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any
from urllib.parse import quote

import requests

from apps.clockify.constants import (
    CLOCKIFY_BASE_URL,
    CLOCKIFY_REPORTS_URL,
    FORBIDDEN_STATUS,
    PROJECTS_MAX_PAGES,
    PROJECTS_PAGE_SIZE,
    REPORT_BLOCK_DAYS,
    REPORT_MAX_ATTEMPTS,
    REPORT_MAX_REQUESTS,
    REPORT_PAGE_SIZE,
    REPORT_PAUSE_SECONDS,
    REPORT_RETRY_WAIT_SECONDS,
    REQUEST_TIMEOUT_SECONDS,
    RETRY_STATUS_TOO_MANY_REQUESTS,
    SERVER_ERROR_STATUS,
    SINGLE_RETRY_WAIT_SECONDS,
    SUCCESS_STATUS_LIMIT,
    TASKS_MAX_PAGES,
    TASKS_PAGE_SIZE,
    UNAUTHORIZED_STATUS,
)
from apps.clockify.exceptions import (
    ClockifyReportForbiddenError,
    ClockifyRequestError,
)

"""BKD.020.004 - Cliente de Clockify
Equivale a listarWorkspacesClockify(), _obtenerProyectosClockify() y
_clockifyReporteProyectoV17_() de ClockifyService.gs.
"""

logger = logging.getLogger(__name__)

JsonObject = dict[str, Any]


@dataclass(frozen=True, slots=True)
class ClockifyProject:
    """Proyecto visible en el workspace de Clockify."""

    project_id: str
    name: str
    client_id: str = ""


class ClockifyClient:
    """Llamadas a la API estandar y a la API de reportes de Clockify."""

    def __init__(
        self,
        api_key: str,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._session = session or requests.Session()
        self._session.headers.update({"X-Api-Key": api_key})
        self._sleep = sleep

    def list_workspaces(self) -> list[JsonObject]:
        """
        Lista los workspaces visibles con la API key.

        Returns:
            Workspaces con id y nombre.
        """
        response = self._send("GET", f"{CLOCKIFY_BASE_URL}/workspaces")
        payload = self._read_json(response)

        if not isinstance(payload, list):
            raise ClockifyRequestError(
                "Clockify devolvio un listado de workspaces inesperado.",
            )

        return [
            {"id": workspace.get("id"), "nombre": workspace.get("name")}
            for workspace in payload
        ]

    def list_projects(self, workspace_id: str) -> list[ClockifyProject]:
        """
        Lista todos los proyectos del workspace, pagina por pagina.

        Args:
            workspace_id: ID del workspace de Clockify.

        Returns:
            Los proyectos del workspace.

        Raises:
            ClockifyRequestError: Cuando Clockify responde con error.
        """
        projects: list[ClockifyProject] = []

        for page_number in range(1, PROJECTS_MAX_PAGES + 1):
            response = self._send(
                "GET",
                f"{CLOCKIFY_BASE_URL}/workspaces/{quote(workspace_id)}"
                "/projects",
                params={
                    "page-size": PROJECTS_PAGE_SIZE,
                    "page": page_number,
                },
            )
            self._raise_for_status(response, "listar proyectos")
            page_items = self._read_json(response)

            if not isinstance(page_items, list):
                raise ClockifyRequestError(
                    "Clockify devolvio un listado de proyectos inesperado.",
                )

            projects.extend(
                ClockifyProject(
                    project_id=str(item.get("id", "")),
                    name=str(item.get("name", "")),
                    client_id=str(item.get("clientId") or ""),
                )
                for item in page_items
            )

            if len(page_items) < PROJECTS_PAGE_SIZE:
                return projects

        raise ClockifyRequestError(
            "La lista de proyectos supera 100 paginas; se detuvo para "
            "evitar una espera indefinida.",
        )

    def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> requests.Response:
        """
        GET a la API estandar sin validar el codigo de respuesta.

        Si Clockify responde 429 espera y reintenta una vez, como
        _fetchConReintento().

        Args:
            path: Ruta despues de /api/v1 (por ejemplo /workspaces).
            params: Parametros de la URL.

        Returns:
            La respuesta tal cual.
        """
        url = f"{CLOCKIFY_BASE_URL}{path}"
        response = self._send("GET", url, params=params)

        if response.status_code == RETRY_STATUS_TOO_MANY_REQUESTS:
            self._sleep(SINGLE_RETRY_WAIT_SECONDS)
            response = self._send("GET", url, params=params)

        return response

    def list_project_tasks(
        self,
        workspace_id: str,
        project_id: str,
    ) -> list[JsonObject]:
        """
        Lista las tasks de un proyecto, pagina por pagina.

        Args:
            workspace_id: ID del workspace.
            project_id: ID del proyecto de Clockify.

        Returns:
            Tasks con id, name y status.

        Raises:
            ClockifyRequestError: Cuando Clockify responde con error.
        """
        tasks: list[JsonObject] = []
        path = (
            f"/workspaces/{quote(workspace_id)}/projects/"
            f"{quote(project_id)}/tasks"
        )

        for page_number in range(1, TASKS_MAX_PAGES + 1):
            response = self.get(
                path,
                {"page-size": TASKS_PAGE_SIZE, "page": page_number},
            )

            if response.status_code >= SUCCESS_STATUS_LIMIT:
                raise ClockifyRequestError(
                    f"Clockify tasks respondió {response.status_code}: "
                    f"{response.text[:200]}",
                    status_code=response.status_code,
                )

            page_items = self._read_json(response) or []

            if not isinstance(page_items, list):
                raise ClockifyRequestError(
                    "Clockify devolvio un listado de tasks inesperado.",
                )

            tasks.extend(
                {
                    "id": item.get("id"),
                    "name": item.get("name") or "",
                    "status": item.get("status") or "",
                }
                for item in page_items
                if isinstance(item, dict)
            )

            if len(page_items) < TASKS_PAGE_SIZE:
                return tasks

        raise ClockifyRequestError(
            "La lista de tasks supera 100 paginas; se detuvo para evitar "
            "una espera indefinida.",
        )

    def fetch_detailed_report(
        self,
        workspace_id: str,
        project_id: str,
        start_date: date,
        end_date: date,
        timezone_name: str,
    ) -> list[JsonObject]:
        """
        Descarga el reporte detallado de un proyecto en bloques de 31 dias.

        Args:
            workspace_id: ID del workspace.
            project_id: ID del proyecto en Clockify.
            start_date: Primer dia del rango.
            end_date: Ultimo dia del rango.
            timezone_name: Zona horaria del reporte.

        Returns:
            Los registros del reporte sin duplicados.
        """
        report_entries, _ = self.fetch_detailed_report_counted(
            workspace_id,
            project_id,
            start_date,
            end_date,
            timezone_name,
        )

        return report_entries

    def fetch_detailed_report_counted(
        self,
        workspace_id: str,
        project_id: str,
        start_date: date,
        end_date: date,
        timezone_name: str,
    ) -> tuple[list[JsonObject], int]:
        """
        Descarga el reporte detallado y cuenta las solicitudes enviadas.

        Args:
            workspace_id: ID del workspace.
            project_id: ID del proyecto en Clockify.
            start_date: Primer dia del rango.
            end_date: Ultimo dia del rango.
            timezone_name: Zona horaria del reporte.

        Returns:
            Los registros sin duplicados y el numero de solicitudes.

        Raises:
            ClockifyRequestError: Cuando el rango o la respuesta no son
                validos. No se regresan datos parciales.
        """
        if start_date > end_date:
            raise ClockifyRequestError(
                f"Rango de fechas invalido: {start_date} > {end_date}.",
            )

        entries_by_id: dict[str, JsonObject] = {}
        request_count = 0
        block_start = start_date

        while block_start <= end_date:
            block_end = min(
                end_date,
                block_start + timedelta(days=REPORT_BLOCK_DAYS - 1),
            )
            request_count = self._fetch_report_block(
                workspace_id,
                project_id,
                (block_start, block_end),
                timezone_name,
                entries_by_id,
                request_count,
            )
            block_start = block_end + timedelta(days=1)

        return list(entries_by_id.values()), request_count

    def _fetch_report_block(
        self,
        workspace_id: str,
        project_id: str,
        date_block: tuple[date, date],
        timezone_name: str,
        entries_by_id: dict[str, JsonObject],
        request_count: int,
    ) -> int:
        """Descarga todas las paginas de un bloque de fechas."""
        block_start, block_end = date_block
        url = (
            f"{CLOCKIFY_REPORTS_URL}/workspaces/{quote(workspace_id)}"
            "/reports/detailed"
        )
        page_signatures: set[str] = set()
        page_number = 1

        while True:
            if request_count >= REPORT_MAX_REQUESTS:
                raise ClockifyRequestError(
                    "El reporte excedio el tamano permitido. No se "
                    "guardaron horas incompletas.",
                )

            if request_count:
                self._sleep(REPORT_PAUSE_SECONDS)

            payload = build_report_payload(
                project_id,
                block_start,
                block_end,
                page_number,
                timezone_name,
            )
            response = self._send_with_retries(url, payload)
            request_count += 1
            self._raise_report_error(response, date_block, page_number)

            page_entries = read_report_entries(self._read_json(response))
            signature = "|".join(
                str(entry.get("_id") or entry.get("id"))
                for entry in page_entries
            )

            if page_entries and signature in page_signatures:
                raise ClockifyRequestError(
                    "Clockify repitio una pagina del reporte. No se "
                    "guardo un total incompleto.",
                )

            page_signatures.add(signature)
            store_report_entries(page_entries, project_id, entries_by_id)

            if len(page_entries) < REPORT_PAGE_SIZE:
                return request_count

            page_number += 1

    def get_users_page(
        self,
        workspace_id: str,
        page_number: int,
        page_size: int,
    ) -> requests.Response:
        """
        Pide una pagina de los usuarios activos del workspace.

        Args:
            workspace_id: ID del workspace de Clockify.
            page_number: Pagina (base 1).
            page_size: Usuarios por pagina.

        Returns:
            La respuesta HTTP; quien llama interpreta el estatus.

        Raises:
            ClockifyRequestError: Cuando no hay conexion.
        """
        return self._send(
            "GET",
            f"{CLOCKIFY_BASE_URL}/workspaces/{quote(workspace_id)}/users",
            params={"page": page_number, "page-size": page_size},
        )

    def post_workspace_report(
        self,
        workspace_id: str,
        payload: JsonObject,
    ) -> requests.Response:
        """
        Pide una pagina del reporte detallado de todo el workspace.

        Reintenta cuando Clockify limita peticiones o falla; quien llama
        interpreta el estatus de la respuesta.

        Args:
            workspace_id: ID del workspace de Clockify.
            payload: Cuerpo del reporte detallado.

        Returns:
            La respuesta HTTP de Clockify.

        Raises:
            ClockifyRequestError: Cuando no hay conexion.
        """
        url = (
            f"{CLOCKIFY_REPORTS_URL}/workspaces/{quote(workspace_id)}"
            "/reports/detailed"
        )

        return self._send_with_retries(url, payload)

    def _send_with_retries(
        self,
        url: str,
        payload: JsonObject,
    ) -> requests.Response:
        """Reintenta cuando Clockify limita peticiones o falla."""
        response = self._send("POST", url, json=payload)

        for attempt_number in range(1, REPORT_MAX_ATTEMPTS):
            if not is_retryable_status(response.status_code):
                break

            self._sleep(REPORT_RETRY_WAIT_SECONDS * attempt_number)
            response = self._send("POST", url, json=payload)

        return response

    def _send(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> requests.Response:
        """
        Envia una peticion HTTP a Clockify.

        Raises:
            ClockifyRequestError: Cuando no hay conexion.
        """
        try:
            return self._session.request(
                method,
                url,
                timeout=REQUEST_TIMEOUT_SECONDS,
                **kwargs,
            )
        except requests.RequestException as error:
            logger.warning("No hubo conexion con Clockify: %s", error)

            raise ClockifyRequestError(
                "No hubo conexion con Clockify.",
            ) from error

    def _raise_for_status(
        self,
        response: requests.Response,
        action: str,
    ) -> None:
        """Lanza un error cuando la respuesta no es exitosa."""
        if response.status_code < SUCCESS_STATUS_LIMIT:
            return

        raise ClockifyRequestError(
            f"Clockify respondio {response.status_code} al {action}.",
            status_code=response.status_code,
        )

    def _raise_report_error(
        self,
        response: requests.Response,
        date_block: tuple[date, date],
        page_number: int,
    ) -> None:
        """Traduce el estatus HTTP del reporte detallado."""
        status_code = response.status_code

        if status_code < SUCCESS_STATUS_LIMIT:
            return

        block_text = (
            f"Rango {date_block[0]} -> {date_block[1]}, pagina {page_number}."
        )

        if status_code == FORBIDDEN_STATUS:
            raise ClockifyReportForbiddenError(
                f"HTTP 403: la API no tiene acceso al reporte. {block_text}",
                status_code=status_code,
            )

        reasons = {
            UNAUTHORIZED_STATUS: "La API key no fue autorizada.",
            RETRY_STATUS_TOO_MANY_REQUESTS: (
                "Clockify limito las solicitudes; reintenta mas tarde."
            ),
        }
        reason = reasons.get(status_code, "Clockify rechazo el reporte.")

        raise ClockifyRequestError(
            f"HTTP {status_code}: {reason} {block_text} No se guardaron "
            "datos parciales.",
            status_code=status_code,
        )

    def _read_json(self, response: requests.Response) -> Any:
        """Interpreta el cuerpo JSON de la respuesta."""
        self._raise_for_status(response, "consultar la API")

        try:
            return response.json()
        except ValueError as error:
            raise ClockifyRequestError(
                "Clockify no devolvio JSON valido.",
            ) from error


def build_report_payload(
    project_id: str,
    block_start: date,
    block_end: date,
    page_number: int,
    timezone_name: str,
) -> JsonObject:
    """
    Construye el cuerpo del reporte detallado.

    Args:
        project_id: ID del proyecto en Clockify.
        block_start: Primer dia del bloque.
        block_end: Ultimo dia del bloque.
        page_number: Pagina solicitada.
        timezone_name: Zona horaria del reporte.

    Returns:
        El cuerpo JSON de la peticion.
    """
    return {
        "dateRangeStart": f"{block_start.isoformat()}T00:00:00.000",
        "dateRangeEnd": f"{block_end.isoformat()}T23:59:59.999",
        "timeZone": timezone_name,
        "amountShown": "HIDE_AMOUNT",
        "dateRangeType": "ABSOLUTE",
        "projects": {"ids": [project_id], "contains": "CONTAINS"},
        "detailedFilter": {
            "page": page_number,
            "pageSize": REPORT_PAGE_SIZE,
            "sortColumn": "ID",
        },
        "sortOrder": "ASCENDING",
        "rounding": False,
        "exportType": "JSON",
    }


def read_report_entries(payload: Any) -> list[JsonObject]:
    """
    Extrae la lista timeentries del reporte.

    Args:
        payload: Respuesta JSON del reporte.

    Returns:
        Los registros de la pagina.

    Raises:
        ClockifyRequestError: Cuando falta timeentries; nunca se
            interpreta como cero horas.
    """
    if not isinstance(payload, dict) or not isinstance(
        payload.get("timeentries"),
        list,
    ):
        raise ClockifyRequestError(
            "Formato de reporte no reconocido: falta timeentries.",
        )

    entries: list[JsonObject] = payload["timeentries"]

    return entries


def store_report_entries(
    page_entries: list[JsonObject],
    project_id: str,
    entries_by_id: dict[str, JsonObject],
) -> None:
    """
    Valida y guarda los registros de una pagina sin duplicados.

    Args:
        page_entries: Registros de la pagina.
        project_id: Proyecto solicitado.
        entries_by_id: Registros acumulados por ID.

    Raises:
        ClockifyRequestError: Cuando un registro no tiene ID o es de
            otro proyecto.
    """
    for entry in page_entries:
        project = entry.get("project") or {}
        entry_project_id = entry.get("projectId") or project.get(
            "id",
            project.get("_id"),
        )

        if str(entry_project_id or "") != project_id:
            raise ClockifyRequestError(
                "El reporte contiene un ID de proyecto distinto al solicitado.",
            )

        entry_id = entry.get("_id") or entry.get("id")

        if not entry_id:
            raise ClockifyRequestError(
                "Registro sin ID en el reporte de Clockify.",
            )

        entries_by_id[str(entry_id)] = entry


def is_retryable_status(status_code: int) -> bool:
    """
    Indica si conviene reintentar una peticion.

    Args:
        status_code: Estatus HTTP recibido.

    Returns:
        True para 429 y errores 5xx.
    """
    return (
        status_code == RETRY_STATUS_TOO_MANY_REQUESTS
        or status_code >= SERVER_ERROR_STATUS
    )
