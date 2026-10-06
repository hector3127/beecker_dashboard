import pytest

from apps.dashboard.schemas.dashboard_filters import parse_dashboard_filters
from apps.dashboard.schemas.records import build_project_record
from apps.dashboard.services.filters import build_available_filters
from core.exceptions import InvalidRequestError
from core.utils.cell_types import SheetRow


def test_sentinel_labels_mean_no_filter():
    filters = parse_dashboard_filters(
        {"proyecto": "Todos los proyectos", "cliente": "Todos los clientes"},
    )

    assert filters.is_empty


def test_invalid_payload_is_rejected():
    with pytest.raises(InvalidRequestError):
        parse_dashboard_filters(["P-1"])


def test_available_filters_deduplicate_and_sort_clients():
    rows: list[SheetRow] = [
        {"ID_Proyecto": " P-1 ", "Nombre": "", "Cliente": "Zeta"},
        {"ID_Proyecto": "P-1", "Nombre": "Duplicado", "Cliente": "Zeta"},
        {
            "ID_Proyecto": "P-2",
            "Nombre": "Beta",
            "Cliente": "ACME",
            "Service": " AER ",
            "Estado": "Development",
        },
        {"ID_Proyecto": "", "Nombre": "Sin ID", "Cliente": ""},
    ]
    projects = [build_project_record(row) for row in rows]

    available = build_available_filters(projects)

    assert available["clientes"] == ["Todos los clientes", "ACME", "Zeta"]
    assert available["proyectos"] == [
        {
            "id": "P-1",
            "nombre": "P-1",
            "cliente": "Zeta",
            "servicio": "",
            "estado": "",
        },
        {
            "id": "P-2",
            "nombre": "Beta",
            "cliente": "ACME",
            "servicio": "AER",
            "estado": "Development",
        },
    ]
