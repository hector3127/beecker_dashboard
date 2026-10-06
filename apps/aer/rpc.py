"""Funciones del dashboard AER / T&M expuestas al frontend por RPC."""

from collections.abc import Callable
from typing import Any

from django.utils import timezone

from apps.aer.services import dashboard, people_client, plan, risks_actions
from apps.aer.services.manual_store import AerStore
from apps.clockify.provider import build_clockify_loader
from apps.daily.services.ixs_functions import fill_args
from apps.daily.services.ixs_store import run_safely
from core.rpc.registry import register_rpc
from core.sheets.factory import build_sheet_repository

"""BKD.080.009 - RPC AER
Registra las funciones de AERTYMProyectoService.gs con los mismos
nombres, argumentos y respuestas.
"""

JsonObject = dict[str, Any]
Action = Callable[[AerStore, tuple[Any, ...]], JsonObject]


def build_store() -> AerStore:
    """Hojas AER con la hora actual."""
    repository = build_sheet_repository()

    return AerStore(reader=repository, writer=repository, now=timezone.now())


def build_hours(store: AerStore) -> dashboard.HoursLoader:
    """Horas de Clockify del proyecto en su rango (MPB)."""

    def load(project: str) -> Any:
        return build_clockify_loader(store.reader).load_project_hours(project)

    return dashboard.safe_hours(load)


def register(name: str, count: int, action: Action) -> None:
    """Registra una funcion; los errores regresan {"ok": False, "error"}."""

    def handler(*args: object) -> JsonObject:
        return run_safely(lambda: action(build_store(), fill_args(args, count)))

    handler.__name__ = name
    register_rpc(name)(handler)


FUNCTIONS: dict[str, tuple[int, Action]] = {
    "getDashboardAERTYMProyecto": (
        1,
        lambda store, args: dashboard.build_dashboard(
            store,
            args[0],
            build_hours(store),
        ),
    ),
    "getRegistrosClockifyAERRango": (
        3,
        lambda store, args: dashboard.entries_in_range(
            args[0],
            (args[1], args[2]),
            build_hours(store),
        ),
    ),
    "guardarPlaneacionAER": (
        1,
        lambda store, args: plan.save_plan(store, args[0]),
    ),
    "guardarLotePlaneacionAER": (
        2,
        lambda store, args: plan.save_plan_batch(store, *args),
    ),
    "actualizarEsfuerzoPlaneacionAER": (
        3,
        lambda store, args: plan.update_effort(store, *args),
    ),
    "actualizarEstadoCierrePlaneacionAER": (
        4,
        lambda store, args: plan.update_close_state(store, args),
    ),
    "marcarCierrePlaneacionAER": (
        3,
        lambda store, args: plan.mark_closed(store, *args),
    ),
    "eliminarPlaneacionAER": (
        1,
        lambda store, args: plan.delete_plan(store, args[0]),
    ),
    "eliminarLotePlaneacionAER": (
        2,
        lambda store, args: plan.delete_plan_batch(store, *args),
    ),
    "guardarRiesgoAER": (
        1,
        lambda store, args: risks_actions.save_risk(store, args[0]),
    ),
    "getRiesgosAERProyecto": (
        1,
        lambda store, args: risks_actions.get_risks(store, args[0]),
    ),
    "limpiarDuplicadosRiesgosAER": (
        1,
        lambda store, args: risks_actions.clean_risks(store, args[0]),
    ),
    "eliminarRiesgoAER": (
        1,
        lambda store, args: risks_actions.delete_risk(store, args[0]),
    ),
    "guardarAccionAER": (
        1,
        lambda store, args: risks_actions.save_action(store, args[0]),
    ),
    "actualizarCampoAccionAER": (
        4,
        lambda store, args: risks_actions.update_action_field(store, args),
    ),
    "getAccionesAERProyecto": (
        1,
        lambda store, args: risks_actions.get_actions(store, args[0]),
    ),
    "limpiarDuplicadosAccionesAER": (
        1,
        lambda store, args: risks_actions.clean_actions(store, args[0]),
    ),
    "eliminarAccionAER": (
        1,
        lambda store, args: risks_actions.delete_action(store, args[0]),
    ),
    "guardarVacacionAER": (
        1,
        lambda store, args: people_client.save_vacation(store, args[0]),
    ),
    "eliminarVacacionAER": (
        2,
        lambda store, args: people_client.delete_vacation(store, *args),
    ),
    "guardarEvaluacionAER": (
        1,
        lambda store, args: people_client.save_evaluation(store, args[0]),
    ),
    "eliminarEvaluacionAER": (
        2,
        lambda store, args: people_client.delete_evaluation(store, *args),
    ),
    "guardarContactoAER": (
        1,
        lambda store, args: people_client.save_contact(store, args[0]),
    ),
    "eliminarContactoAER": (
        2,
        lambda store, args: people_client.delete_contact(store, *args),
    ),
    "guardarClienteInfoAER": (
        1,
        lambda store, args: people_client.save_client_info(store, args[0]),
    ),
    "guardarGobiernoClienteAER": (
        2,
        lambda store, args: people_client.save_governance(store, *args),
    ),
    "guardarDocumentoClienteAER": (
        1,
        lambda store, args: people_client.save_document(store, args[0]),
    ),
    "eliminarDocumentoClienteAER": (
        2,
        lambda store, args: people_client.delete_document(store, *args),
    ),
}

for _name, (_count, _action) in FUNCTIONS.items():
    register(_name, _count, _action)
