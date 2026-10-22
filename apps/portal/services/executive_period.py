"""Validated executive date ranges isolated per request and cache."""

from calendar import monthrange
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import date, datetime
from functools import wraps
from typing import Any, Concatenate

from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.utils import timezone


@dataclass(frozen=True)
class ExecutivePeriod:
    """Fechas inclusivas y modo de seleccion de la vista ejecutiva."""

    start: date
    end: date
    mode: str

    @property
    def label(self) -> str:
        """Etiqueta local del rango elegido."""
        return f"{self.start:%d/%m/%Y} - {self.end:%d/%m/%Y}"

    @property
    def key(self) -> str:
        """Identidad del rango para separar resultados guardados."""
        return f"{self.start.isoformat()}:{self.end.isoformat()}"


_current: ContextVar[ExecutivePeriod | None] = ContextVar(
    "executive_period",
    default=None,
)


def parse(
    query: Mapping[str, Any], today: date | None = None
) -> ExecutivePeriod:
    """Valida un ano, trimestre, mes o rango de hasta tres anos."""
    today = today or timezone.localdate()
    mode = query.get("periodo", "anio")
    year = int(query.get("anio", today.year))
    if not 2000 <= year <= 2100:
        raise ValueError("El ano debe estar entre 2000 y 2100.")
    if mode == "anio":
        start, end = date(year, 1, 1), date(year, 12, 31)
    elif mode == "trimestre":
        quarter = int(query.get("trimestre", (today.month - 1) // 3 + 1))
        if quarter not in range(1, 5):
            raise ValueError("Selecciona un trimestre del 1 al 4.")
        month = (quarter - 1) * 3 + 1
        start, end = (
            date(year, month, 1),
            date(year, month + 2, monthrange(year, month + 2)[1]),
        )
    elif mode == "mes":
        month = int(query.get("mes", today.month))
        start, end = (
            date(year, month, 1),
            date(year, month, monthrange(year, month)[1]),
        )
    elif mode == "rango":
        start, end = (
            date.fromisoformat(query.get("desde", "")),
            date.fromisoformat(query.get("hasta", "")),
        )
    else:
        raise ValueError("Periodo no valido.")
    if end < start:
        raise ValueError(
            "La fecha final debe ser igual o posterior a la inicial."
        )
    if (end - start).days > 1096:
        raise ValueError("El rango no puede superar tres anos.")
    return ExecutivePeriod(start, end, mode)


def current() -> ExecutivePeriod | None:
    """Periodo propio de la peticion, sin afectar otras consultas."""
    return _current.get()


def bounds() -> tuple[date, date]:
    """Limites seleccionados o el ejercicio 2026 predeterminado."""
    period = current()
    return (
        (period.start, period.end)
        if period
        else (date(2026, 1, 1), date(2026, 12, 31))
    )


def contains(moment: datetime | None) -> bool:
    """Comprueba la fecha local, incluyendo ambos extremos del rango."""
    if not moment:
        return False
    start, end = bounds()
    return start <= moment.date() <= end


def cache_suffix() -> str:
    """Sufijo de cache exclusivo de las fechas seleccionadas."""
    first, last = bounds()
    # The default financial exercise and an explicit full-2026 range are
    # identical.
    if first == date(2026, 1, 1) and last == date(2026, 12, 31):
        return ""
    return ":period:" + first.isoformat() + ":" + last.isoformat()


@contextmanager
def applied(period: ExecutivePeriod | None) -> Iterator[None]:
    """Aplica un periodo ya validado a lo que se calcule dentro del bloque."""
    token = _current.set(period)
    try:
        yield
    finally:
        _current.reset(token)


def period_view[**P](
    view: Callable[Concatenate[HttpRequest, P], HttpResponse],
) -> Callable[Concatenate[HttpRequest, P], HttpResponse]:
    """Aplica el periodo a la vista y lo restaura incluso ante errores."""

    @wraps(view)
    def wrapped(
        request: HttpRequest, /, *args: P.args, **kwargs: P.kwargs
    ) -> HttpResponse:
        try:
            period = parse(request.GET) if "periodo" in request.GET else None
        except (ValueError, TypeError, OverflowError) as error:
            return HttpResponseBadRequest(str(error))
        token = _current.set(period)
        request.__dict__["executive_period"] = period
        try:
            return view(request, *args, **kwargs)
        finally:
            _current.reset(token)

    return wrapped


def query_string() -> str:
    """Conserva la seleccion al navegar a cuentas y costos."""
    from urllib.parse import urlencode

    selected = current()
    if not selected:
        return ""
    values: dict[str, str | int] = {
        "periodo": selected.mode,
        "anio": selected.start.year,
    }
    if selected.mode == "rango":
        values = {
            "periodo": "rango",
            "desde": selected.start.isoformat(),
            "hasta": selected.end.isoformat(),
        }
    elif selected.mode == "trimestre":
        values["trimestre"] = (selected.start.month - 1) // 3 + 1
    elif selected.mode == "mes":
        values["mes"] = selected.start.month
    return urlencode(values)
