"""Texto del comunicado de extension de proyecto."""

from dataclasses import dataclass
from html import escape

"""BKD.110.009 - Comunicado de extension
Genera el mismo texto de la vista previa, en texto plano y en HTML, a
partir de los datos capturados.
"""


@dataclass(frozen=True)
class ExtensionData:
    """Datos capturados en la pantalla de extension."""

    project: str
    stage: str
    current_date: str
    new_date: str
    reason: str
    roadmap_link: str
    has_attachments: bool


def format_date(iso_date: str) -> str:
    """
    Pasa una fecha AAAA-MM-DD a DD/MM/AAAA.

    Args:
        iso_date: Fecha en formato ISO.

    Returns:
        La fecha con dia primero.
    """
    year, month, day = iso_date.split("-")

    return f"{day}/{month}/{year}"


def reason_sentence(reason: str) -> str:
    """
    Deja el motivo listo para ir despues de "debido a que".

    Args:
        reason: Motivo escrito por el usuario.

    Returns:
        El motivo con la primera letra en minuscula y sin punto final.
    """
    clean = " ".join(reason.split())

    if not clean:
        return clean

    return (clean[0].lower() + clean[1:]).rstrip(".")


def build_text(data: ExtensionData) -> str:
    """
    Arma el comunicado en texto plano.

    Args:
        data: Datos de la extension.

    Returns:
        El texto del correo.
    """
    lines = [
        "Hola estimados,",
        "",
        f"Informo la extensión del proyecto {data.project} debido a que "
        f"{reason_sentence(data.reason)}.",
        "",
        f"Esta situación impide cerrar la etapa {data.stage} en la fecha "
        "originalmente establecida.",
        "",
        "Fechas actualizadas:",
        f"  • Fecha actual de cierre: {format_date(data.current_date)}",
        f"  • Nueva fecha: {format_date(data.new_date)}",
        "",
        "Adjunto el Roadmap actualizado, el cual se compartirá mediante el "
        "siguiente enlace:",
        f"Roadmap actualizado: {data.roadmap_link}",
        "",
    ]

    if data.has_attachments:
        lines += [
            "También se incluyen archivos de soporte con evidencias y "
            "detalles adicionales.",
            "",
        ]

    lines.append("Saludos!")

    return "\n".join(lines)


def _bold(value: str) -> str:
    """Texto escapado en negritas."""
    return f"<b>{escape(value)}</b>"


def build_html(data: ExtensionData) -> str:
    """
    Arma el comunicado en HTML, escapando todo lo capturado.

    Args:
        data: Datos de la extension.

    Returns:
        El HTML del correo.
    """
    link = escape(data.roadmap_link, quote=True)
    support = (
        "<p>También se incluyen archivos de soporte con evidencias y "
        "detalles adicionales.</p>"
        if data.has_attachments
        else ""
    )

    return (
        "<div>"
        "<p>Hola estimados,</p>"
        f"<p>Informo la extensión del proyecto {_bold(data.project)} debido "
        f"a que {escape(reason_sentence(data.reason))}.</p>"
        f"<p>Esta situación impide cerrar la etapa {_bold(data.stage)} en la "
        "fecha originalmente establecida.</p>"
        "<p>Fechas actualizadas:</p>"
        "<ul>"
        f"<li>Fecha actual de cierre: {_bold(format_date(data.current_date))}"
        "</li>"
        f"<li>Nueva fecha: {_bold(format_date(data.new_date))}</li>"
        "</ul>"
        "<p>Adjunto el Roadmap actualizado, el cual se compartirá mediante "
        "el siguiente enlace:</p>"
        f'<p>Roadmap actualizado: <a href="{link}">Ver roadmap</a></p>'
        f"{support}"
        "<p>Saludos!</p>"
        "</div>"
    )
