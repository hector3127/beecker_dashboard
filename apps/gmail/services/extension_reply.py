"""Valida la extension y la entrega como borrador o envio en el hilo."""

import logging
import os
import re
from collections.abc import Mapping
from datetime import date
from typing import Any, Protocol
from urllib.parse import urlsplit

from apps.gmail.constants import (
    ALLOWED_EXTENSIONS,
    DELIVERY_DRAFT,
    DELIVERY_SEND,
    GMAIL_WEB_URL,
    MAX_FILE_BYTES,
    MAX_FILES,
    MAX_REASON_LENGTH,
    MAX_TOTAL_BYTES,
    STAGES,
)
from apps.gmail.exceptions import GmailApiError, ReplyValidationError
from apps.gmail.services.communique import (
    ExtensionData,
    build_html,
    build_text,
)
from apps.gmail.services.reply_builder import (
    Attachment,
    build_raw_message,
    build_references,
    compute_reply_all,
    headers_of,
    last_message,
    reply_subject,
)
from apps.gmail.services.thread_finder import is_project_thread

"""BKD.110.011 - Entrega de la extension
Comprueba los datos, calcula a quien va la respuesta con el ultimo
mensaje del hilo elegido y crea el borrador (o envia) dentro del hilo.
"""

logger = logging.getLogger("gmail.audit")

JsonObject = dict[str, Any]

THREAD_ID_PATTERN = re.compile(r"^[0-9a-fA-F]{8,32}$")


class ReplyApi(Protocol):
    """Lo que se necesita de GmailApi para responder."""

    def get_thread(self, thread_id: str) -> JsonObject:
        """Lee un hilo."""
        ...

    def create_draft(self, raw: str, thread_id: str) -> JsonObject:
        """Crea un borrador."""
        ...

    def send_message(self, raw: str, thread_id: str) -> JsonObject:
        """Envia un mensaje."""
        ...


def parse_extension(
    fields: Mapping[str, str],
    attachment_count: int,
) -> tuple[ExtensionData, str]:
    """
    Valida los campos capturados.

    Args:
        fields: Datos del formulario.
        attachment_count: Cuantos archivos se adjuntan.

    Returns:
        Los datos de la extension y el ID del hilo elegido.

    Raises:
        ReplyValidationError: Cuando falta o es invalido algun dato.
    """
    project = fields.get("project", "").strip()
    stage = fields.get("stage", "").strip()
    reason = fields.get("reason", "").strip()
    link = fields.get("roadmapLink", "").strip()
    thread_id = fields.get("threadId", "").strip()

    if not project:
        raise ReplyValidationError("Falta el proyecto.")

    if stage not in STAGES:
        raise ReplyValidationError("Elige una etapa valida.")

    if not reason or len(reason) > MAX_REASON_LENGTH:
        raise ReplyValidationError(
            f"El motivo es obligatorio y mide hasta {MAX_REASON_LENGTH}.",
        )

    if (
        urlsplit(link).scheme not in ("http", "https")
        or not urlsplit(
            link,
        ).netloc
    ):
        raise ReplyValidationError("El link del roadmap debe ser http(s).")

    if not THREAD_ID_PATTERN.match(thread_id):
        raise ReplyValidationError("Elige el hilo donde se va a responder.")

    data = ExtensionData(
        project=project,
        stage=stage,
        current_date=_check_date(fields.get("currentDate", "")),
        new_date=_check_date(fields.get("newDate", "")),
        reason=reason,
        roadmap_link=link,
        has_attachments=attachment_count > 0,
    )

    return data, thread_id


def validate_files(
    files: list[tuple[str, bytes]],
) -> list[Attachment]:
    """
    Comprueba tipo, tamano y cantidad de los archivos.

    Args:
        files: Nombre y contenido de cada archivo.

    Returns:
        Los archivos como adjuntos con nombre seguro.

    Raises:
        ReplyValidationError: Cuando alguno no cumple.
    """
    if len(files) > MAX_FILES:
        raise ReplyValidationError(f"Maximo {MAX_FILES} archivos.")

    total = sum(len(content) for _, content in files)

    if total > MAX_TOTAL_BYTES:
        raise ReplyValidationError("Los archivos pesan mas de 18 MB juntos.")

    attachments: list[Attachment] = []

    for raw_name, content in files:
        name = os.path.basename(raw_name.replace("\\", "/")).strip()

        if not name.lower().endswith(ALLOWED_EXTENSIONS):
            raise ReplyValidationError(f"{name or 'Archivo'}: tipo no valido.")

        if len(content) > MAX_FILE_BYTES:
            raise ReplyValidationError(f"{name} pesa mas de 10 MB.")

        attachments.append(Attachment(name, content))

    return attachments


def deliver_extension(
    api: ReplyApi,
    my_email: str,
    data: ExtensionData,
    thread_id: str,
    attachments: list[Attachment],
    mode: str,
) -> JsonObject:
    """
    Responde a todos en el hilo, como borrador o como envio.

    Args:
        api: Cliente de Gmail del usuario.
        my_email: Correo de quien responde.
        data: Datos validados de la extension.
        thread_id: Hilo elegido.
        attachments: Archivos de soporte validados.
        mode: "draft" o "send".

    Returns:
        Resumen de lo creado: modo, destinatarios, asunto y enlace.

    Raises:
        ReplyValidationError: Cuando el hilo no es de un proyecto.
        GmailApiError: Cuando Gmail rechaza la creacion.
    """
    thread = api.get_thread(thread_id)
    message = last_message(thread)

    if message is None:
        raise ReplyValidationError("El hilo no tiene mensajes.")

    headers = headers_of(message)
    thread_subject = headers.get("subject", "")

    if not is_project_thread(thread_subject):
        raise ReplyValidationError(
            "Solo se puede responder en hilos que empiecen con Inicio de.",
        )

    to_list, cc_list = compute_reply_all(headers, my_email)

    if not to_list and not cc_list:
        raise ReplyValidationError("El hilo no tiene a quien responder.")

    subject = reply_subject(thread_subject)
    raw = build_raw_message(
        sender=my_email,
        to_list=to_list,
        cc_list=cc_list,
        subject=subject,
        reply_headers=build_references(headers),
        bodies=(build_text(data), build_html(data)),
        attachments=attachments,
    )

    if mode == DELIVERY_SEND:
        created = api.send_message(raw, thread_id)
        message_id = str(created.get("id", ""))
        link = f"{GMAIL_WEB_URL}#all/{thread_id}"
    else:
        created = api.create_draft(raw, thread_id)
        draft_message = created.get("message")
        message_id = (
            str(draft_message.get("id", ""))
            if isinstance(draft_message, dict)
            else ""
        )

        if not message_id:
            raise GmailApiError("Gmail no devolvio el borrador creado.")

        link = f"{GMAIL_WEB_URL}#drafts?compose={message_id}"

    logger.info(
        "Extension %s: sender=%s project=%s thread=%s message=%s "
        "to=%d cc=%d files=%d",
        "enviada" if mode == DELIVERY_SEND else "borrador",
        my_email,
        data.project,
        thread_id,
        message_id,
        len(to_list),
        len(cc_list),
        len(attachments),
    )

    return {
        "mode": DELIVERY_SEND if mode == DELIVERY_SEND else DELIVERY_DRAFT,
        "subject": subject,
        "to": to_list,
        "cc": cc_list,
        "link": link,
    }


def _check_date(value: str) -> str:
    """Comprueba que sea una fecha AAAA-MM-DD valida."""
    try:
        date.fromisoformat(value.strip())
    except ValueError as error:
        raise ReplyValidationError(
            "Las fechas deben tener formato AAAA-MM-DD.",
        ) from error

    return value.strip()
