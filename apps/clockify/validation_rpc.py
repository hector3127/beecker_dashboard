"""Validacion de registros de Clockify expuesta al frontend por RPC."""

from collections.abc import Callable
from typing import Any

from apps.clockify.provider import build_clockify_loader
from apps.clockify.services import entry_validation as validation
from apps.daily.services.ixs_functions import fill_args
from apps.daily.services.ixs_store import run_safely
from core.rpc.registry import register_rpc
from core.sheets.factory import build_sheet_repository
from core.sheets.repository import GoogleSheetRepository

"""BKD.020.014 - RPC de validacion de Clockify
Registra obtenerRegistrosMalRegistrados, obtenerAreasReglas,
guardarAreaRegla, eliminarAreaRegla y limpiarValidacionesIAClockify con
los mismos nombres y respuestas que ClockifyService.gs.
"""

JsonObject = dict[str, Any]
Action = Callable[[GoogleSheetRepository, tuple[Any, ...]], JsonObject]


def bad_entries(
    repository: GoogleSheetRepository,
    project: object,
) -> JsonObject:
    """Registros sin tag o fuera de horario del proyecto."""
    loader = build_clockify_loader(repository)

    return validation.bad_entries(
        project,
        repository.read_as_objects(validation.RESOURCES_SHEET),
        loader.load_project_hours,
    )


def register(name: str, count: int, action: Action) -> None:
    """Registra una funcion; los errores regresan {"ok": False, "error"}."""

    def handler(*args: object) -> JsonObject:
        return run_safely(
            lambda: action(build_sheet_repository(), fill_args(args, count)),
        )

    handler.__name__ = name
    register_rpc(name)(handler)


FUNCTIONS: dict[str, tuple[int, Action]] = {
    "obtenerRegistrosMalRegistrados": (
        1,
        lambda repo, args: bad_entries(repo, args[0]),
    ),
    "obtenerAreasReglas": (
        0,
        lambda repo, args: validation.list_area_rules(repo, repo),
    ),
    "guardarAreaRegla": (
        2,
        lambda repo, args: validation.save_area_rule(repo, repo, *args),
    ),
    "eliminarAreaRegla": (
        1,
        lambda repo, args: validation.delete_area_rule(repo, repo, args[0]),
    ),
    "limpiarValidacionesIAClockify": (
        0,
        lambda repo, args: validation.clear_validations(repo, repo),
    ),
}

for _name, (_count, _action) in FUNCTIONS.items():
    register(_name, _count, _action)
