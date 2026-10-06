"""Valores esperados obtenidos al ejecutar el obtenerResumenIXBRaaS()
original con los mismos datos de ixb_sample_data.py."""

from apps.azure_devops.services.azure_client import flatten_iterations
from apps.clockify.exceptions import ClockifyProjectError
from apps.ejecutivo.services.ixb_rules import (
    calculate_exact_burn,
    extract_nomenclature,
    sort_project_ids,
)
from apps.ejecutivo.services.ixb_summary import IxbSources, build_ixb_summary
from apps.ejecutivo.services.project_milestones import (
    calculate_project_milestones,
)
from tests.ejecutivo.ixb_sample_data import (
    AZURE_PROJECTS,
    CLOCKIFY_ENTRIES,
    HISTORY_ROWS,
    ITERATION_TREES,
    NOW,
    PROJECT_ROWS,
    WORK_ITEMS,
)


class FakeAzure:
    def __init__(self):
        self.prefetched = []

    def prefetch(self, project_names, include_iterations):
        self.prefetched.append((list(project_names), include_iterations))

    def list_project_names(self):
        return AZURE_PROJECTS

    def list_iterations(self, project_name):
        iterations = []
        flatten_iterations(ITERATION_TREES[project_name], "", iterations)
        return iterations

    def list_work_items(self, project_name):
        return WORK_ITEMS.get(project_name, [])


def load_entries(project_id):
    if project_id not in CLOCKIFY_ENTRIES:
        raise ClockifyProjectError("Sin coincidencia en Clockify.")
    return CLOCKIFY_ENTRIES[project_id]


def build_summary(azure=None):
    sources = IxbSources(
        project_rows=PROJECT_ROWS,
        history_rows=HISTORY_ROWS,
        load_project_entries=load_entries,
        azure=azure,
    )
    return build_ixb_summary(sources, NOW)


def rows_by_id(summary):
    return {row["idProyecto"]: row for row in summary["filas"]}


def test_sort_project_ids_prefers_specific_nomenclature():
    # Mismo resultado que _altoNivelIdPreferidoIXB() del original.
    assert (
        sort_project_ids(["A.1", "A.1_S2", "A.1_S10", "A.1_CR"])[0] == "A.1_CR"
    )
    assert sort_project_ids(["A.1", "A.1_S2", "A.1_S10"])[0] == "A.1_S10"


def test_extract_nomenclature():
    assert extract_nomenclature("Desarrollo CR1") == "CR1"
    assert extract_nomenclature("s2") == "S2"
    assert extract_nomenclature("S10x") == ""
    assert extract_nomenclature("General") == ""


def test_exact_burn_filters_nomenclature_and_duplicates():
    assert (
        calculate_exact_burn(CLOCKIFY_ENTRIES["RAS.001_CR1"], "RAS.001_CR1")
        == 15.5
    )


def test_milestones_mark_phase_in_progress():
    milestones = calculate_project_milestones(HISTORY_ROWS, "SAS.004", NOW)

    assert [item["estado"] for item in milestones.milestones] == [
        "Completado",
        "En curso",
    ]
    assert milestones.full_history[-1]["enCurso"] is True
    assert milestones.delivery_manager == "Ana"


def test_ixb_summary_matches_original():
    summary = build_summary(FakeAzure())
    rows = rows_by_id(summary)

    assert list(rows) == ["SAS.004", "RAS.001_CR1", "IXB.002_S2"]

    cr_row = rows["RAS.001_CR1"]
    assert cr_row["deliveryManager"] == "Laura"
    assert cr_row["budget"] == 40
    assert cr_row["burn"] == 15.5
    assert cr_row["avance"] == 38.8
    assert cr_row["status"] == "Development / Deployment"
    assert cr_row["proyectoAzure"] == "RAS.001"
    assert cr_row["fechaInicio"] == "2026-08-01T00:00:00.000Z"
    assert cr_row["fechaFin"] == "2026-11-30T00:00:00.000Z"
    assert cr_row["desviacionDias"] == 58
    assert cr_row["wi"]["general"] == {
        "total": 7,
        "cerrados": 3,
        "pendientes": 4,
    }
    assert cr_row["wi"]["development"] == {
        "total": 1,
        "cerrados": 0,
        "pendientes": 1,
    }
    assert cr_row["wi"]["deployment"]["total"] == 1
    assert cr_row["etapas"] == {
        "discovery": {"cerrada": True},
        "development": {"cerrada": False},
        "deployment": {"cerrada": False},
    }
    assert cr_row["riesgos"] == ["Riesgo abierto"]

    s2_row = rows["IXB.002_S2"]
    assert s2_row["status"] == "Suspendido"
    assert s2_row["deliveryManager"] == "Mario"
    assert s2_row["burn"] == 70
    assert s2_row["etc"] == -10

    saas_row = rows["SAS.004"]
    assert saas_row["status"] == "Development"
    assert saas_row["nombre"] == "SAS.004"
    assert saas_row["cliente"] == "Umbrella"
    assert saas_row["burn"] == 0
    assert saas_row["proyectoAzure"] == ""


def test_ixb_pivots():
    summary = build_summary(FakeAzure())

    assert summary["pivoteServicio"] == [
        {"deliveryManager": "Ana", "total": 1, "SAAS": 1},
        {"deliveryManager": "Laura", "total": 1, "RAAS": 1},
        {"deliveryManager": "Mario", "total": 1, "IXB": 1},
    ]
    assert summary["pivoteStatus"][0] == {
        "deliveryManager": "Ana",
        "Sus": 0,
        "Dis": 0,
        "Dev": 1,
        "Dep": 0,
        "total": 1,
    }


def test_ixb_summary_prefetches_azure_projects():
    azure = FakeAzure()

    build_summary(azure)

    assert azure.prefetched == [(["RAS.001", "IXB.002_Main", "", ""], True)]


def test_ixb_summary_without_azure():
    summary = build_summary(azure=None)

    assert rows_by_id(summary)["RAS.001_CR1"]["status"] == "Development"
