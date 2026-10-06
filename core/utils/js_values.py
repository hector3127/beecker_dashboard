"""Conversiones de valores con las reglas de JavaScript."""

import json
import math
import re
import unicodedata
from decimal import Decimal
from typing import Any

from core.utils.text import to_text

"""BKD.002.004 - Valores como en JavaScript
String(x), !!x, x || '', Number(x) y JSON.stringify(x) tal como los
evaluaba Apps Script, para respuestas identicas al original.
"""

MAX_PLAIN_EXPONENT = 21
MIN_PLAIN_EXPONENT = -6
JS_DECIMAL = re.compile(
    r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?|[+-]?Infinity",
    re.ASCII,
)
JS_RADIX = re.compile(r"0([xX][0-9a-fA-F]+|[oO][0-7]+|[bB][01]+)", re.ASCII)
RADIX_BASES = {"x": 16, "o": 8, "b": 2}


def js_truthy(value: object) -> bool:
    """
    Verdad de JavaScript (!!x).

    Args:
        value: Valor recibido.

    Returns:
        False para null, false, 0, NaN y ""; True en otro caso.
    """
    if value is None or value is False or value == "":
        return False

    if isinstance(value, int | float) and not isinstance(value, bool):
        return value != 0 and not math.isnan(value)

    return True


def js_str(value: object) -> str:
    """
    Texto como String(x) de JavaScript.

    Args:
        value: Valor recibido.

    Returns:
        El texto; null -> "null", listas unidas por comas.
    """
    if value is None:
        return "null"

    if isinstance(value, dict):
        return "[object Object]"

    if isinstance(value, list):
        return ",".join("" if item is None else js_str(item) for item in value)

    if isinstance(value, float):
        return js_number_text(value)

    return (
        to_text(value) if isinstance(value, str | int | float) else str(value)
    )


def js_number_text(number: float) -> str:
    """
    Texto de un numero como Number.prototype.toString().

    Args:
        number: Numero.

    Returns:
        "5", "0.1", "1e+21", "1e-7", "NaN", "Infinity", etc.
    """
    if math.isnan(number):
        return "NaN"

    if math.isinf(number):
        return "Infinity" if number > 0 else "-Infinity"

    if number == 0:
        return "0"

    sign = "-" if number < 0 else ""
    digits_tuple = Decimal(repr(abs(number))).normalize().as_tuple()
    digits = "".join(str(digit) for digit in digits_tuple.digits)
    exponent = int(digits_tuple.exponent) + len(digits)
    size = len(digits)

    if size <= exponent <= MAX_PLAIN_EXPONENT:
        text = digits + "0" * (exponent - size)
    elif 0 < exponent <= MAX_PLAIN_EXPONENT:
        text = f"{digits[:exponent]}.{digits[exponent:]}"
    elif MIN_PLAIN_EXPONENT < exponent <= 0:
        text = f"0.{'0' * -exponent}{digits}"
    else:
        power = exponent - 1
        mantissa = digits if size == 1 else f"{digits[0]}.{digits[1:]}"
        text = f"{mantissa}e{'+' if power >= 0 else '-'}{abs(power)}"

    return sign + text


def js_or_text(value: object) -> str:
    """Texto como String(x || '')."""
    return js_str(value) if js_truthy(value) else ""


def js_null_text(value: object) -> str:
    """Texto como String(x == null ? '' : x)."""
    return "" if value is None else js_str(value)


def js_number(value: object) -> float:
    """
    Numero como Number(x) de JavaScript (NaN si no es numero).

    Args:
        value: Valor recibido.

    Returns:
        El numero.
    """
    if value is None or value == "":
        return 0.0

    if isinstance(value, bool | int | float):
        return float(value)

    if not isinstance(value, str):
        return math.nan

    text = value.strip()

    if not text:
        return 0.0

    radix = JS_RADIX.fullmatch(text)

    if radix:
        prefix = radix.group(1)
        return float(int(prefix[1:], RADIX_BASES[prefix[0].lower()]))

    if JS_DECIMAL.fullmatch(text):
        return float(text.replace("Infinity", "inf"))

    return math.nan


def js_or(value: object, default: object) -> Any:
    """Valor como x || default."""
    return value if js_truthy(value) else default


def js_len(text: str) -> int:
    """Largo en unidades UTF-16, como String.prototype.length."""
    return len(text.encode("utf-16-le")) // 2


def js_slice(text: str, start: int, end: int | None = None) -> str:
    """
    String.prototype.slice() con posiciones en unidades UTF-16.

    Args:
        text: Texto.
        start: Inicio (negativo cuenta desde el final).
        end: Fin exclusivo, o None para el final.

    Returns:
        El fragmento.
    """
    if text.isascii() or all(ord(character) < 0x10000 for character in text):
        return text[start:end]

    units = text.encode("utf-16-le")
    size = len(units) // 2
    first = max(0, size + start) if start < 0 else min(start, size)
    last = (
        size
        if end is None
        else max(0, size + end)
        if end < 0
        else min(end, size)
    )

    if last <= first:
        return ""

    return units[first * 2 : last * 2].decode("utf-16-le", errors="replace")


def js_object_keys(data: dict[str, Any]) -> list[str]:
    """Object.keys(): primero las llaves enteras en orden, luego las demas."""
    integer_keys = sorted(
        (key for key in data if is_array_index(key)),
        key=int,
    )

    return integer_keys + [key for key in data if not is_array_index(key)]


def is_array_index(key: str) -> bool:
    """Llave que JavaScript ordena como indice ("0", "12", no "012")."""
    return key.isascii() and key.isdigit() and (key == "0" or key[0] != "0")


def js_json(data: object) -> str:
    """Texto como JSON.stringify(x) (sin espacios ni escapes ASCII)."""
    return json.dumps(
        json_ready(data),
        ensure_ascii=False,
        separators=(",", ":"),
    )


def json_ready(data: object) -> Any:
    """
    Prepara un valor como lo serializa JSON.stringify.

    Los numeros sin decimales van como enteros, NaN e Infinity como null y
    las llaves de los objetos en el orden de Object.keys().
    """
    if isinstance(data, bool) or data is None or isinstance(data, str | int):
        return data

    if isinstance(data, float):
        if not math.isfinite(data):
            return None

        return int(data) if data.is_integer() and abs(data) < 2**53 else data

    if isinstance(data, dict):
        text_keys = {str(key): value for key, value in data.items()}
        return {
            key: json_ready(text_keys[key]) for key in js_object_keys(text_keys)
        }

    if isinstance(data, list | tuple):
        return [json_ready(item) for item in data]

    return str(data)


def to_json_number(number: float) -> int | float:
    """Numero listo para JSON: entero cuando no tiene decimales."""
    return int(number) if number.is_integer() else number


def js_locale_key(text: str) -> tuple[str, str, str]:
    """
    Llave de orden aproximada a localeCompare() (es).

    Compara sin acentos ni mayusculas; luego con acentos; luego pone las
    minusculas antes que las mayusculas.
    """
    base = "".join(
        character
        for character in unicodedata.normalize("NFD", text)
        if not 0x0300 <= ord(character) <= 0x036F
    )

    return base.lower(), text.lower(), text.swapcase()
