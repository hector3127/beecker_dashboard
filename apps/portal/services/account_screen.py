"""Datos de una cuenta para su pantalla: proyectos, ROC, backlog y horas."""

from typing import Any

from apps.ejecutivo.account_rpc import (
    get_account_consumption,
    get_account_view,
)

"""BKD.120.022 - Cuenta
Entrega lo que la hoja de la cuenta ya calcula; los totales de lo que se ve en
pantalla (avance, consumo, estados, alertas) los suma el frontend porque las
horas de Clockify llegan por lotes despues de abrir la pagina.
"""

BATCH = 3  # proyectos MPB por consulta de horas


def load_account(client: str) -> dict[str, Any]:
    """Vista de la cuenta; ok=False con el motivo si no se pudo leer."""
    return get_account_view(client)


def load_consumption(
    client: str, offset: object, pending_ids: list[str] | None
) -> dict[str, Any]:
    """Horas de un lote de proyectos pendientes."""
    return get_account_consumption(client, offset, BATCH, pending_ids)
