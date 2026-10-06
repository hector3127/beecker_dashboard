"""Conversiones de texto y busqueda flexible de columnas."""

import unicodedata
from collections.abc import Mapping, Sequence

from core.utils.cell_types import CellValue

"""BKD.003.002 - Utilidades de texto
Equivale a normalizarNombre() y valorPorClaveFlexible() de
RecursosDetalleService.gs.
"""

COMBINING_MARK_START = 0x0300

COMBINING_MARK_END = 0x036F


def to_text(value: CellValue) -> str:
    """
    Convierte un valor de celda a texto como String(x) en JavaScript.

    Args:
        value: Valor leido de Google Sheets.

    Returns:
        El texto equivalente. None se convierte en cadena vacia.
    """
    if value is None:
        return ""

    if isinstance(value, bool):
        return "true" if value else "false"

    if isinstance(value, float) and value.is_integer():
        # String(5) en JavaScript es "5", no "5.0".
        return str(int(value))

    return str(value)


def is_truthy(value: CellValue) -> bool:
    """
    Evalua un valor de celda con las reglas de verdad de JavaScript.

    Args:
        value: Valor leido de Google Sheets.

    Returns:
        False para None, cadena vacia, cero y False; True en otro caso.
    """
    return bool(value)


def text_or_default(value: CellValue, default: CellValue) -> CellValue:
    """
    Replica la expresion "value || default" de JavaScript.

    Args:
        value: Valor principal.
        default: Valor usado cuando el principal es falso.

    Returns:
        El valor principal si es verdadero; si no, el valor por defecto.
    """
    if is_truthy(value):
        return value

    return default


def normalize_name(value: CellValue) -> str:
    """
    Normaliza un nombre para compararlo sin acentos ni mayusculas.

    Args:
        value: Nombre o encabezado a normalizar.

    Returns:
        El texto en minusculas, sin espacios externos y sin acentos.
    """
    lowered_text = to_text(value).strip().lower()
    decomposed_text = unicodedata.normalize("NFD", lowered_text)

    return "".join(
        character
        for character in decomposed_text
        if not (COMBINING_MARK_START <= ord(character) <= COMBINING_MARK_END)
    )


def get_flexible_value(
    row: Mapping[str, CellValue],
    candidate_names: Sequence[str],
) -> CellValue:
    """
    Busca el valor de una columna probando varios nombres posibles.

    Ignora acentos, mayusculas y espacios externos en los encabezados,
    igual que valorPorClaveFlexible() del Apps Script.

    Args:
        row: Fila de Sheets como diccionario encabezado -> valor.
        candidate_names: Nombres posibles de la columna, en orden.

    Returns:
        El primer valor no vacio encontrado, o cadena vacia.
    """
    real_key_by_normalized = {normalize_name(header): header for header in row}

    for candidate_name in candidate_names:
        real_key = real_key_by_normalized.get(normalize_name(candidate_name))

        if real_key is None:
            continue

        cell_value = row[real_key]

        if cell_value is not None and cell_value != "":
            return cell_value

    return ""


def strip_accents(text: str) -> str:
    """
    Quita los acentos de un texto.

    Args:
        text: Texto original.

    Returns:
        El texto sin marcas diacriticas.
    """
    decomposed_text = unicodedata.normalize("NFD", text)

    return "".join(
        character
        for character in decomposed_text
        if not unicodedata.combining(character)
    )


def extract_base_id(project_id: str) -> str:
    """
    Obtiene el ID base antes del guion bajo, como _baseIdProyecto().

    Args:
        project_id: ID interno, por ejemplo AMK.008_S4.

    Returns:
        El ID base, por ejemplo AMK.008.
    """
    return project_id.split("_")[0].strip()
