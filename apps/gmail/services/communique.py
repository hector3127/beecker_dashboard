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


"""BKD.110.014 - Otros comunicados
Suspension y reanudacion (dirigidos a ROC) y cierre IXB / AER-T&M. Cada
plantilla es una lista de parrafos; se rinde en texto plano y en HTML.
"""

KIND_EXTENSION = "extension"
KIND_SUSPENSION = "suspension"
KIND_RESUMPTION = "reanudacion"
KIND_CLOSE_IXB = "cierre_ixb"
KIND_CLOSE_AER = "cierre_aer"
OTHER_KINDS = (
    KIND_SUSPENSION,
    KIND_RESUMPTION,
    KIND_CLOSE_IXB,
    KIND_CLOSE_AER,
)

Segment = str | tuple[str, str]  # texto, ("b", texto) o ("a", url)


@dataclass(frozen=True)
class CommuniqueData:
    """Campos de suspension, reanudacion o cierre ya validados."""

    kind: str
    project: str
    fields: dict[str, str]
    has_attachments: bool


def greeting(hour: int) -> str:
    """Saludo segun la hora local de envio."""
    return "Buenos días" if hour < 12 else "Buenas tardes"


def _bold_text(value: str) -> Segment:
    return ("b", value)


def _paragraphs(data: CommuniqueData, hour: int, today: str) -> list[list]:
    """Parrafos de la plantilla; cada uno es una lista de segmentos."""
    f = data.fields
    project = _bold_text(data.project)
    link = f.get("link", "")
    blocks: list[list]
    if data.kind == KIND_SUSPENSION:
        blocks = [
            [f"{greeting(hour)} ROC,"],
            [
                "Informo la suspensión temporal del proyecto ",
                project,
                ", debido a:",
            ],
            [f["reason"]],
            [
                "Esta situación impide continuar con la etapa ",
                _bold_text(f["stage"]),
                " y avanzar conforme al plan establecido.",
            ],
            [
                "La fecha tentativa de reanudación es ",
                _bold_text(format_date(f["resumeDate"])),
                ", siempre que se confirme ",
                f["condition"],
                ".",
            ],
        ]
        closing = [["Quedamos atentos a tus comentarios o confirmación."]]
    elif data.kind == KIND_RESUMPTION:
        blocks = [
            [f"{greeting(hour)} ROC,"],
            [
                "Informo la reanudación del proyecto ",
                project,
                " – ya que han sido resueltos los puntos que originaron su "
                "suspensión.",
            ],
            [
                "La fecha efectiva de reanudación es ",
                _bold_text(format_date(f["resumeDate"])),
                ", conforme a la coordinación establecida con el equipo "
                "operativo.",
            ],
            ["Retomamos las actividades según el plan de trabajo vigente."],
        ]
        closing = [["Saludos!"]]
    elif data.kind == KIND_CLOSE_IXB:
        name = f.get("projectName", "")
        title = [f' "{name}"'] if name else []
        blocks = [
            ["Hola, Buen día!"],
            [
                "Por este medio hago el comunicado oficial del cierre del "
                "proyecto ",
                project,
                *title,
                " el día ",
                _bold_text(format_date(f["closeDate"])),
            ],
            ["Adjunto la MCO donde podrán ver el VoBo del proyecto"],
        ]
        closing = [["Quedo atento a sus comentarios,"], ["Saludos!"]]
    else:
        iso = f["closeDate"]
        when = (
            ["el día de hoy - ", _bold_text(format_date(iso)), " -"]
            if iso == today
            else ["el día ", _bold_text(format_date(iso))]
        )
        about = f.get("description", "")
        tail = [f" - afiliado {about}"] if about else []
        blocks = [
            ["Buen día equipo."],
            [
                "El presente es para dar como finalizado ",
                *when,
                " el cierre de este proyecto ",
                project,
                *tail,
                ".",
            ],
            ["Se hará el pase correspondiente."],
            ["Gracias a todos por su apoyo y tiempo."],
        ]
        closing = [["Saludos cordiales."]]
    if link:
        label = "MCO" if data.kind == KIND_CLOSE_IXB else "Enlace de soporte"
        blocks.append([f"{label}: ", ("a", link)])
    if data.has_attachments:
        blocks.append(
            [
                "La MCO se incluye como archivo adjunto."
                if data.kind == KIND_CLOSE_IXB
                else "También se incluyen archivos de soporte con "
                "evidencias y detalles adicionales."
            ]
        )
    return [*blocks, *closing]


def build_other_text(data: CommuniqueData, hour: int, today: str) -> str:
    """Texto plano del comunicado."""
    lines = []
    for block in _paragraphs(data, hour, today):
        lines.append(
            "".join(
                part if isinstance(part, str) else part[1] for part in block
            )
        )
    return "\n\n".join(lines)


def build_other_html(data: CommuniqueData, hour: int, today: str) -> str:
    """HTML del comunicado, escapando todo lo capturado."""
    parts = []
    for block in _paragraphs(data, hour, today):
        inner = ""
        for part in block:
            if isinstance(part, str):
                inner += escape(part)
            elif part[0] == "b":
                inner += _bold(part[1])
            else:
                url = escape(part[1], quote=True)
                inner += f'<a href="{url}">{escape(part[1])}</a>'
        parts.append(f"<p>{inner}</p>")
    return "<div>" + "".join(parts) + "</div>"
