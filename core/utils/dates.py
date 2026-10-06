"""Conversion de fechas de Google Sheets a objetos datetime."""

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from core.utils.cell_types import CellValue

"""BKD.003.003 - Utilidades de fechas
Interpreta las fechas que entrega la API de Sheets (numero de serie o
texto) para reemplazar el uso de new Date() del Apps Script.
"""

LOCAL_TIMEZONE = ZoneInfo("America/Mexico_City")

# Google Sheets cuenta los dias a partir del 30 de diciembre de 1899.
SHEETS_EPOCH = datetime(1899, 12, 30)

TEXT_DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%d/%m/%Y",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
)

SECONDS_PER_DAY = 86_400


def to_datetime(value: CellValue | datetime | date) -> datetime | None:
    """
    Convierte un valor de celda a datetime local sin zona horaria.

    Args:
        value: Numero de serie de Sheets, texto de fecha o fecha.

    Returns:
        La fecha interpretada, o None cuando el valor no es una fecha.
    """
    if isinstance(value, datetime):
        return to_local_naive(value)

    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)

    if isinstance(value, bool) or value is None:
        return None

    if isinstance(value, int | float):
        return SHEETS_EPOCH + timedelta(days=float(value))

    return parse_date_text(value)


def parse_date_text(text: str) -> datetime | None:
    """
    Interpreta un texto de fecha en formato ISO o dia/mes/anio.

    Args:
        text: Texto leido de la celda.

    Returns:
        La fecha interpretada, o None cuando el texto no es una fecha.
    """
    clean_text = text.strip()

    if not clean_text:
        return None

    iso_moment = parse_iso_text(clean_text)

    if iso_moment is not None:
        return iso_moment

    for date_format in TEXT_DATE_FORMATS:
        try:
            return datetime.strptime(clean_text, date_format)
        except ValueError:
            # El texto no coincide con este formato; se prueba el
            # siguiente de la lista.
            continue

    return None


def parse_iso_text(text: str) -> datetime | None:
    """
    Interpreta un texto en formato ISO 8601, con o sin zona horaria.

    Args:
        text: Texto sin espacios externos.

    Returns:
        La fecha en hora local, o None si el texto no es ISO 8601.
    """
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        # No es ISO 8601; quien llama prueba los formatos dia/mes/anio.
        return None

    return to_local_naive(moment)


def to_local_naive(moment: datetime) -> datetime:
    """
    Convierte un datetime con zona horaria a hora local sin zona.

    Args:
        moment: Fecha con o sin zona horaria.

    Returns:
        La fecha en hora de la Ciudad de Mexico sin zona horaria.
    """
    if moment.tzinfo is None:
        return moment

    return moment.astimezone(LOCAL_TIMEZONE).replace(tzinfo=None)


def days_between(start: datetime, end: datetime) -> float:
    """
    Calcula los dias transcurridos entre dos fechas.

    Args:
        start: Fecha inicial.
        end: Fecha final.

    Returns:
        Los dias como numero decimal; negativo si end es anterior.
    """
    return (end - start).total_seconds() / SECONDS_PER_DAY


def format_iso_date(moment: datetime) -> str:
    """
    Da formato YYYY-MM-DD, igual que formatoFecha() del Apps Script.

    Args:
        moment: Fecha a formatear.

    Returns:
        La fecha como texto YYYY-MM-DD.
    """
    return moment.strftime("%Y-%m-%d")


def format_sheet_datetime(moment: datetime) -> str:
    """
    Da formato a una fecha para escribirla en Sheets como fecha real.

    Args:
        moment: Fecha a escribir.

    Returns:
        Texto YYYY-MM-DD HH:MM:SS que Sheets reconoce como fecha.
    """
    return to_local_naive(moment).strftime("%Y-%m-%d %H:%M:%S")


def to_utc_iso(moment: datetime) -> str:
    """
    Da formato como Date.toISOString() de JavaScript.

    Args:
        moment: Fecha local sin zona (hora de la Ciudad de Mexico) o con
            zona horaria.

    Returns:
        Fecha UTC con milisegundos y sufijo Z.
    """
    aware_moment = (
        moment.replace(tzinfo=LOCAL_TIMEZONE)
        if moment.tzinfo is None
        else moment
    )
    utc_text = aware_moment.astimezone(UTC).isoformat(timespec="milliseconds")

    return utc_text.replace("+00:00", "Z")
