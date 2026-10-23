"""Transporte HTTP de GSE; conserva los servicios y campos del RPC anterior."""

import re
from typing import Any

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework.exceptions import ParseError
from rest_framework.request import Request
from rest_framework.response import Response

from apps.gse import rpc
from apps.portal.api.operations import OperationsScreen


def _integer(value: Any, label: str, low: int, high: int) -> int:
    if isinstance(value, bool) or not re.fullmatch(r"[0-9]+", str(value)):
        raise ParseError(f"{label} no válido.")
    number = int(value)
    if not low <= number <= high:
        raise ParseError(f"{label} fuera de rango.")
    return number


def _year(data: Any) -> int:
    return _integer(data.get("anio", ""), "Año", 2000, 2100)


def _payload(request: Request) -> dict[str, Any]:
    data = request.data
    if not isinstance(data, dict):
        raise ParseError("Se esperaba un objeto JSON.")
    return data


def _area(data: Any) -> str:
    area = data.get("area", "")
    if not isinstance(area, str):
        raise ParseError("Área no válida.")
    return area


def _month(data: Any) -> str:
    month = str(data.get("mes", ""))
    if not re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", month):
        raise ParseError("Selecciona un mes válido (AAAA-MM).")
    _integer(month[:4], "Año", 2000, 2100)
    return month


class AreaListView(OperationsScreen):
    """Áreas de Bandas/rol, sin consultar horas."""

    def get(self, request: Request) -> Response:
        """Lista las áreas sin recalcular el catálogo."""
        return self.body(rpc.get_gse_areas())


class AreaMonthView(OperationsScreen):
    """Mes de Clockify, incluyendo los estados de lectura parcial."""

    def get(self, request: Request) -> Response:
        """Conserva mes, fuente, área y refresco del servicio original."""
        data = request.query_params
        month = _month(data)
        source = data.get("fuente", "sheet")
        if source not in {"sheet", "api"}:
            raise ParseError("Fuente no válida.")
        return self.body(
            rpc.get_gse_month(
                month,
                source,
                data.get("actualizar") == "1",
                _area(data),
            )
        )


class AreaBatchView(OperationsScreen):
    """Lectura anual por lotes con cursor y total de la consulta original."""

    def get(self, request: Request) -> Response:
        """Valida el cursor y entrega el lote sin transformar sus registros."""
        data = request.query_params
        year = _year(data)
        cursor = _integer(data.get("cursor", "0"), "Cursor", 0, 2**53 - 1)
        total = data.get("total")
        expected = (
            None
            if total in {None, ""}
            else _integer(total, "Total", 0, 2**53 - 1)
        )
        return self.body(
            rpc.get_gse_batch(
                year,
                _area(data),
                cursor,
                expected,
                data.get("actualizar") == "1",
            )
        )


@method_decorator(csrf_protect, name="dispatch")
class AreaCacheView(OperationsScreen):
    """Resultado anual guardado; el refresco y guardado utilizan POST."""

    def get(self, request: Request) -> Response:
        """Lee el resultado anual disponible."""
        return self.body(
            rpc.read_gse_result_cache(
                _year(request.query_params),
                _area(request.query_params),
                False,
            )
        )

    def post(self, request: Request) -> Response:
        """Invalida o guarda el mismo resultado anual de GSE."""
        data = _payload(request)
        year = _year(data)
        area = _area(data)
        if not isinstance(data.get("borrar", False), bool):
            raise ParseError("El indicador de borrado debe ser booleano.")
        if data.get("borrar") is True:
            return self.body(rpc.read_gse_result_cache(year, area, True))
        result = data.get("resultado")
        if not isinstance(result, dict):
            raise ParseError("Falta el resultado anual.")
        return self.body(rpc.save_gse_result_cache(year, area, result))


@method_decorator(csrf_protect, name="dispatch")
class AreaIdsView(OperationsScreen):
    """Búsqueda y guardado de IDs con el mismo permiso del RPC original."""

    def post(self, request: Request) -> Response:
        """Obtiene y guarda IDs, conservando la continuación por reporte."""
        data = _payload(request)
        month = _month(data)
        report = data.get("solo_reporte", False)
        if not isinstance(report, bool):
            raise ParseError("El modo de reporte debe ser booleano.")
        return self.body(rpc.get_gse_clockify_ids(month, report))
