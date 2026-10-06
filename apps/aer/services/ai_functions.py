"""Tabla de funciones de IA AER (nombre -> argumentos y accion)."""

from collections.abc import Callable
from typing import Any

from apps.aer.services import ai_claude, ai_minutes, ai_parts
from apps.aer.services.ai_common import AerAiContext

"""BKD.080.015 - Funciones de IA AER
Relaciona cada funcion de AERIAService.gs con su numero de argumentos,
la accion en Python y si necesita Google Drive.
"""

JsonObject = dict[str, Any]
Action = Callable[[AerAiContext, tuple[Any, ...]], JsonObject]


def claude_kind(kind: str) -> Action:
    """preguntar, correo o borrador de minuta sin forzar."""
    return lambda ctx, args: ai_claude.ask_claude(
        ctx,
        kind,
        args[0],
        args[1],
        args[2],
        False,
    )


FUNCTIONS: dict[str, tuple[int, Action, bool]] = {
    "analizarProyectoClaudeAER": (
        3,
        lambda ctx, args: ai_claude.analyze(ctx, *args),
        False,
    ),
    "obtenerUltimoAnalisisProyectoAER": (
        2,
        lambda ctx, args: ai_claude.last_analysis(ctx, *args),
        False,
    ),
    "obtenerUltimoResumenEjecutivoAER": (
        1,
        lambda ctx, args: ai_claude.last_summary(ctx, args[0]),
        False,
    ),
    "generarResumenEjecutivoClaudeAER": (
        3,
        lambda ctx, args: ai_claude.generate_summary(ctx, *args),
        True,
    ),
    "preguntarClaudeProyectoAER": (3, claude_kind("pregunta"), False),
    "redactarCorreoClaudeAER": (3, claude_kind("correo"), False),
    "generarBorradorMinutaClaudeAER": (3, claude_kind("minuta"), False),
    "listarMinutasIAProyectoAER": (
        1,
        lambda ctx, args: ai_minutes.list_minutes(ctx, args[0]),
        False,
    ),
    "guardarMinutaIAProyectoAER": (
        2,
        lambda ctx, args: ai_minutes.save_minute(ctx, *args),
        False,
    ),
    "obtenerConfigCarpetaMinutasAER": (
        1,
        lambda ctx, args: ai_minutes.get_config(ctx, args[0]),
        False,
    ),
    "obtenerPromptMinutaDefectoAER": (
        1,
        lambda ctx, args: ai_minutes.get_default_prompt(ctx, args[0]),
        False,
    ),
    "guardarConfigCarpetaMinutasAER": (
        2,
        lambda ctx, args: ai_minutes.save_config(ctx, *args),
        False,
    ),
    "buscarMinutasCarpetaAER": (
        1,
        lambda ctx, args: ai_minutes.search_folder(ctx, args[0]),
        True,
    ),
    "generarBorradorMinutaDesdeCarpetaClaudeAER": (
        3,
        lambda ctx, args: ai_minutes.draft_from_folder(ctx, *args),
        True,
    ),
    "listarAccionesPartesAER": (
        1,
        lambda ctx, args: ai_parts.list_parts(ctx, args[0]),
        False,
    ),
    "guardarAccionParteAER": (
        2,
        lambda ctx, args: ai_parts.save_part(ctx, *args),
        False,
    ),
    "actualizarCampoAccionParteAER": (
        4,
        lambda ctx, args: ai_parts.update_part(ctx, *args),
        False,
    ),
    "eliminarAccionParteAER": (
        2,
        lambda ctx, args: ai_parts.delete_part(ctx, *args),
        False,
    ),
}
