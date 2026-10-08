"""Busca los hilos de proyecto en el Gmail del usuario."""

import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from email.utils import getaddresses
from typing import Any, Protocol

from apps.gmail.constants import (
    MAX_MATCHING_THREADS,
    MAX_THREADS,
    THREAD_SUBJECT_TERM,
    THREAD_WORKERS,
)
from apps.gmail.services.reply_builder import (
    compute_reply_all,
    headers_of,
    last_message,
)

"""BKD.110.007 - Selector de hilos
Detecta los hilos "Inicio de ..." (proyecto, agente, T&M, etc.) y los
resume para que el usuario elija en cual responder. Los que coinciden con el nombre del
proyecto abierto se marcan como sugeridos.
"""

JsonObject = dict[str, Any]

PREFIX_PATTERN = re.compile(r"^\s*(re|rv|fw|fwd)\s*:\s*", re.IGNORECASE)

SNIPPET_LENGTH = 140


class ThreadSource(Protocol):
    """Lo que se necesita de GmailApi para buscar hilos."""

    def search_thread_ids(self, query: str, limit: int) -> list[str]:
        """Busca IDs de hilos."""
        ...

    def get_thread(self, thread_id: str) -> JsonObject:
        """Lee un hilo."""
        ...


def normalize_text(text: str) -> str:
    """
    Pasa a minusculas, quita acentos y deja solo letras y numeros.

    Args:
        text: Texto original.

    Returns:
        El texto comparable, con una sola separacion entre palabras.
    """
    decomposed = unicodedata.normalize("NFD", text)
    plain = "".join(c for c in decomposed if not unicodedata.combining(c))

    return " ".join(re.sub(r"[^a-z0-9]+", " ", plain.lower()).split())


def strip_reply_prefixes(subject: str) -> str:
    """
    Quita los Re:, RV: o Fwd: del inicio del asunto.

    Args:
        subject: Asunto del hilo.

    Returns:
        El asunto sin prefijos de respuesta.
    """
    clean = subject.strip()

    while PREFIX_PATTERN.match(clean):
        clean = PREFIX_PATTERN.sub("", clean, count=1)

    return clean.strip()


def project_name_from_subject(subject: str) -> str:
    """
    Saca el nombre del proyecto de "Inicio de <tipo>: <nombre>".

    Acepta "Inicio de proyecto: X", "Inicio de agente: X" e
    "Inicio de T&M | X"; el separador puede ser dos puntos, barra
    vertical o guion con espacios.

    Args:
        subject: Asunto del hilo.

    Returns:
        El nombre, o el asunto limpio si no sigue ese formato.
    """
    clean = strip_reply_prefixes(subject)
    match = re.match(
        rf"^{re.escape(THREAD_SUBJECT_TERM)}\s+[^:|]*?(?::|\||\s-\s)\s*(.*)$",
        clean,
        re.IGNORECASE,
    )

    if match:
        return match.group(1).strip()

    plain = re.match(
        rf"^{re.escape(THREAD_SUBJECT_TERM)}\s+(.*)$",
        clean,
        re.IGNORECASE,
    )

    return plain.group(1).strip() if plain else clean


def is_project_thread(subject: str) -> bool:
    """
    Indica si el asunto es de un hilo de inicio ("Inicio de ...").

    Args:
        subject: Asunto del hilo, con o sin Re:.

    Returns:
        True cuando el asunto empieza con "Inicio de".
    """
    clean = normalize_text(strip_reply_prefixes(subject))
    term = normalize_text(THREAD_SUBJECT_TERM)

    return clean.startswith(term + " ")


def build_queries(project_name: str, free_text: str) -> list[tuple[str, int]]:
    """
    Arma las busquedas de Gmail y cuantos hilos pedir en cada una.

    Args:
        project_name: Nombre del proyecto abierto; puede ir vacio.
        free_text: Texto que escribio el usuario para filtrar.

    Returns:
        Pares de busqueda y limite; primero las mas especificas.
    """
    base = f'subject:"{THREAD_SUBJECT_TERM}"'
    queries: list[tuple[str, int]] = []
    name = project_name.replace('"', " ").strip()
    text = free_text.replace('"', " ").strip()

    if name:
        queries.append((f'{base} subject:"{name}"', MAX_MATCHING_THREADS))

    queries.append((f"{base} {text}".strip(), MAX_THREADS))

    return queries


def find_threads(
    source: ThreadSource,
    project_name: str,
    free_text: str,
    my_email: str,
    remembered_id: str = "",
) -> list[JsonObject]:
    """
    Detecta los hilos de proyecto y los resume.

    Args:
        source: Cliente de Gmail.
        project_name: Nombre del proyecto abierto.
        free_text: Filtro escrito por el usuario.
        my_email: Correo de quien inicio sesion.
        remembered_id: Hilo elegido antes para este proyecto.

    Returns:
        Un resumen por hilo, sugeridos primero y luego por fecha.
    """
    ids: list[str] = []

    for query, limit in build_queries(project_name, free_text):
        for thread_id in source.search_thread_ids(query, limit):
            if thread_id not in ids:
                ids.append(thread_id)

    with ThreadPoolExecutor(max_workers=THREAD_WORKERS) as pool:
        threads = list(pool.map(source.get_thread, ids[:MAX_THREADS]))

    wanted = normalize_text(project_name)
    summaries = [
        summarize_thread(thread, my_email, wanted, remembered_id)
        for thread in threads
    ]
    valid = [item for item in summaries if item["subject"]]

    return sorted(
        valid,
        key=lambda item: (
            not item["remembered"],
            not item["suggested"],
            -int(item["lastTimestamp"]),
        ),
    )


def summarize_thread(
    thread: JsonObject,
    my_email: str,
    wanted_name: str,
    remembered_id: str,
) -> JsonObject:
    """
    Resume un hilo para mostrarlo en el selector.

    Args:
        thread: Hilo leido con format=metadata.
        my_email: Correo de quien inicio sesion.
        wanted_name: Nombre del proyecto ya normalizado.
        remembered_id: Hilo elegido antes para este proyecto.

    Returns:
        Asunto, ultimo mensaje, participantes y destinatarios de la
        respuesta a todos.
    """
    message = last_message(thread)

    if message is None:
        return {"subject": ""}

    headers = headers_of(message)
    subject = headers.get("subject", "")
    to_list, cc_list = compute_reply_all(headers, my_email)
    timestamp = _timestamp_ms(message)
    thread_id = str(thread.get("id", ""))
    name = normalize_text(subject)

    return {
        "id": thread_id,
        "subject": subject,
        "projectName": project_name_from_subject(subject),
        "suggested": bool(wanted_name) and wanted_name in name,
        "remembered": bool(remembered_id) and remembered_id == thread_id,
        "messageCount": len(_messages(thread)),
        "participants": _participants(thread),
        "lastFrom": headers.get("from", ""),
        "lastDate": _iso(timestamp),
        "lastTimestamp": timestamp,
        "snippet": str(message.get("snippet", ""))[:SNIPPET_LENGTH],
        "replyTo": to_list,
        "replyCc": cc_list,
    }


def _messages(thread: JsonObject) -> list[JsonObject]:
    """Mensajes del hilo."""
    messages = thread.get("messages")

    if not isinstance(messages, list):
        return []

    return [item for item in messages if isinstance(item, dict)]


def _participants(thread: JsonObject) -> int:
    """Cuenta las direcciones distintas que escribieron o recibieron."""
    addresses: set[str] = set()

    for message in _messages(thread):
        headers = headers_of(message)

        for name in ("from", "to", "cc", "reply-to"):
            # getaddresses falla con valores vacios dentro de una lista.
            value = headers.get(name, "")

            for _, address in getaddresses([value] if value else []):
                if address:
                    addresses.add(address.lower())

    return len(addresses)


def _timestamp_ms(message: JsonObject) -> int:
    """Fecha del mensaje en milisegundos."""
    try:
        return int(str(message.get("internalDate", "0")))
    except ValueError:
        return 0


def _iso(timestamp_ms: int) -> str:
    """Fecha ISO en UTC, o vacia si no hay."""
    if timestamp_ms <= 0:
        return ""

    return datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC).isoformat()
