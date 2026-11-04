"""Fuentes opcionales de Planeación/RAID sin ampliar la carga predeterminada."""

from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command

from apps.datastore.models import SheetSnapshot
from apps.datastore.services.project_sheets import (
    OPTIONAL_PROJECT_SHEETS,
    PROJECT_SHEETS,
    ProjectSheetError,
    sync_project_sheets,
)
from tests.datastore.test_project_sheets import Reader

pytestmark = pytest.mark.django_db
CASES = [
    ("AER_Planeacion", ["UID", "ID_Proyecto", "Actividad"]),
    ("AER_Riesgos", ["UID", "ID_Proyecto", "Riesgo"]),
    ("AER_Vacaciones", ["UID", "ID_Proyecto", "Recurso", "Inicio", "Fin"]),
    ("IXS_Planeacion", ["UID", "ID_Proyecto", "Tipo", "DatosJSON"]),
]


@pytest.mark.parametrize("name,header", CASES)
def test_fuentes_opcionales_preservan_celdas(name, header):
    rows = [header, ["u", "AMK.001_S1", '{"nota":"á"}', "", 1]]
    reader = Reader({name: rows})
    assert sync_project_sheets(reader, [name]) == {name: 1}
    assert SheetSnapshot.objects.get(name=name).rows == rows


@pytest.mark.parametrize("name,header", CASES)
def test_falta_encabezado_rechaza_el_lote(name, header):
    with pytest.raises(ProjectSheetError):
        sync_project_sheets(Reader({name: [header[:-1]]}), [name])
    assert not SheetSnapshot.objects.exists()


def test_inspeccion_opcional_no_crea_cliente_google():
    output = StringIO()
    with patch(
        "apps.datastore.management.commands.sync_project_sheets.build_sheet_repository"
    ) as factory:
        call_command("sync_project_sheets", hoja=["AER_Riesgos"], stdout=output)
    factory.assert_not_called()
    assert "AER_Riesgos" in output.getvalue()
    assert "sin copia local" in output.getvalue()


def test_predeterminadas_y_opcionales_son_alcances_distintos():
    assert len(PROJECT_SHEETS) == 12
    assert set(OPTIONAL_PROJECT_SHEETS) == {name for name, _ in CASES}
    assert not set(PROJECT_SHEETS) & set(OPTIONAL_PROJECT_SHEETS)
