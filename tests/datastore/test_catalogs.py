import pytest

from apps.datastore.models import (
    Client,
    ClientAlias,
    ClockifyTimeEntry,
    Person,
    PersonAlias,
    Project,
)
from apps.datastore.services import catalogs

pytestmark = pytest.mark.django_db


def sheet(width, *rows, header=None):
    """Hoja de prueba: encabezado de `header` {columna: texto} y filas."""
    top = [""] * width
    for index, text in (header or {}).items():
        top[index] = text
    return [top, *rows]


def row(width, **cells):
    values = [""] * width
    for index, value in cells.items():
        values[int(index.removeprefix("c"))] = value
    return values


def sample_sheets():
    return {
        "Proyectos": sheet(
            11,
            row(
                11,
                c0="GPO.007",
                c1="MultiProfile",
                c2="Grupo Posadas",
                c3="IxB",
                c4="Christian Samano",
            ),
            row(
                11, c0="GPO.001_ CR", c1="Cambio", c2="Grupo Posadas", c3="IxB"
            ),
            header={
                0: "ID_Proyecto",
                1: "Nombre",
                2: "Cliente",
                3: "Servicio",
                4: "Scrum_Master",
            },
        ),
        "MPB": sheet(
            21,
            row(
                21,
                c1="grupo  posadas",
                c2="GPO.007",
                c4="Otro nombre",
                c5="IXB",
                c20="Dora Quintero",
            ),
            row(
                21,
                c1="Zurich Brasil",
                c2="ZUR.B.008_S1",
                c4="Comprobantes",
                c5="IxB",
                c20="Dora Quintero",
            ),
            header={
                1: "CLIENTE",
                2: "ID",
                4: "NOMBRE",
                5: "SERVICE",
                20: "Delivery Manager",
            },
        ),
        "DataRevenue": sheet(
            5,
            row(5, c1="Grupo Posadás", c4="GPO.007"),
            row(5, c1="(No value)", c4="TBD"),
            header={1: "Cliente", 4: "Project ID"},
        ),
        "Bandas/rol": sheet(
            3,
            row(3, c0="Dóra Quintero", c2="u-1"),
            row(3, c0="Christian Samano", c2="u-2"),
            header={0: "Nombre", 2: "ID Clockify"},
        ),
    }


def test_spellings_of_a_client_become_one_client_with_aliases():
    result = catalogs.build_catalogs(sample_sheets())
    assert Client.objects.count() == 2
    posadas = Client.objects.get(key="grupo posadas")
    assert posadas.name == "Grupo Posadas"
    alias = ClientAlias.objects.get(key="grupo posadas")
    assert set(alias.spellings) == {
        "Grupo Posadas",
        "grupo posadas",
        "Grupo Posadás",
    }
    assert result.merged_clients and "Grupo Posadas" in result.merged_clients[0]


def test_persons_join_the_clockify_id_from_the_roster_and_the_time_entries():
    ClockifyTimeEntry.objects.create(
        entry_id="e1",
        project_id="p",
        user_id="u-9",
        user_name="Ana Ruiz",
        start="",
        end="",
        entry_date=None,
        month="2026-09-01",
        duration_seconds=1,
    )
    catalogs.build_catalogs(sample_sheets())
    dora = Person.objects.get(key="dora quintero")
    assert dora.clockify_user_id == "u-1"
    assert set(dora.roles) == {"delivery_manager", "recurso"}
    assert Person.objects.get(key="ana ruiz").clockify_user_id == "u-9"
    assert PersonAlias.objects.get(key="dora quintero").spellings == [
        "Dora Quintero",
        "Dóra Quintero",
    ]


def test_projects_have_one_row_with_base_client_and_manager():
    result = catalogs.build_catalogs(sample_sheets())
    assert set(Project.objects.values_list("internal_id", flat=True)) == {
        "GPO.007",
        "GPO.001_CR",
        "ZUR.B.008_S1",
    }
    project = Project.objects.get(internal_id="GPO.007")
    # El nombre lo fija la primera hoja (Proyectos), no MPB.
    assert (project.name, project.service) == ("MultiProfile", "IxB")
    assert project.client.name == "Grupo Posadas"
    assert project.delivery_manager.name == "Dora Quintero"
    assert project.sources == ["DataRevenue", "MPB", "Proyectos"]
    assert Project.objects.get(internal_id="GPO.001_CR").base_id == "GPO.001"
    assert (
        Project.objects.get(internal_id="ZUR.B.008_S1").base_id == "ZUR.B.008"
    )
    assert Project.objects.get(internal_id="GPO.001_CR").spellings == [
        "GPO.001_ CR"
    ]
    # «TBD» no es un ID de proyecto.
    assert result.skipped_ids == 1


def test_base_id_strips_every_variant_suffix():
    assert catalogs.base_project_id("AMK.008_S2") == "AMK.008"
    assert catalogs.base_project_id("AIN.002_CR1") == "AIN.002"
    assert catalogs.base_project_id("ABC.001_S1_QA") == "ABC.001"
    assert catalogs.base_project_id("ROC.AIN.001") == "ROC.AIN.001"


def test_a_manual_alias_survives_the_next_build():
    sheets = sample_sheets()
    sheets["Proyectos"].append(row(11, c0="GPO.020", c2="GNP"))
    catalogs.build_catalogs(sheets)
    posadas = Client.objects.get(key="grupo posadas")
    # Alguien decide que GNP es lo mismo que Grupo Posadas.
    alias = ClientAlias.objects.get(key="gnp")
    alias.client, alias.manual = posadas, True
    alias.save()
    catalogs.build_catalogs(sheets)
    assert ClientAlias.objects.get(key="gnp").client == posadas
    assert not Client.objects.filter(key="gnp").exists()
    assert Project.objects.get(internal_id="GPO.020").client == posadas


def test_names_that_disappear_from_the_sheets_leave_the_catalog():
    sheets = sample_sheets()
    catalogs.build_catalogs(sheets)
    sheets["MPB"] = sheet(21, header={1: "CLIENTE", 2: "ID"})
    catalogs.build_catalogs(sheets)
    assert not Client.objects.filter(key="zurich brasil").exists()
    assert not Project.objects.filter(internal_id="ZUR.B.008_S1").exists()


def test_a_sheet_whose_column_moved_is_skipped_with_a_warning():
    sheets = sample_sheets()
    sheets["DataRevenue"][0][1] = "Otra cosa"
    result = catalogs.build_catalogs(sheets)
    assert any("DataRevenue" in w and "«Cliente»" in w for w in result.warnings)
    # No se leyo la columna equivocada: el ID de esa hoja si se ignora.
    assert not Project.objects.filter(internal_id="TBD").exists()
