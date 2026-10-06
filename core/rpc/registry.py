"""Registro de las funciones que el frontend invoca por nombre."""

from collections.abc import Callable
from typing import TypeVar

"""BKD.006.001 - Registro RPC
Cada app registra aqui las funciones que antes se llamaban con
google.script.run, usando el mismo nombre que tenian en Apps Script.
"""

RpcFunction = Callable[..., object]

RpcFunctionType = TypeVar("RpcFunctionType", bound=RpcFunction)

# Nombre de la funcion en Apps Script -> funcion de Python.
RPC_FUNCTIONS: dict[str, RpcFunction] = {}


class DuplicateRpcFunctionError(ValueError):
    """Indica que dos modulos registraron el mismo nombre de funcion."""


def register_rpc(
    legacy_name: str,
) -> Callable[[RpcFunctionType], RpcFunctionType]:
    """
    Registra una funcion con el nombre que usaba en Apps Script.

    Args:
        legacy_name: Nombre de la funcion en el codigo .gs original.

    Returns:
        El decorador que registra la funcion sin modificarla.

    Raises:
        DuplicateRpcFunctionError: Cuando el nombre ya esta registrado.
    """

    def decorator(rpc_function: RpcFunctionType) -> RpcFunctionType:
        if legacy_name in RPC_FUNCTIONS:
            raise DuplicateRpcFunctionError(
                f"La funcion RPC {legacy_name} ya esta registrada.",
            )

        RPC_FUNCTIONS[legacy_name] = rpc_function

        return rpc_function

    return decorator


def get_rpc_function(legacy_name: str) -> RpcFunction | None:
    """
    Busca una funcion registrada.

    Args:
        legacy_name: Nombre de la funcion en Apps Script.

    Returns:
        La funcion registrada, o None si aun no se migra.
    """
    return RPC_FUNCTIONS.get(legacy_name)
