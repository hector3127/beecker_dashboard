"""Endpoint que reemplaza a google.script.run."""

import inspect
import logging
from typing import Final

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.exceptions import DashboardError, InvalidRequestError
from core.rpc.registry import RpcFunction, get_rpc_function

"""BKD.006.002 - Endpoint RPC
Recibe el nombre de la funcion y sus argumentos, ejecuta la funcion
registrada y responde con el mismo JSON que regresaba Apps Script.
"""

logger = logging.getLogger(__name__)

NOT_MIGRATED_CODE: Final[str] = "ERR_RPC_NOT_MIGRATED"

NOT_MIGRATED_STATUS: Final[int] = 404


class RpcView(APIView):
    """Ejecuta funciones registradas con register_rpc."""

    def post(self, request: Request, function_name: str) -> Response:
        """
        Ejecuta la funcion solicitada por el frontend.

        Args:
            request: Peticion con el cuerpo {"args": [...]}.
            function_name: Nombre de la funcion en Apps Script.

        Returns:
            {"ok": true, "result": ...} o {"ok": false, ...} con error.
        """
        rpc_function = get_rpc_function(function_name)

        if rpc_function is None:
            return build_error_response(
                code=NOT_MIGRATED_CODE,
                message=(
                    f"La funcion {function_name} todavia no se migra a Django."
                ),
                status=NOT_MIGRATED_STATUS,
            )

        try:
            args = parse_args(request.data)
            validate_arguments(rpc_function, args)
            result = rpc_function(*args)
        except DashboardError as error:
            logger.warning(
                "Falla controlada en %s. code=%s detail=%s",
                function_name,
                error.code,
                error.detail,
            )

            return build_error_response(
                code=error.code,
                message=error.build_message(),
                status=error.http_status,
            )

        return Response({"ok": True, "result": result})


def parse_args(payload: object) -> list[object]:
    """
    Extrae la lista de argumentos del cuerpo de la peticion.

    Args:
        payload: Cuerpo JSON ya interpretado.

    Returns:
        La lista de argumentos posicionales.

    Raises:
        InvalidRequestError: Cuando el cuerpo no tiene el formato.
    """
    if not isinstance(payload, dict):
        raise InvalidRequestError("El cuerpo debe ser un objeto JSON.")

    args = payload.get("args", [])

    if not isinstance(args, list):
        raise InvalidRequestError("El campo args debe ser una lista.")

    return args


def validate_arguments(rpc_function: RpcFunction, args: list[object]) -> None:
    """
    Verifica que la cantidad de argumentos coincida con la funcion.

    Args:
        rpc_function: Funcion que se va a ejecutar.
        args: Argumentos recibidos.

    Raises:
        InvalidRequestError: Cuando sobran o faltan argumentos.
    """
    try:
        inspect.signature(rpc_function).bind(*args)
    except TypeError as error:
        raise InvalidRequestError(
            f"Argumentos invalidos: {error}.",
        ) from error


def build_error_response(*, code: str, message: str, status: int) -> Response:
    """
    Construye la respuesta JSON de error.

    Args:
        code: Codigo de error para el frontend.
        message: Mensaje que se muestra al usuario.
        status: Estatus HTTP.

    Returns:
        La respuesta de DRF.
    """
    return Response(
        {
            "ok": False,
            "code": code,
            "message": message,
        },
        status=status,
    )
