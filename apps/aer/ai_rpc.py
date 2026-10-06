"""IA por proyecto AER/T&M expuesta al frontend por RPC."""

import uuid
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from apps.aer.services.ai_common import AerAiContext
from apps.aer.services.ai_functions import FUNCTIONS, Action
from apps.daily.services.ixs_drive import GoogleDriveFolders
from apps.daily.services.ixs_functions import fill_args
from apps.daily.services.ixs_store import run_safely
from core.integrations.claude_client import DEFAULT_MODEL, ClaudeClient
from core.rpc.registry import register_rpc
from core.sheets.client import build_drive_service
from core.sheets.factory import build_sheet_repository, get_credentials

"""BKD.080.014 - RPC de IA AER
Registra las 18 funciones de AERIAService.gs con los mismos nombres,
argumentos y respuestas.
"""

JsonObject = dict[str, Any]


def build_context(with_drive: bool) -> AerAiContext:
    """Hojas, Claude (.env), cache de Django y, si hace falta, Drive."""
    repository = build_sheet_repository()
    api_key = settings.ANTHROPIC_API_KEY
    drive = (
        GoogleDriveFolders(
            build_drive_service(
                get_credentials(settings.GOOGLE_CREDENTIALS_FILE),
            ),
        )
        if with_drive
        else None
    )

    return AerAiContext(
        reader=repository,
        writer=repository,
        now=timezone.now(),
        api_key=api_key,
        model=settings.CLAUDE_MODEL or DEFAULT_MODEL,
        build_client=lambda: ClaudeClient(api_key),
        cache=cache,
        new_uid=lambda: str(uuid.uuid4()),
        drive=drive,
    )


def register(name: str, count: int, action: Action, drive: bool) -> None:
    """Registra una funcion; los errores regresan {"ok": False, "error"}."""

    def handler(*args: object) -> JsonObject:
        return run_safely(
            lambda: action(build_context(drive), fill_args(args, count)),
        )

    handler.__name__ = name
    register_rpc(name)(handler)


for _name, (_count, _action, _drive) in FUNCTIONS.items():
    register(_name, _count, _action, _drive)
