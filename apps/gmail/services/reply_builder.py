"""Destinatarios y mensaje MIME de una respuesta a todos."""

import base64
import mimetypes
import re
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr, getaddresses
from typing import Any

"""BKD.110.008 - Responder a todos
Calcula a quien va la respuesta igual que el boton "Responder a todos"
de Gmail y arma el mensaje con los encabezados que mantienen el hilo.
"""

JsonObject = dict[str, Any]

REPLY_PREFIX = re.compile(r"^\s*(re|rv)\s*:", re.IGNORECASE)


@dataclass(frozen=True)
class Attachment:
    """Archivo que se adjunta al correo."""

    filename: str
    content: bytes


def last_message(thread: JsonObject) -> JsonObject | None:
    """
    Busca el mensaje mas reciente de un hilo.

    Args:
        thread: Hilo de Gmail con sus mensajes.

    Returns:
        El mensaje con la fecha interna mas alta, o None si no hay.
    """
    messages = thread.get("messages")

    if not isinstance(messages, list):
        return None

    valid = [item for item in messages if isinstance(item, dict)]

    if not valid:
        return None

    return max(valid, key=_internal_date)


def headers_of(message: JsonObject) -> dict[str, str]:
    """
    Pasa los encabezados de un mensaje a un diccionario en minusculas.

    Args:
        message: Mensaje leido con format=metadata.

    Returns:
        Nombre del encabezado en minusculas y su valor.
    """
    payload = message.get("payload")
    headers = payload.get("headers") if isinstance(payload, dict) else None
    result: dict[str, str] = {}

    if not isinstance(headers, list):
        return result

    for header in headers:
        if isinstance(header, dict) and header.get("name"):
            result.setdefault(
                str(header["name"]).lower(),
                str(header.get("value", "")).strip(),
            )

    return result


def compute_reply_all(
    headers: dict[str, str],
    my_email: str,
) -> tuple[list[str], list[str]]:
    """
    Calcula Para y Cc de "Responder a todos" sobre un mensaje.

    Si el ultimo mensaje es del propio usuario, se conserva su Para y su
    Cc; si no, se contesta a quien lo escribio (o a su Reply-To) y los
    demas pasan a Cc. El usuario nunca se incluye.

    Args:
        headers: Encabezados del ultimo mensaje, en minusculas.
        my_email: Correo de quien responde.

    Returns:
        Las listas Para y Cc, sin repetidos y con el nombre visible.
    """
    me = my_email.strip().lower()
    sender = _addresses(headers.get("from", ""))
    reply_to = _addresses(headers.get("reply-to", "")) or sender
    original_to = _addresses(headers.get("to", ""))
    original_cc = _addresses(headers.get("cc", ""))
    sent_by_me = any(address.lower() == me for _, address in sender)

    if sent_by_me:
        primary, secondary = original_to, original_cc
    else:
        primary, secondary = reply_to, original_to + original_cc

    to_list = _unique(primary, me, set())
    taken = {address.lower() for _, address in to_list}
    cc_list = _unique(secondary, me, taken)

    return (
        [formataddr(pair) for pair in to_list],
        [formataddr(pair) for pair in cc_list],
    )


def reply_subject(subject: str) -> str:
    """
    Pone "Re:" al asunto si todavia no lo tiene.

    Args:
        subject: Asunto del ultimo mensaje.

    Returns:
        El asunto de la respuesta.
    """
    clean = subject.strip()

    return clean if REPLY_PREFIX.match(clean) else f"Re: {clean}"


def build_references(headers: dict[str, str]) -> tuple[str, str]:
    """
    Arma In-Reply-To y References para que Gmail una el hilo.

    Args:
        headers: Encabezados del ultimo mensaje, en minusculas.

    Returns:
        El In-Reply-To y el References de la respuesta.
    """
    message_id = headers.get("message-id", "").strip()
    previous = headers.get("references", "").strip()
    references = " ".join(part for part in (previous, message_id) if part)

    return message_id, references


def build_raw_message(
    sender: str,
    to_list: list[str],
    cc_list: list[str],
    subject: str,
    reply_headers: tuple[str, str],
    bodies: tuple[str, str],
    attachments: list[Attachment],
) -> str:
    """
    Arma el correo MIME y lo codifica como pide la API de Gmail.

    Args:
        sender: Correo de quien responde.
        to_list: Direcciones del Para.
        cc_list: Direcciones del Cc.
        subject: Asunto de la respuesta.
        reply_headers: In-Reply-To y References.
        bodies: Texto plano y HTML del comunicado.
        attachments: Archivos de soporte.

    Returns:
        El mensaje en base64 url-safe.
    """
    message = EmailMessage()
    message["From"] = sender
    message["To"] = ", ".join(to_list)

    if cc_list:
        message["Cc"] = ", ".join(cc_list)

    message["Subject"] = subject
    in_reply_to, references = reply_headers

    if in_reply_to:
        message["In-Reply-To"] = in_reply_to

    if references:
        message["References"] = references

    text, html = bodies
    message.set_content(text)
    message.add_alternative(html, subtype="html")

    for attachment in attachments:
        content_type = (
            mimetypes.guess_type(attachment.filename)[0]
            or "application/octet-stream"
        )
        maintype, _, subtype = content_type.partition("/")
        message.add_attachment(
            attachment.content,
            maintype=maintype,
            subtype=subtype,
            filename=attachment.filename,
        )

    return base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")


def _addresses(value: str) -> list[tuple[str, str]]:
    """Separa un encabezado de direcciones en pares nombre y correo."""
    return [
        (name, address)
        for name, address in getaddresses([value])
        if address and "@" in address
    ]


def _unique(
    pairs: list[tuple[str, str]],
    my_email: str,
    skip: set[str],
) -> list[tuple[str, str]]:
    """Quita repetidos, al usuario y las direcciones ya tomadas."""
    seen = set(skip)
    result: list[tuple[str, str]] = []

    for name, address in pairs:
        key = address.lower()

        if key == my_email or key in seen:
            continue

        seen.add(key)
        result.append((name, address))

    return result


def _internal_date(message: JsonObject) -> int:
    """Fecha interna del mensaje; 0 si no se puede leer."""
    try:
        return int(str(message.get("internalDate", "0")))
    except ValueError:
        return 0
