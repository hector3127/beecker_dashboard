"""Llamadas REST a Azure DevOps que usa el panel Daily."""

import json
import random
import time
from collections.abc import Callable, Sequence
from typing import Any

import requests

from apps.azure_devops.services.azure_client import (
    build_basic_auth,
    encode_url_part,
)
from apps.daily.constants import (
    API_VERSION,
    AZURE_BASE_URL,
    COMMENTS_API_VERSION,
    REQUEST_TIMEOUT_SECONDS,
)
from apps.daily.exceptions import AzureConnectionError, AzureHttpError

"""BKD.070.005 - Cliente REST del Daily
Equivale a las llamadas UrlFetchApp de DailyPanelService.gs. Cada error
conserva el codigo HTTP y el cuerpo para armar los mismos mensajes.
"""

SUCCESS_LIMIT = 300
# Azure responde 203 con la pagina de inicio de sesion cuando el PAT no
# sirve; el original lo trataba como token invalido.
NON_AUTHORITATIVE_STATUS = 203

JsonObject = dict[str, Any]

# _ixsAzureLeerConReintentosV96_: solo lecturas (GET y WIQL), 4 intentos.
RETRY_DELAYS_SECONDS = (0.4, 1.0, 2.1)
RETRY_JITTER_SECONDS = 0.14
TRANSIENT_STATUSES = frozenset({408, 429, 500, 502, 503, 504})


class DailyAzureClient:
    """Cliente de una organizacion de Azure DevOps."""

    def __init__(
        self,
        organization: str,
        personal_access_token: str,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._organization = organization
        self._sleep = sleep
        self._session = session or requests.Session()
        self._session.headers.update(
            {"Authorization": build_basic_auth(personal_access_token)},
        )

    def organization_url(self) -> str:
        """URL base de la organizacion."""
        return f"{AZURE_BASE_URL}/{encode_url_part(self._organization)}"

    def project_url(self, project: str) -> str:
        """URL base de las APIs de work items del proyecto."""
        return (
            f"{self.organization_url()}/{encode_url_part(project)}/_apis/wit/"
        )

    def list_projects(self) -> list[JsonObject]:
        """
        Lista los Team Projects de la organizacion.

        Returns:
            Los proyectos con id y name.
        """
        payload = self.send(
            "GET",
            f"{self.organization_url()}/_apis/projects",
            params={"api-version": API_VERSION, "$top": 300},
        )
        projects: list[JsonObject] = payload.get("value") or []

        return projects

    def get_project(self, project: str) -> JsonObject:
        """
        Lee un Team Project.

        Args:
            project: Nombre del proyecto.

        Returns:
            El proyecto.
        """
        return self.send(
            "GET",
            f"{self.organization_url()}/_apis/projects/"
            f"{encode_url_part(project)}",
            params={"api-version": API_VERSION},
        )

    def run_wiql(self, project: str, query: str) -> list[int]:
        """
        Ejecuta una consulta WIQL.

        Args:
            project: Team Project.
            query: Consulta WIQL.

        Returns:
            Los IDs en el orden de la consulta.
        """
        payload = self.send(
            "POST",
            f"{self.project_url(project)}wiql",
            params={"api-version": API_VERSION},
            json={"query": query},
        )

        return [int(item["id"]) for item in payload.get("workItems") or []]

    def get_work_items(
        self,
        project: str,
        ids: Sequence[int],
        fields: Sequence[str] | None,
    ) -> list[JsonObject]:
        """
        Lee varios work items.

        Args:
            project: Team Project.
            ids: IDs a leer.
            fields: Campos; None trae todos ($expand=fields).

        Returns:
            Los work items.
        """
        params: dict[str, str] = {
            "ids": ",".join(str(item_id) for item_id in ids),
            "api-version": API_VERSION,
        }

        if fields is None:
            params["$expand"] = "fields"
        else:
            params["fields"] = ",".join(fields)

        payload = self.send(
            "GET",
            f"{self.project_url(project)}workitems",
            params=params,
        )
        work_items: list[JsonObject] = payload.get("value") or []

        return work_items

    def get_work_item(self, project: str, work_item_id: int) -> JsonObject:
        """
        Lee un work item con todos sus campos.

        Args:
            project: Team Project.
            work_item_id: ID del work item.

        Returns:
            El work item.
        """
        return self.send(
            "GET",
            f"{self.project_url(project)}workitems/{work_item_id}",
            params={"$expand": "fields", "api-version": API_VERSION},
        )

    def add_comment(
        self,
        project: str,
        work_item_id: str,
        text: str,
    ) -> JsonObject:
        """
        Publica un comentario en la discusion del work item.

        Args:
            project: Team Project.
            work_item_id: ID del work item.
            text: Texto del comentario.

        Returns:
            El comentario creado.
        """
        return self.send(
            "POST",
            f"{self.project_url(project)}workItems/{work_item_id}/comments",
            params={"api-version": COMMENTS_API_VERSION},
            json={"text": text},
        )

    def get_type_fields(self, project: str, work_item_type: str) -> JsonObject:
        """
        Definicion de campos de un tipo de work item con valores permitidos.

        Args:
            project: Team Project.
            work_item_type: Tipo (por ejemplo Risk).

        Returns:
            La respuesta con value.
        """
        return self.send(
            "GET",
            f"{self.project_url(project)}workitemtypes/"
            f"{encode_url_part(work_item_type)}/fields",
            params={"api-version": API_VERSION, "$expand": "allowedValues"},
        )

    def get_iteration_tree(self, project: str) -> JsonObject:
        """
        Arbol de iteraciones del proyecto (15 niveles).

        Args:
            project: Team Project.

        Returns:
            El nodo raiz.
        """
        return self.send(
            "GET",
            f"{self.project_url(project)}classificationnodes/iterations",
            params={"$depth": 15, "api-version": API_VERSION},
        )

    def create_work_item(
        self,
        project: str,
        work_item_type: str,
        operations: list[JsonObject],
    ) -> JsonObject:
        """
        Crea un work item con operaciones JSON Patch.

        Args:
            project: Team Project.
            work_item_type: Tipo (Risk).
            operations: Operaciones add de campos y relaciones.

        Returns:
            El work item creado.
        """
        return self.send(
            "POST",
            f"{self.project_url(project)}workitems/${work_item_type}",
            params={"api-version": API_VERSION},
            data=json.dumps(operations),
            headers={"Content-Type": "application/json-patch+json"},
        )

    def send(
        self,
        method: str,
        url: str,
        retry: bool = False,
        **kwargs: Any,
    ) -> JsonObject:
        """
        Envia la peticion y regresa el JSON.

        Args:
            method: Metodo HTTP.
            url: URL completa.
            retry: Reintenta fallos temporales (solo para lecturas).
            **kwargs: Parametros de requests.

        Returns:
            El JSON de la respuesta.

        Raises:
            AzureConnectionError: Cuando no hay conexion.
            AzureHttpError: Cuando el codigo es 300 o mayor.
        """
        attempts = len(RETRY_DELAYS_SECONDS) + 1 if retry else 1

        for attempt in range(attempts):
            is_last = attempt == attempts - 1

            try:
                response = self._session.request(
                    method,
                    url,
                    timeout=REQUEST_TIMEOUT_SECONDS,
                    **kwargs,
                )
            except requests.RequestException as error:
                if is_last or not isinstance(
                    error,
                    requests.ConnectionError | requests.Timeout,
                ):
                    raise AzureConnectionError(str(error)) from error

                self._pause(attempt)
                continue

            if response.status_code in TRANSIENT_STATUSES and not is_last:
                self._pause(attempt)
                continue

            return read_payload(response)

        raise AzureConnectionError(
            "La consulta Azure no respondió después de 4 intentos.",
        )

    def _pause(self, attempt: int) -> None:
        """Espera antes del siguiente intento."""
        self._sleep(
            RETRY_DELAYS_SECONDS[attempt]
            + random.uniform(0, RETRY_JITTER_SECONDS),  # noqa: S311
        )


def read_payload(response: requests.Response) -> JsonObject:
    """
    Valida el codigo y lee el JSON de la respuesta.

    Args:
        response: Respuesta de Azure.

    Returns:
        El JSON.

    Raises:
        AzureHttpError: Cuando el codigo es 300 o mayor (o 203).
        AzureConnectionError: Cuando el cuerpo no es JSON.
    """
    if (
        response.status_code >= SUCCESS_LIMIT
        or response.status_code == NON_AUTHORITATIVE_STATUS
    ):
        raise AzureHttpError(response.status_code, response.text)

    try:
        payload = response.json()
    except (ValueError, json.JSONDecodeError) as error:
        raise AzureConnectionError(
            "Azure DevOps no devolvio JSON valido.",
        ) from error

    return payload if isinstance(payload, dict) else {}
