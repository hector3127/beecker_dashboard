"""Conversiones de valores del dashboard AER con las reglas del original."""

import math
import re
import unicodedata
from datetime import UTC, date, datetime, timedelta

from core.utils.dates import LOCAL_TIMEZONE, to_datetime
from core.utils.js_values import js_number, js_str, js_truthy

"""BKD.080.003 - Valores AER
Equivale a _aertymRound(), _aertymPct(), _aertymTexto(),
_aertymFechaISO(), _aertymFechaObj(), _aertymNormalizarEstado() y
_aertymBool() de AERTYMProyectoService.gs.
"""

ISO_PREFIX = re.compile(r"^(\d{4})-(\d{2})-(\d{2})", re.ASCII)
US_DATE = re.compile(
    r"^(\d{1,2})/(\d{1,2})/(\d{4})(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?)?$",
    re.ASCII,
)
SLASH_ISO_DATE = re.compile(r"^(\d{4})/(\d{1,2})/(\d{1,2})$", re.ASCII)
DATE_TEXT_FORMATS = ("%a %b %d %Y", "%b %d %Y", "%d %b %Y", "%B %d, %Y")
DATE_TEXT_WITH_TIME = re.compile(r"^(\w{3} \w{3} \d{2} \d{4})")
TRUE_WORDS = frozenset({"1", "true", "si", "sí", "yes", "x", "ok"})
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def js_round(value: float) -> int:
    """Math.round() de JavaScript (los medios suben)."""
    return math.floor(value + 0.5)


def round2(value: object) -> float:
    """Math.round((Number(n) || 0) * 100) / 100."""
    number = js_number(value)
    number = 0.0 if math.isnan(number) else number

    return as_number(js_round(number * 100) / 100)


def pct(part: object, total: object) -> float:
    """Porcentaje con un decimal; 0 si el total es 0 (_aertymPct)."""
    total_number = js_number(total)

    if not js_truthy(total) or math.isnan(total_number):
        return 0

    part_number = js_number(part if js_truthy(part) else 0)

    return as_number(js_round(part_number / total_number * 1000) / 10)


def as_number(value: float) -> float:
    """Numero como lo serializa JSON.stringify (5.0 -> 5)."""
    return int(value) if float(value).is_integer() else value


def number_or_zero(value: object) -> float:
    """Number(x) || 0."""
    number = js_number(value)

    return 0.0 if math.isnan(number) else number


def clamp(value: object, low: float, high: float) -> float:
    """Math.max(low, Math.min(high, Number(v) || 0))."""
    return as_number(max(low, min(high, number_or_zero(value))))


def text(value: object) -> str:
    """
    Texto sin espacios externos (_aertymTexto).

    Las fechas de la hoja se escriben como yyyy-MM-dd HH:mm:ss.
    """
    if value is None:
        return ""

    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")

    return js_str(value).strip()


def normalize_state(value: object) -> str:
    """Mayusculas sin acentos (_aertymNormalizarEstado)."""
    decomposed = unicodedata.normalize("NFD", text(value).upper())

    return "".join(
        character
        for character in decomposed
        if not 0x0300 <= ord(character) <= 0x036F
    )


def js_date(value: object) -> datetime | None:
    """
    Fecha local como new Date(v) de JavaScript.

    Las fechas de la hoja llegan como datetime; un numero son
    milisegundos desde 1970; un texto YYYY-MM-DD es medianoche UTC.

    Args:
        value: Valor recibido.

    Returns:
        La fecha y hora local sin zona, o None si no es valida.
    """
    if isinstance(value, datetime):
        return value

    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)

    if isinstance(value, bool):
        return utc_to_local(EPOCH + timedelta(milliseconds=int(value)))

    if isinstance(value, int | float):
        if not math.isfinite(value):
            return None

        return utc_to_local(EPOCH + timedelta(milliseconds=value))

    return parse_date_text(js_str(value).strip()) if value is not None else None


def utc_to_local(moment: datetime) -> datetime:
    """Instante UTC a hora local sin zona."""
    return moment.astimezone(LOCAL_TIMEZONE).replace(tzinfo=None)


def parse_date_text(raw: str) -> datetime | None:
    """Formatos de texto que entiende new Date() y que usan las hojas."""
    iso = ISO_PREFIX.match(raw)

    if iso and len(raw) == len("2026-01-01"):
        try:
            day = date(int(iso[1]), int(iso[2]), int(iso[3]))
        except ValueError:
            return None

        return utc_to_local(datetime(day.year, day.month, day.day, tzinfo=UTC))

    if iso:
        try:
            moment = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None

        return utc_to_local(moment) if moment.tzinfo else moment

    for pattern in (US_DATE, SLASH_ISO_DATE):
        match = pattern.match(raw)

        if match:
            return build_slash_date(pattern, match.groups())

    prefix = DATE_TEXT_WITH_TIME.match(raw)
    candidate = prefix.group(1) if prefix else raw

    for date_format in DATE_TEXT_FORMATS:
        try:
            return datetime.strptime(candidate, date_format)
        except ValueError:
            continue

    return None


def build_slash_date(
    pattern: re.Pattern[str],
    groups: tuple[str | None, ...],
) -> datetime | None:
    """M/D/YYYY [HH:mm[:ss]] o YYYY/M/D en hora local."""
    try:
        if pattern is SLASH_ISO_DATE:
            return datetime(
                int(groups[0] or 0), int(groups[1] or 0), int(groups[2] or 0)
            )

        month, day, year, hour, minute, second = groups
        return datetime(
            int(year or 0),
            int(month or 0),
            int(day or 0),
            int(hour or 0),
            int(minute or 0),
            int(second or 0),
        )
    except ValueError:
        return None


def date_iso(value: object) -> str:
    """
    Fecha YYYY-MM-DD (_aertymFechaISO).

    Un texto que empieza con YYYY-MM-DD se recorta; lo demas se interpreta
    como new Date(v) en la zona horaria del script.
    """
    if not js_truthy(value):
        return ""

    if isinstance(value, str):
        iso = ISO_PREFIX.match(value)

        if iso:
            return f"{iso[1]}-{iso[2]}-{iso[3]}"

    moment = js_date(value)

    return moment.strftime("%Y-%m-%d") if moment else ""


def date_obj(value: object) -> date | None:
    """Dia local de la fecha (_aertymFechaObj)."""
    iso = date_iso(value)

    if not iso:
        return None

    try:
        return date.fromisoformat(iso)
    except ValueError:
        return None


def to_bool(value: object) -> bool:
    """Si/no flexible (_aertymBool)."""
    if isinstance(value, bool):
        return value

    return text(value).lower() in TRUE_WORDS


def sheet_date(value: object) -> object:
    """Numero de serie de una columna de fecha como datetime local."""
    if isinstance(value, int | float) and not isinstance(value, bool):
        return to_datetime(value)

    return value
