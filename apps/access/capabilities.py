"""Catalogo de capacidades: lo que una persona puede hacer en el portal."""

from dataclasses import dataclass

"""BKD.140.002 - Catalogo de capacidades
Los codigos son un contrato estable: Genesis asigna estos nombres a sus
roles y el frontend los lee de /api/v1/me/. Una capacidad nueva se agrega
aqui junto con la pantalla o accion que protege.
"""


@dataclass(frozen=True)
class Capability:
    """Una accion que se puede conceder: codigo estable y nombre legible."""

    code: str
    label: str


CATALOG: tuple[Capability, ...] = (
    Capability("view_executive", "Ver Business Overview"),
    Capability("view_operations", "Ver Operativa"),
    Capability("view_commercial", "Ver Comercial"),
    Capability("view_costs", "Ver costos, ingresos y márgenes"),
    Capability("view_agreements", "Consultar acuerdos y pendientes"),
    Capability("edit_agreements", "Crear y modificar acuerdos y pendientes"),
)

CODES: frozenset[str] = frozenset(item.code for item in CATALOG)
