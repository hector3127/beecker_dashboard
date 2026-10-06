"""Alta manual de riesgos desde el dashboard ejecutivo."""

from datetime import datetime

from core.exceptions import InvalidRequestError
from core.sheets import sheet_names
from core.sheets.audit import append_history
from core.sheets.protocols import SheetReader, SheetWriter
from core.utils.cell_types import CellValue
from core.utils.text import to_text

"""BKD.040.016 - Riesgos manuales
Equivale a agregarRiesgoManual(): agrega el riesgo en Riesgos con
estado Abierto y origen Manual-Dashboard, y lo registra en
Historico_Riesgos.
"""

IMPACTS = ("Alto", "Medio", "Bajo")
PROBABILITIES = ("Alta", "Media", "Baja")
RISK_ORIGIN = "Manual-Dashboard"
RISK_ID_COLUMN = "ID_Riesgo"


def add_manual_risk(
    repositories: tuple[SheetReader, SheetWriter],
    risk: tuple[object, object, object, object, object],
    moment: tuple[datetime, int],
) -> str:
    """
    Valida y guarda un riesgo nuevo.

    Args:
        repositories: Lector y escritor de Sheets.
        risk: Proyecto, descripcion, impacto, probabilidad y responsable.
        moment: Fecha local actual y milisegundos desde 1970 (para el ID,
            como Date.now()).

    Returns:
        El ID del riesgo creado.

    Raises:
        InvalidRequestError: Cuando falta un dato o no es valido.
    """
    reader, writer = repositories
    now, timestamp_ms = moment
    project_id, description, impact, probability, owner = risk

    if not project_id:
        raise InvalidRequestError("Falta el ID de proyecto.")

    description_text = read_text(description).strip()

    if not description_text:
        raise InvalidRequestError("Falta la descripción del riesgo.")

    if impact not in IMPACTS:
        raise InvalidRequestError("Impacto inválido.")

    if probability not in PROBABILITIES:
        raise InvalidRequestError("Probabilidad inválida.")

    project_text = read_text(project_id)
    risk_id = f"RSK-{project_text}-{timestamp_ms}"
    data: dict[str, CellValue | datetime] = {
        RISK_ID_COLUMN: risk_id,
        "ID_Proyecto": project_text,
        "Descripcion": description_text,
        "Impacto": read_text(impact),
        "Probabilidad": read_text(probability),
        "Estado": "Abierto",
        "Responsable": read_text(owner).strip(),
        "Fecha_Deteccion": now,
        "Fecha_Revision": "",
        "Plan_Mitigacion": "",
        "Origen": RISK_ORIGIN,
    }
    writer.upsert_row(sheet_names.SHEET_RISKS, RISK_ID_COLUMN, data)
    append_history(
        reader,
        writer,
        sheet_names.SHEET_RISKS_HISTORY,
        data,
        None,
        now,
    )

    return risk_id


def read_text(value: object) -> str:
    """
    Convierte un argumento del frontend a texto como String(x || '').

    Args:
        value: Valor recibido.

    Returns:
        El texto, o cadena vacia si el valor es falso.
    """
    if not value:
        return ""

    if isinstance(value, str | int | float | bool):
        return to_text(value)

    return str(value)
