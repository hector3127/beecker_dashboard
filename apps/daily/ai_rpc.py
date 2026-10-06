"""Funciones de Claude e IA de la vista IXS expuestas por RPC."""

from collections.abc import Callable
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from apps.daily.services import claude_assist, ixs_ai, ixs_drive
from apps.daily.services.claude_assist import ClaudeSettings
from apps.daily.services.ixs_drive import DriveContext, GoogleDriveFolders
from apps.daily.services.ixs_functions import fill_args
from apps.daily.services.ixs_store import IxsStore, run_safely
from core.integrations.claude_client import DEFAULT_MODEL, ClaudeClient
from core.rpc.registry import register_rpc
from core.sheets.client import build_drive_service
from core.sheets.factory import build_sheet_repository, get_credentials

"""BKD.070.024 - RPC de Claude e IA IXS
Registra las funciones de configuracion y sugerencias de Claude y las
ixsIA* con los mismos nombres y respuestas que DailyPanelService.gs.
"""

JsonObject = dict[str, Any]


def build_claude() -> ClaudeSettings:
    """API key y modelo del .env, prompts en la cache de Django."""
    api_key = settings.ANTHROPIC_API_KEY

    return ClaudeSettings(
        api_key=api_key,
        model=settings.CLAUDE_MODEL or DEFAULT_MODEL,
        store=cache,
        build_client=lambda: ClaudeClient(api_key),
        now=timezone.now(),
    )


def build_ixs_store() -> IxsStore:
    """Hojas de la vista IXS con la hora actual."""
    repository = build_sheet_repository()

    return IxsStore(reader=repository, writer=repository, now=timezone.now())


def build_drive_context() -> DriveContext:
    """Hojas y Drive con la cuenta de servicio."""
    return DriveContext(
        store=build_ixs_store(),
        drive=GoogleDriveFolders(
            build_drive_service(
                get_credentials(settings.GOOGLE_CREDENTIALS_FILE),
            ),
        ),
    )


def register(
    name: str,
    count: int,
    action: Callable[[tuple[Any, ...]], JsonObject],
) -> None:
    """
    Registra una funcion con count argumentos de google.script.run.

    Los que faltan llegan como None y los que sobran se ignoran.
    """

    def handler(*args: object) -> JsonObject:
        return run_safely(lambda: action(fill_args(args, count)))

    handler.__name__ = name
    register_rpc(name)(handler)


register(
    "guardarApiKeyClaude",
    1,
    lambda args: claude_assist.save_api_key(args[0]),
)
register(
    "guardarPromptPersonalizadoClaude",
    1,
    lambda args: claude_assist.save_custom_prompt(build_claude(), args[0]),
)
register(
    "obtenerConfigClaude",
    0,
    lambda args: claude_assist.read_config(build_claude()),
)
register(
    "generarSugerenciaRiesgoConClaude",
    1,
    lambda args: claude_assist.suggest_risk(build_claude(), args[0]),
)
register(
    "ixsRaidGuardarPrompt",
    2,
    lambda args: claude_assist.save_raid_prompt(build_claude(), *args),
)
register(
    "ixsRaidObtenerPrompt",
    1,
    lambda args: claude_assist.read_raid_prompt(build_claude(), args[0]),
)
register(
    "ixsRaidSugerirClaude",
    2,
    lambda args: claude_assist.suggest_raid(build_claude(), *args),
)
register(
    "ixsIAAnalizar",
    3,
    lambda args: ixs_ai.analyze_project(
        build_claude(), build_ixs_store(), args
    ),
)
register(
    "ixsIAPreguntar",
    3,
    lambda args: ixs_ai.ask_question(build_claude(), args),
)
register(
    "ixsIAAnalisisLeer",
    1,
    lambda args: ixs_ai.read_analysis(build_ixs_store(), args[0]),
)
register(
    "ixsIAMemoriaLeer",
    1,
    lambda args: ixs_ai.read_memory(build_ixs_store(), args[0]),
)
register(
    "ixsIAMemoriaActualizar",
    3,
    lambda args: ixs_ai.save_memory(build_ixs_store(), *args),
)
register(
    "ixsIAMinutasLeer",
    1,
    lambda args: ixs_ai.read_minutes(build_ixs_store(), args[0]),
)
register(
    "ixsIAMinutaGuardar",
    4,
    lambda args: ixs_ai.save_minute(build_ixs_store(), args),
)
register(
    "ixsIADriveConfigLeer",
    1,
    lambda args: ixs_drive.read_config(build_ixs_store(), args[0]),
)
register(
    "ixsIADriveConfigGuardar",
    3,
    lambda args: ixs_drive.save_folder(build_drive_context(), *args),
)
register(
    "ixsIADriveConfigQuitar",
    3,
    lambda args: ixs_drive.remove_folder(build_ixs_store(), *args),
)
register(
    "ixsIADriveListar",
    1,
    lambda args: ixs_drive.list_files(build_drive_context(), args[0]),
)
register(
    "ixsIADriveLeerDocumento",
    2,
    lambda args: ixs_drive.read_document(build_drive_context(), *args),
)
register(
    "ixsIADriveGenerarMinuta",
    5,
    lambda args: ixs_drive.generate_minute(
        build_claude(),
        build_drive_context(),
        args,
    ),
)
