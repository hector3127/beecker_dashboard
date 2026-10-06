"""Cliente HTTP de la API REST de Azure DevOps."""

import base64
import logging
from typing import Any
from urllib.parse import quote

import requests

from apps.azure_devops.constants import (
    API_VERSION,
    AZURE_DEVOPS_BASE_URL,
    ITERATIONS_DEPTH,
    MAX_WORK_ITEMS,
    PROJECTS_PAGE_SIZE,
    REQUEST_TIMEOUT_SECONDS,
    SUCCESS_STATUS_LIMIT,
    WORK_ITEM_FIELDS,
    WORK_ITEMS_BATCH_SIZE,
)
from apps.azure_devops.exceptions import AzureDevOpsRequestError

"""BKD.030.003 - Cliente de Azure DevOps
Equivale a _altoNivelListarProyectosAzure() y
_altoNivelObtenerWorkItemsProyectoAzure() de ResumenAltoNivelService.gs.
"""

logger = logging.getLogger(__name__)

JsonObject = dict[str, Any]

URL_SAFE_CHARACTERS = "-_.!~*'()"


class AzureDevOpsClient:
    """Llamadas a la API REST de una organizacion de Azure DevOps."""

    def __init__(
        self,
        organization: str,
        personal_access_token: str,
        session: requests.Session | None = None,
    ) -> None:
        self._organization_url = (
            f"{AZURE_DEVOPS_BASE_URL}/{encode_url_part(organization)}"
        )
        self._session = session or requests.Session()
        self._session.headers.update(
            {"Authorization": build_basic_auth(personal_access_token)},
        )

    def list_project_names(self) -> list[str]:
        """
        Lista los Team Projects de la organizacion.

        Returns:
            Los nombres de los proyectos.

        Raises:
            AzureDevOpsRequestError: Cuando Azure responde con error.
        """
        payload = self._send(
            "GET",
            f"{self._organization_url}/_apis/projects",
            params={"api-version": API_VERSION, "$top": PROJECTS_PAGE_SIZE},
        )

        return [
            str(project.get("name", ""))
            for project in payload.get("value", [])
            if project.get("name")
        ]

    def list_work_items(self, project_name: str) -> list[JsonObject]:
        """
        Lee hasta 1000 work items del proyecto, los mas recientes primero.

        Args:
            project_name: Nombre del Team Project.

        Returns:
            Los work items con los campos que usa el dashboard.

        Raises:
            AzureDevOpsRequestError: Cuando falla la consulta WIQL.
        """
        project_url = (
            f"{self._organization_url}/{encode_url_part(project_name)}"
        )
        escaped_name = project_name.replace("'", "''")
        wiql_payload = self._send(
            "POST",
            f"{project_url}/_apis/wit/wiql",
            params={"api-version": API_VERSION},
            json={
                "query": (
                    "SELECT [System.Id] FROM WorkItems WHERE "
                    f"[System.TeamProject] = '{escaped_name}' "
                    "ORDER BY [System.ChangedDate] DESC"
                ),
            },
        )
        work_item_ids = [
            work_item["id"]
            for work_item in wiql_payload.get("workItems", [])
            if "id" in work_item
        ][:MAX_WORK_ITEMS]

        work_items: list[JsonObject] = []

        for batch_start in range(0, len(work_item_ids), WORK_ITEMS_BATCH_SIZE):
            batch_end = batch_start + WORK_ITEMS_BATCH_SIZE
            batch_ids = work_item_ids[batch_start:batch_end]
            work_items.extend(
                self._read_work_item_batch(project_url, batch_ids)
            )

        return work_items

    def list_raid_items(self, project_name: str) -> list[JsonObject]:
        """
        Riesgos y oportunidades Active/Proposed con todos sus campos.

        Equivale a la consulta de obtenerRaidProyectoEjecutivoAzure():
        WIQL por tipo y estado, y detalle con $expand=fields en lotes de
        180; un lote fallido se omite.

        Args:
            project_name: Nombre del Team Project.

        Returns:
            Los work items, los cambiados mas recientemente primero.
        """
        project_url = (
            f"{self._organization_url}/{encode_url_part(project_name)}"
        )
        escaped_name = project_name.replace("'", "''")
        wiql_payload = self._send(
            "POST",
            f"{project_url}/_apis/wit/wiql",
            params={"api-version": API_VERSION},
            json={
                "query": (
                    "SELECT [System.Id] FROM WorkItems WHERE "
                    f"[System.TeamProject] = '{escaped_name}' "
                    "AND [System.WorkItemType] IN ('Risk','Opportunity') "
                    "AND [System.State] IN ('Active','Proposed') "
                    "ORDER BY [System.ChangedDate] DESC"
                ),
            },
        )
        work_item_ids = [
            work_item["id"]
            for work_item in wiql_payload.get("workItems", [])
            if "id" in work_item
        ]
        work_items: list[JsonObject] = []

        for batch_start in range(0, len(work_item_ids), WORK_ITEMS_BATCH_SIZE):
            batch_ids = work_item_ids[
                batch_start : batch_start + WORK_ITEMS_BATCH_SIZE
            ]

            try:
                payload = self._send(
                    "GET",
                    f"{project_url}/_apis/wit/workitems",
                    params={
                        "ids": ",".join(str(item_id) for item_id in batch_ids),
                        "$expand": "fields",
                        "api-version": API_VERSION,
                    },
                )
            except AzureDevOpsRequestError as error:
                logger.warning("Lote RAID omitido: %s", error.detail)
                continue

            work_items.extend(payload.get("value", []))

        return work_items

    def list_risk_fields(self, project_name: str) -> list[JsonObject]:
        """
        Campos del tipo Risk del proceso del proyecto.

        Args:
            project_name: Nombre del Team Project.

        Returns:
            Campos con name y referenceName.
        """
        project_url = (
            f"{self._organization_url}/{encode_url_part(project_name)}"
        )
        payload = self._send(
            "GET",
            f"{project_url}/_apis/wit/workitemtypes/Risk/fields",
            params={"api-version": API_VERSION},
        )
        fields: list[JsonObject] = payload.get("value", [])

        return fields

    def list_iterations(self, project_name: str) -> list[JsonObject]:
        """
        Lee el arbol de iteraciones del proyecto como lista plana.

        Equivale a _altoNivelObtenerIteracionesAzure().

        Args:
            project_name: Nombre del Team Project.

        Returns:
            Iteraciones con nombre, path, fechaInicio y fechaFin.
        """
        project_url = (
            f"{self._organization_url}/{encode_url_part(project_name)}"
        )
        root_node = self._send(
            "GET",
            f"{project_url}/_apis/wit/classificationnodes/iterations",
            params={"$depth": ITERATIONS_DEPTH, "api-version": API_VERSION},
        )
        iterations: list[JsonObject] = []
        flatten_iterations(root_node, "", iterations)

        return iterations

    def _read_work_item_batch(
        self,
        project_url: str,
        batch_ids: list[int],
    ) -> list[JsonObject]:
        """Lee un lote de work items; un lote fallido se registra y omite."""
        try:
            payload = self._send(
                "GET",
                f"{project_url}/_apis/wit/workitems",
                params={
                    "ids": ",".join(str(item_id) for item_id in batch_ids),
                    "fields": ",".join(WORK_ITEM_FIELDS),
                    "api-version": API_VERSION,
                },
            )
        except AzureDevOpsRequestError as error:
            # El original omitia el lote fallido y seguia con los demas.
            logger.warning("Lote de work items omitido: %s", error.detail)
            return []

        batch_items: list[JsonObject] = payload.get("value", [])

        return batch_items

    def _send(self, method: str, url: str, **kwargs: Any) -> JsonObject:
        """
        Envia una peticion y regresa el JSON de la respuesta.

        Raises:
            AzureDevOpsRequestError: Cuando no hay conexion, el estatus
                no es exitoso o el cuerpo no es JSON.
        """
        try:
            response = self._session.request(
                method,
                url,
                timeout=REQUEST_TIMEOUT_SECONDS,
                **kwargs,
            )
        except requests.RequestException as error:
            raise AzureDevOpsRequestError(
                "No hubo conexion con Azure DevOps.",
            ) from error

        if response.status_code >= SUCCESS_STATUS_LIMIT:
            raise AzureDevOpsRequestError(
                f"Azure DevOps respondio {response.status_code}. Revisa la "
                "organizacion y que el PAT tenga permiso de lectura.",
            )

        try:
            payload = response.json()
        except ValueError as error:
            raise AzureDevOpsRequestError(
                "Azure DevOps no devolvio JSON valido.",
            ) from error

        if not isinstance(payload, dict):
            raise AzureDevOpsRequestError(
                "Azure DevOps devolvio una respuesta inesperada.",
            )

        return payload


def flatten_iterations(
    node: JsonObject,
    parent_path: str,
    iterations: list[JsonObject],
) -> None:
    """
    Recorre el arbol de iteraciones y agrega cada nodo a la lista.

    Args:
        node: Nodo de iteracion de Azure.
        parent_path: Ruta del nodo padre.
        iterations: Lista donde se agregan las iteraciones.
    """
    node_name = str(node.get("name") or "")
    path = f"{parent_path}\\{node_name}" if parent_path else node_name
    attributes = node.get("attributes") or {}
    iterations.append(
        {
            "nombre": node_name,
            "path": path,
            "fechaInicio": attributes.get("startDate"),
            "fechaFin": attributes.get("finishDate"),
        },
    )

    for child_node in node.get("children") or []:
        flatten_iterations(child_node, path, iterations)


def build_basic_auth(personal_access_token: str) -> str:
    """
    Construye el encabezado Basic con el PAT, como _headerAuthAzureDevOps().

    Args:
        personal_access_token: PAT de Azure DevOps.

    Returns:
        El valor del encabezado Authorization.
    """
    token = base64.b64encode(f":{personal_access_token}".encode()).decode()

    return f"Basic {token}"


def encode_url_part(text: str) -> str:
    """
    Codifica un segmento de URL como encodeURIComponent().

    Args:
        text: Texto a codificar.

    Returns:
        El texto codificado.
    """
    return quote(text, safe=URL_SAFE_CHARACTERS)
