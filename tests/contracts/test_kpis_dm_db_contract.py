"""Contrato de KPIs de DM leído de las tablas guardadas, y su paquete de datos.

A diferencia de `test_kpis_dm_contract.py` (lecturas simuladas), aquí la API
lee filas reales de `DmKpiPeriod`, `DmKpiObservation` y `DmKpiMetric`. El mismo
escenario sale como paquete de exportación (`kpis_dm_db/export/`): Genesis lo
importa y debe devolver estas mismas respuestas.

Se reescribe solo a propósito: `UPDATE_CONTRACTS=1 pytest tests/contracts`.
"""

import json
import os
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from apps.datastore.models import (
    DmKpiMetric,
    DmKpiObservation,
    DmKpiPeriod,
    EvaExtraction,
)
from apps.datastore.services.genesis_export import export_tables, resolve_models
from apps.portal.services.kpi_dm_store import closing_day

pytestmark = pytest.mark.django_db

URL = "/api/v1/screens/kpis-dm/"
CARPETA = Path(__file__).parent / "kpis_dm_db"
PAQUETE = CARPETA / "export"
HOY = date(2026, 10, 28)
MOMENTO = datetime(2026, 10, 28, 18, 0, tzinfo=UTC)
FUENTE = {"engine": "contrato", "app": "dashboard-management"}
MANAGERS = ("Ana", "Beto", "Carla Díaz")

CASOS = {
    "anio_por_omision": {},
    "mes_cerrado": {"mes": "2026-09"},
    "mes_sin_captura": {"mes": "2026-03"},
    "corte_exacto_sin_dato": {"corte": "2026-02-15"},
    "con_dm": {"dm": ["Ana", "Carla Díaz"]},
    "anio_anterior_vacio": {"history_year": "2025", "chart_year": "2025"},
}


def instante(mes: int, dia: int = 1) -> datetime:
    return datetime(2026, mes, dia, 12, 0, tzinfo=UTC)


def conteos(mes: int, indice: int) -> dict[str, int]:
    total = 3 + indice + mes % 3
    tarde = (mes + indice) % 3
    sin_dato = 1 if (mes == 7 and indice == 2) else 0
    return {
        "total": total,
        "on_time": total - tarde - sin_dato,
        "late": tarde,
        "time_unknown": sin_dato,
        "over_budget": (mes + indice) % 2,
        "cost_unknown": 1 if (mes == 9 and indice == 0) else 0,
    }


@pytest.fixture
def escenario(monkeypatch):
    monkeypatch.setattr("django.utils.timezone.localdate", lambda *a: HOY)
    extraccion = EvaExtraction.objects.create(
        cut=HOY,
        started_at=MOMENTO,
        finished_at=MOMENTO,
        published=True,
        metrics={"proyectos": 12},
    )
    for mes in range(1, 11):
        if mes == 3:
            continue
        cierre = closing_day(date(2026, mes, 1))
        periodo = DmKpiPeriod.objects.create(
            month=date(2026, mes, 1),
            closing_day=cierre,
            status="open"
            if mes == 10
            else ("pending" if mes == 6 else "closed"),
            closed_at=None if mes >= 10 else instante(mes, 28),
        )
        if mes == 6:
            continue
        observacion = DmKpiObservation.objects.create(
            period=periodo,
            cut=HOY if mes == 10 else cierre,
            source=extraccion if mes == 10 else None,
            source_observed_at=instante(mes, 28),
            issues=["Horas pendientes"] if mes == 8 else [],
        )
        periodo.latest_observation = observacion
        periodo.save()
        if mes == 5:
            continue
        for indice, nombre in enumerate(MANAGERS):
            DmKpiMetric.objects.create(
                observation=observacion,
                manager=nombre,
                slug=nombre.lower().replace(" ", "-").replace("í", "i"),
                **conteos(mes, indice),
            )
    DmKpiPeriod.objects.update(updated_at=MOMENTO)
    DmKpiObservation.objects.update(captured_at=MOMENTO)


def normalizar(cuerpo: object) -> object:
    texto = json.dumps(cuerpo, sort_keys=True, ensure_ascii=False)
    return json.loads(texto)


def guardar_o_leer(ruta: Path, actual: object) -> object:
    if os.environ.get("UPDATE_CONTRACTS") == "1":
        ruta.parent.mkdir(parents=True, exist_ok=True)
        texto = json.dumps(actual, sort_keys=True, ensure_ascii=False, indent=2)
        ruta.write_text(texto + "\n", encoding="utf-8", newline="\n")
    assert ruta.exists(), (
        f"Falta {ruta.name}: corre con UPDATE_CONTRACTS=1 y revisa el cambio"
    )
    return json.loads(ruta.read_text(encoding="utf-8"))


@pytest.mark.parametrize("nombre", CASOS)
def test_la_api_leida_de_las_tablas_coincide_con_el_contrato(
    client, escenario, nombre
):
    respuesta = client.get(URL, CASOS[nombre])
    assert respuesta.status_code == 200

    actual = normalizar(respuesta.json())

    assert actual == guardar_o_leer(CARPETA / f"{nombre}.json", actual)


def test_el_paquete_de_exportacion_del_escenario_no_cambia(tmp_path, escenario):
    destino = tmp_path / "export"
    manifiesto = export_tables(
        resolve_models(["kpi"], []),
        destino,
        created_at=MOMENTO,
        source=FUENTE,
    )

    if os.environ.get("UPDATE_CONTRACTS") == "1":
        PAQUETE.mkdir(parents=True, exist_ok=True)
        for archivo in destino.iterdir():
            contenido = archivo.read_bytes()
            (PAQUETE / archivo.name).write_bytes(contenido)
    guardado = json.loads((PAQUETE / "manifest.json").read_text("utf-8"))

    assert manifiesto == guardado
    for tabla in manifiesto["tables"]:
        esperado = (PAQUETE / tabla["file"]).read_bytes()
        assert (destino / tabla["file"]).read_bytes() == esperado
