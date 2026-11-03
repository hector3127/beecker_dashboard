"""Contrato de EVA-04 leído de las hojas y las horas guardadas.

ROC sale de `SheetSnapshot` y las horas de `ClockifyTimeEntry`, como en
producción con las dos banderas de almacén activas. El mismo escenario sale
como paquete de exportación (`eva4_db/export/`): Genesis lo importa y debe
devolver estos mismos cuerpos.

Se reescribe solo a propósito: `UPDATE_CONTRACTS=1 pytest tests/contracts`.
"""

import json
import os
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from django.core.cache import cache

from apps.datastore.models import (
    ClockifyMonthSync,
    ClockifyTimeEntry,
    SheetSnapshot,
    SyncRun,
)
from apps.datastore.services.genesis_export import export_tables, resolve_models
from apps.portal.api.serializers import eva4_screen
from apps.portal.services import eva4
from core.exceptions import SheetNotFoundError
from core.sheets import store_read_cache
from tests.portal.test_eva4 import HEADER

pytestmark = pytest.mark.django_db

CARPETA = Path(__file__).parent / "eva4_db"
PAQUETE = CARPETA / "export"
HOY = date(2026, 10, 14)
MOMENTO = datetime(2026, 10, 14, 17, 0, tzinfo=UTC)
FUENTE = {"engine": "contrato", "app": "dashboard-management"}
TABLAS = [
    "datastore.SheetSnapshot",
    "datastore.ClockifyMonthSync",
    "datastore.ClockifyTimeEntry",
]
HOJAS = ["ROC", "MPB", "08.Base Clockify 2026", "Proyectos"]
CASOS = {
    "mes_actual": None,
    "mes_anterior": "2026-09",
    "mes_sin_horas": "2026-03",
}


def proceso(
    cliente, pais, roc, bot, servicio, estado, nombre, dm, am, inicio, fin
) -> list:
    return [
        cliente,
        pais,
        roc,
        bot,
        servicio,
        estado,
        nombre,
        dm,
        am,
        inicio,
        fin,
        0,
        "Riesgo",
    ]


ROC = [
    HEADER,
    proceso(
        "Nestlé",
        "MEX",
        "ROC.NSC.001",
        "1058",
        "ROC",
        "Activo",
        "1058 - Reporte KE30",
        "Ana",
        "Beto",
        "2026-01-01",
        "2026-10-20",
    ),
    proceso(
        "Nestlé",
        "MEX",
        "ROC.NSC.001",
        "1059",
        "ROC",
        "Activo",
        "1059 - Conciliación",
        "Ana",
        "Beto",
        "2026-01-01",
        "2026-12-15",
    ),
    proceso(
        "Nestlé",
        "COL",
        "ROC.NSC.002",
        "2001",
        "SAAS",
        "Suspendido",
        "2001 - Facturas",
        "Ana",
        "Beto",
        "2026-02-01",
        "2026-11-30",
    ),
    proceso(
        "Cagsa",
        "MEX",
        "SAAS.CAG.001",
        "77",
        "SAAS",
        "Activo",
        "77 - Pedidos",
        "Carla Díaz",
        "Beto",
        "2026-03-01",
        "2027-03-01",
    ),
    proceso(
        "Cagsa",
        "MEX",
        "RAAS.CAG.002",
        "78",
        "RAAS",
        "Activo",
        "78 - Soporte",
        "Carla Díaz",
        "Ana",
        "2026-03-01",
        "2026-12-31",
    ),
    proceso(
        "Cagsa",
        "MEX",
        "AER.CAG.003",
        "79",
        "AER",
        "Activo",
        "79 - Evaluación",
        "Carla Díaz",
        "Ana",
        "2026-03-01",
        "2026-12-31",
    ),
    proceso(
        "Delta",
        "MEX",
        "ROC.DEL.001",
        "5",
        "T&M",
        "Activo",
        "5 - Soporte T&M",
        "Ana",
        "Beto",
        "2026-05-01",
        "2026-11-05",
    ),
    proceso(
        "Delta",
        "MEX",
        "",
        "6",
        "ROC",
        "Activo",
        "6 - Sin ROC ID",
        "Ana",
        "Beto",
        "2026-05-01",
        "2026-11-05",
    ),
    proceso(
        "Delta",
        "MEX",
        "ROC.DEL.001",
        "5",
        "ROC",
        "Activo",
        "5 - Bot compartido",
        "Ana",
        "Beto",
        "2026-05-01",
        "2026-11-25",
    ),
    proceso(
        "Epsilon",
        "MEX",
        "ROC.EPS.001",
        "9",
        "ROC",
        "Cerrado",
        "9 - Cerrado",
        "Ana",
        "Beto",
        "2026-01-01",
        "2026-06-01",
    ),
    proceso("Total", "", "", "", "", "Activo", "", "", "", "", ""),
]
HORAS = [
    (
        "ROC.NSC.001",
        "1058 - Reporte KE30",
        ["Monitoreo"],
        date(2026, 10, 2),
        3 * 3600 + 1800,
    ),
    (
        "ROC.NSC.001",
        "1058 - Reporte KE30",
        ["Ajustes L1"],
        date(2026, 10, 5),
        2 * 3600,
    ),
    (
        "ROC.NSC.001",
        "1058 - Reporte KE30",
        ["Change Request"],
        date(2026, 10, 6),
        4 * 3600,
    ),
    (
        "ROC.NSC.001",
        "1059 - Conciliación",
        ["Monitoreo"],
        date(2026, 10, 7),
        5400,
    ),
    ("ROC.NSC.002", "2001 - Facturas", ["Monitoreo"], date(2026, 10, 8), 3600),
    (
        "SAAS.CAG.001",
        "77 - Pedidos",
        ["Sesión con cliente"],
        date(2026, 10, 9),
        7200,
    ),
    (
        "RAAS.CAG.002",
        "78 - Soporte",
        ["Monitoreo"],
        date(2026, 9, 21),
        3 * 3600,
    ),
    ("RAAS.CAG.002", "78 - Soporte", ["Hora Extra"], date(2026, 9, 22), 3600),
    (
        "RAAS.CAG.002",
        "78 - Soporte",
        ["Monitoreo"],
        date(2026, 10, 12),
        6 * 3600,
    ),
    (
        "ROC.DEL.001",
        "5 - Soporte T&M",
        ["Atención a cliente"],
        date(2026, 10, 13),
        2 * 3600,
    ),
    ("OTRO.001", "6 - Sin ROC ID", ["Monitoreo"], date(2026, 10, 13), 3600),
]


class Lector:
    def read_values(self, nombre):
        filas = store_read_cache.read_snapshot(nombre)
        if not isinstance(filas, list):
            raise SheetNotFoundError(f"No existe la hoja {nombre}.")
        return [list(fila) for fila in filas]

    def sheet_exists(self, nombre):
        ids = store_read_cache.read_snapshot(store_read_cache.SHEET_IDS_NAME)
        return isinstance(ids, dict) and nombre in ids

    def prefetch(self, nombres):
        return None


@pytest.fixture
def escenario(monkeypatch, settings):
    settings.SHEETS_STORE_ENABLED = True
    settings.CLOCKIFY_STORE_ENABLED = True
    settings.GOOGLE_SPREADSHEET_ID = "contrato"
    cache.clear()
    store_read_cache._memory.clear()
    monkeypatch.setattr("django.utils.timezone.localdate", lambda *a: HOY)
    monkeypatch.setattr(
        "django.utils.timezone.localtime",
        lambda value=None, timezone=None: MOMENTO if value is None else value,
    )
    monkeypatch.setattr(eva4, "build_sheet_repository", Lector)
    for nombre, filas in (
        ("ROC", ROC),
        ("MPB", [["Cliente"]]),
        ("Proyectos", [["ID"]]),
        (
            store_read_cache.SHEET_IDS_NAME,
            {n: i for i, n in enumerate(HOJAS, 1)},
        ),
    ):
        SheetSnapshot.objects.create(
            name=nombre,
            rows=filas,
            row_count=len(filas) if isinstance(filas, list) else 0,
            synced_at=MOMENTO,
        )
    for mes in (date(2026, 9, 1), date(2026, 10, 1)):
        corrida = SyncRun.objects.create(kind="daily", status="ok")
        ClockifyMonthSync.objects.create(
            month=mes,
            entries_count=1,
            total_seconds=3600,
            synced_at=MOMENTO,
            run_id=corrida.pk,
        )
    for indice, (proyecto, tarea, etiquetas, dia, segundos) in enumerate(
        HORAS, 1
    ):
        ClockifyTimeEntry.objects.create(
            entry_id=f"e{indice:03d}",
            project_id=f"p-{proyecto.lower()}",
            project_name=proyecto,
            task_name=tarea,
            tags=etiquetas,
            billable=True,
            start=f"{dia.isoformat()}T15:00:00Z",
            end=f"{dia.isoformat()}T16:00:00Z",
            entry_date=dia,
            month=dia.replace(day=1),
            duration_seconds=segundos,
        )


def normalizar(cuerpo: object) -> object:
    return json.loads(json.dumps(cuerpo, sort_keys=True, ensure_ascii=False))


def guardar_o_leer(ruta: Path, actual: object) -> object:
    if os.environ.get("UPDATE_CONTRACTS") == "1":
        ruta.parent.mkdir(parents=True, exist_ok=True)
        texto = json.dumps(actual, sort_keys=True, ensure_ascii=False, indent=2)
        ruta.write_text(texto + "\n", encoding="utf-8", newline="\n")
    assert ruta.exists(), (
        f"Falta {ruta.name}: corre con UPDATE_CONTRACTS=1 y revisa el cambio"
    )
    return json.loads(ruta.read_text(encoding="utf-8"))


@pytest.mark.parametrize("nombre", list(CASOS))
def test_eva4_leido_de_las_tablas_coincide_con_el_contrato(escenario, nombre):
    mes = CASOS[nombre]

    actual = normalizar(
        eva4_screen(eva4.load_eva4(mes) if mes else eva4.load_eva4())
    )

    assert actual == guardar_o_leer(CARPETA / f"{nombre}.json", actual)


def test_el_escenario_cuenta_solo_procesos_activos_o_suspendidos_sin_aer(
    escenario,
):
    informe = eva4.load_eva4()

    assert informe["available"] is True
    assert informe["total"] == 8
    assert informe["active"] == 7
    assert informe["suspended"] == 1


def test_el_paquete_de_exportacion_del_escenario_no_cambia(tmp_path, escenario):
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
