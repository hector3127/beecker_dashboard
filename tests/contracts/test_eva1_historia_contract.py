"""Contrato de EVA 1 con historia de Azure: cortes pasados desde revisiones.

Sobre el escenario de `test_eva1_contract.py` se agrega un flujo de
revisiones. Con él, el corte de hoy y uno pasado recalculan conteos, riesgos
y estado desde la última revisión de cada work item anterior al fin de ese
día. El paquete (`eva1_db/export_historia/`) incluye el flujo y sus
revisiones: Genesis lo importa y debe devolver estos mismos cuerpos.

Se reescribe solo a propósito: `UPDATE_CONTRACTS=1 pytest tests/contracts`.
"""

import json
import os
from datetime import UTC, date, datetime

import pytest

from apps.datastore.models import AzureHistoryFeed, AzureWorkItemRevision
from apps.datastore.services.genesis_export import export_tables, resolve_models
from apps.portal.api.plain import plain
from apps.portal.services.azure_history import feed_identity
from apps.portal.services.eva1_screen import build_eva1_screen
from tests.contracts.test_eva1_contract import (  # noqa: F401
    CARPETA,
    FUENTE,
    HOY,
    MOMENTO,
    escenario,
    guardar_o_leer,
    normalizar,
)

pytestmark = pytest.mark.django_db

PAQUETE = CARPETA / "export_historia"
TABLAS = [
    "datastore.EvaExtraction",
    "datastore.EvaAzureSource",
    "datastore.EvaScopeSnapshot",
    "datastore.AzureHistoryFeed",
    "datastore.AzureWorkItemRevision",
]
CASOS = {
    "historia_corte_anterior": (date(2026, 10, 12), "", ""),
    "historia_hoy": (HOY, "", ""),
    "historia_con_dm": (date(2026, 10, 12), "Beto Soto", ""),
}


def revision(
    feed: AzureHistoryFeed,
    proyecto: str,
    identificador: int,
    numero: int,
    cuando: str,
    tipo: str,
    estado: str,
    titulo: str,
    ruta: str,
    *,
    borrado: bool = False,
) -> None:
    AzureWorkItemRevision.objects.create(
        feed=feed,
        work_item_id=identificador,
        revision=numero,
        project_name=proyecto,
        changed_at=datetime.fromisoformat(cuando).replace(tzinfo=UTC),
        deleted=borrado,
        fields={
            "System.Id": identificador,
            "System.WorkItemType": tipo,
            "System.State": estado,
            "System.Title": titulo,
            "System.IterationPath": ruta,
        },
    )


@pytest.fixture
def historia(escenario, settings):  # noqa: F811
    settings.AZURE_DEVOPS_ORGANIZATION = "org-contrato"
    settings.AZURE_DEVOPS_PAT = "pat-contrato"
    flujo = AzureHistoryFeed.objects.create(
        identity=feed_identity(), complete_through=MOMENTO, updated_at=MOMENTO
    )
    acm = "ACM.001\\General_S1"
    desarrollo = acm + "\\Development_S1"
    descubrimiento = acm + "\\Discovery_S1"
    for datos in (
        (101, 1, "2026-08-17T15:00:00", "Epic", "Active", "General_S1", acm),
        (
            102,
            1,
            "2026-08-17T15:00:00",
            "Epic",
            "Active",
            "Discovery_S1",
            descubrimiento,
        ),
        (
            102,
            2,
            "2026-08-28T15:00:00",
            "Epic",
            "Closed",
            "Discovery_S1",
            descubrimiento,
        ),
        (
            103,
            1,
            "2026-08-31T15:00:00",
            "Epic",
            "Active",
            "Development_S1",
            desarrollo,
        ),
        (
            104,
            1,
            "2026-08-18T15:00:00",
            "Task",
            "Active",
            "Tarea 1",
            descubrimiento,
        ),
        (
            104,
            2,
            "2026-10-20T15:00:00",
            "Task",
            "Closed",
            "Tarea 1",
            descubrimiento,
        ),
        (
            105,
            1,
            "2026-09-01T15:00:00",
            "Task",
            "Active",
            "Tarea 2",
            desarrollo,
        ),
        (
            106,
            1,
            "2026-10-01T15:00:00",
            "Risk",
            "Active",
            "Riesgo de datos",
            acm,
        ),
        (
            106,
            2,
            "2026-10-25T15:00:00",
            "Risk",
            "Closed",
            "Riesgo de datos",
            acm,
        ),
        (
            107,
            1,
            "2026-09-01T15:00:00",
            "Task",
            "Active",
            "Tarea borrada",
            desarrollo,
        ),
    ):
        revision(flujo, "ACM.001", *datos)
    revision(
        flujo,
        "ACM.001",
        107,
        2,
        "2026-10-10T15:00:00",
        "Task",
        "Active",
        "Tarea borrada",
        desarrollo,
        borrado=True,
    )
    cr = "ACM.001\\General_CR1"
    revision(
        flujo,
        "ACM.001",
        201,
        1,
        "2026-10-01T15:00:00",
        "Epic",
        "Active",
        "General_CR1",
        cr,
    )
    revision(
        flujo,
        "ACM.001",
        202,
        1,
        "2026-10-05T15:00:00",
        "Task",
        "Active",
        "Tarea CR",
        cr + "\\Development_CR1",
    )
    bta = "BTA.002\\General_S1"
    revision(
        flujo,
        "BTA.002",
        301,
        1,
        "2026-10-19T15:00:00",
        "Epic",
        "Suspended",
        "General_S1",
        bta,
    )
    revision(
        flujo,
        "BTA.002",
        302,
        1,
        "2026-10-20T15:00:00",
        "Task",
        "Active",
        "Tarea BTA",
        bta + "\\Discovery_S1",
    )
    return flujo


@pytest.mark.parametrize("nombre", list(CASOS))
def test_eva1_con_historia_coincide_con_el_contrato(historia, nombre):
    corte, dm, servicio = CASOS[nombre]

    actual = normalizar(plain(build_eva1_screen(corte, dm, servicio)))

    assert actual == guardar_o_leer(CARPETA / f"{nombre}.json", actual)


def test_la_historia_cambia_los_conteos_segun_el_dia(historia):
    antes = build_eva1_screen(date(2026, 10, 12), "", "")["eva"]
    hoy = build_eva1_screen(HOY, "", "")["eva"]

    acm_antes = next(p for p in antes.projects if p.project_id == "ACM.001_S1")
    acm_hoy = next(p for p in hoy.projects if p.project_id == "ACM.001_S1")

    assert acm_antes.risks == 1
    assert acm_hoy.risks == 0
    assert acm_antes.stages[0].pending > acm_hoy.stages[0].pending


def test_el_paquete_de_exportacion_con_historia_no_cambia(tmp_path, historia):
    destino = tmp_path / "export"
    manifiesto = export_tables(
        resolve_models([], TABLAS), destino, created_at=MOMENTO, source=FUENTE
    )

    if os.environ.get("UPDATE_CONTRACTS") == "1":
        PAQUETE.mkdir(parents=True, exist_ok=True)
        for archivo in destino.iterdir():
            (PAQUETE / archivo.name).write_bytes(archivo.read_bytes())
    guardado = json.loads((PAQUETE / "manifest.json").read_text("utf-8"))

    assert manifiesto == guardado
    for tabla in manifiesto["tables"]:
        esperado = (PAQUETE / tabla["file"]).read_bytes()
        assert (destino / tabla["file"]).read_bytes() == esperado.replace(
            b"\r\n", b"\n"
        )
