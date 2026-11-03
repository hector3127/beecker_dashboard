"""Contrato del motor GSE (horas del mes por área, persona y categoría).

Bandas/rol y CatalagoProyectos salen de `SheetSnapshot` y las horas de
`ClockifyTimeEntry`, como en producción con las dos banderas de almacén
activas. El mismo escenario sale como paquete de exportación
(`gse_db/export/`): Genesis lo importa y debe devolver estos cuerpos.

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
from apps.gse.services.base_store import build_base_store, build_connection
from apps.gse.services.clockify_month import MonthReportLoader
from apps.gse.services.month_report import GseContext, get_month
from core.exceptions import SheetNotFoundError
from core.sheets import store_read_cache

pytestmark = pytest.mark.django_db

CARPETA = Path(__file__).parent / "gse_db"
PAQUETE = CARPETA / "export"
MOMENTO = datetime(2026, 10, 14, 17, 0, tzinfo=UTC)
FUENTE = {"engine": "contrato", "app": "dashboard-management"}
TABLAS = [
    "datastore.SheetSnapshot",
    "datastore.ClockifyMonthSync",
    "datastore.ClockifyTimeEntry",
]
ESPACIO = "ws-contrato"
BANDAS = [
    ["Plantilla de la empresa", "", "", "", ""],
    ["Nombre", "ROL", "ID Clockify", "septiembre 2026", "octubre 2026"],
    ["Ana Ruiz", "Desarrollo", "u1", "B2", "B3"],
    ["Beto Soto", "Desarrollo", "u2", "B1", "BAJA"],
    ["Carla Díaz", "QA", "u3", "B2", "B2"],
    ["Dani Paz", "QA", "", "B1", "B1"],
    ["Ana Ruiz", "QA", "u9", "B9", "B9"],
    ["", "QA", "u8", "B8", "B8"],
]
CATALOGO = [
    ["", "Operación", "Tipo", "ID_Proyecto", "", "", "", "", "Servicio"],
    ["", "Desarrollo", "Facturable", "AER.ACM.001", "", "", "", "", "AER"],
    [
        "",
        "Desarrollo",
        "Facturable",
        "AER.ACM.001_S1",
        "",
        "",
        "",
        "",
        "Sprint",
    ],
    ["", "Optimización", "No facturable", "INT.OPT.001", "", "", "", "", ""],
    ["", "Laboratorio", "No facturable", "INT.LAB.001", "", "", "", "", "Lab"],
    ["", "Agentes Autónomos", "Interno", "INT.AGE.001", "", "", "", "", ""],
    ["", "Desarrollo", "Facturable", "AER.ACM.001", "", "", "", "", ""],
]
HOJAS = {"Bandas/rol": 1, "CatalagoProyectos": 2}
REGISTROS = [
    (
        "u1",
        "Ana Ruiz",
        "AER.ACM.001",
        "Sprint 1 _S1",
        ["Desarrollo"],
        8,
        "2026-10-02",
    ),
    (
        "u1",
        "Ana Ruiz",
        "AER.ACM.001",
        "Mantenimiento",
        ["Desarrollo"],
        4,
        "2026-10-05",
    ),
    (
        "u1",
        "Ana Ruiz",
        "INT.OPT.001",
        "Mejora",
        ["INV_OPERATIVA"],
        3,
        "2026-10-06",
    ),
    (
        "u1",
        "Ana Ruiz",
        "INT.OPT.001",
        "Mejora",
        ["Desarrollo"],
        0,
        "2026-10-06",
    ),
    ("u2", "Beto Soto", "000.ADMIN", "Reuniones", [], 5, "2026-10-07"),
    ("u2", "Beto Soto", "Vacaciones", "Descanso", [], 8, "2026-10-08"),
    (
        "u3",
        "Carla Díaz",
        "INT.LAB.001",
        "Pruebas",
        ["Laboratorio"],
        6,
        "2026-10-09",
    ),
    (
        "u3",
        "Carla Díaz",
        "Administrative Activities",
        "Papeleo",
        ["INV_COMERCIAL", "Desarrollo"],
        1.5,
        "2026-10-12",
    ),
    (
        "u4",
        "Dani Paz",
        "AER.ACM.001",
        "Soporte _CR1",
        ["Desarrollo"],
        3.25,
        "2026-10-13",
    ),
    (
        "u4",
        "Dani Paz",
        "Cliente nuevo",
        "Pre venta",
        ["Pre-Venta"],
        2,
        "2026-10-14",
    ),
    ("ux", "Zed Extraño", "AER.ACM.001", "Soporte", [], 2, "2026-10-15"),
    ("u1", "Ana Ruiz", "AER.ACM.001", "Sprint 1 _S1", [], 6, "2026-09-03"),
    (
        "u3",
        "Carla Díaz",
        "INT.OPT.001",
        "Mejora",
        ["Desarrollo"],
        4,
        "2026-09-10",
    ),
    ("ux", "Zed Extraño", "AER.ACM.001", "Soporte", [], 1, "2026-08-04"),
    ("u1", "Ana Ruiz", "INT.AGE.001", "Agente", [], 2.5, "2026-11-02"),
]
MESES_SINCRONIZADOS = (8, 9, 10, 11)


class Lector:
    def read_values(self, nombre):
        filas = store_read_cache.read_snapshot(nombre)
        if not isinstance(filas, list):
            raise SheetNotFoundError(f"No existe la hoja {nombre}.")
        return [list(f) for f in filas]

    def sheet_exists(self, nombre):
        return nombre in self.list_sheet_names()

    def list_sheet_names(self):
        ids = store_read_cache.read_snapshot(store_read_cache.SHEET_IDS_NAME)
        return list(ids) if isinstance(ids, dict) else []

    def prefetch(self, nombres):
        return None


def guardar_hoja(nombre, filas):
    SheetSnapshot.objects.update_or_create(
        name=nombre,
        defaults={
            "rows": filas,
            "row_count": len(filas) if isinstance(filas, list) else 0,
            "synced_at": MOMENTO,
        },
    )


@pytest.fixture
def escenario(monkeypatch, settings):
    settings.SHEETS_STORE_ENABLED = True
    settings.CLOCKIFY_STORE_ENABLED = True
    settings.CLOCKIFY_API_KEY = "contrato"
    settings.CLOCKIFY_WORKSPACE_ID = ESPACIO
    cache.clear()
    store_read_cache._memory.clear()
    guardar_hoja("Bandas/rol", BANDAS)
    guardar_hoja("CatalagoProyectos", CATALOGO)
    guardar_hoja(store_read_cache.SHEET_IDS_NAME, HOJAS)
    for mes in MESES_SINCRONIZADOS:
        corrida = SyncRun.objects.create(kind="daily", status="ok")
        ClockifyMonthSync.objects.create(
            month=date(2026, mes, 1),
            entries_count=1,
            total_seconds=1,
            synced_at=MOMENTO,
            run_id=corrida.pk,
        )
    for indice, (
        usuario,
        nombre,
        proyecto,
        tarea,
        etiquetas,
        horas,
        dia,
    ) in enumerate(REGISTROS, 1):
        fecha = date.fromisoformat(dia)
        ClockifyTimeEntry.objects.create(
            entry_id=f"e{indice:03d}",
            project_id=f"p-{indice}",
            project_name=proyecto,
            task_name=tarea,
            user_id=usuario,
            user_name=nombre,
            tags=etiquetas,
            billable=True,
            start=f"{dia}T15:00:00Z",
            end=f"{dia}T16:00:00Z",
            entry_date=fecha,
            month=fecha.replace(day=1),
            duration_seconds=int(horas * 3600),
        )


def contexto() -> GseContext:
    lector = Lector()
    conexion = build_connection("contrato", ESPACIO)
    almacen = build_base_store(lector, conexion, MOMENTO)
    cargador = MonthReportLoader(
        ("contrato", ESPACIO, "America/Mexico_City"),
        (almacen, conexion, cache),
        persist=None,
    )
    return GseContext(lector, almacen, cargador)


def mes(valor, fuente="api", area=""):
    return get_month(contexto(), (valor, fuente, False, area))


def quitar_catalogo():
    SheetSnapshot.objects.filter(name="CatalagoProyectos").delete()
    guardar_hoja(store_read_cache.SHEET_IDS_NAME, {"Bandas/rol": 1})
    store_read_cache._memory.clear()


def cuerpo() -> dict:
    casos = {
        "api_octubre": mes("2026-10"),
        "hoja_octubre": mes("2026-10", "sheet"),
        "area_qa": mes("2026-10", area="QA"),
        "area_desarrollo_por_ids": mes("2026-10", area="Desarrollo"),
        "septiembre": mes("2026-09"),
        "agosto_sin_coincidencias": mes("2026-08"),
        "noviembre_sin_columna_de_banda": mes("2026-11"),
        "julio_sin_base": mes("2026-07", "sheet"),
        "mes_invalido": mes("2026-13"),
        "mes_no_texto": mes(None),
        "area_inexistente": mes("2026-10", area="Nada"),
    }
    quitar_catalogo()
    casos["sin_catalogo"] = mes("2026-10")
    return casos


def normalizar(valor: object) -> object:
    return json.loads(json.dumps(valor, sort_keys=True, ensure_ascii=False))


def guardar_o_leer(ruta: Path, actual: object) -> object:
    if os.environ.get("UPDATE_CONTRACTS") == "1":
        ruta.parent.mkdir(parents=True, exist_ok=True)
        texto = json.dumps(actual, sort_keys=True, ensure_ascii=False, indent=2)
        ruta.write_text(texto + "\n", encoding="utf-8", newline="\n")
    assert ruta.exists(), (
        f"Falta {ruta.name}: corre con UPDATE_CONTRACTS=1 y revisa el cambio"
    )
    return json.loads(ruta.read_text(encoding="utf-8"))


def test_gse_leido_de_las_tablas_coincide_con_el_contrato(escenario):
    actual = normalizar(cuerpo())

    assert actual == guardar_o_leer(CARPETA / "meses.json", actual)


def test_el_escenario_cubre_las_ramas_del_motor(escenario):
    casos = cuerpo()

    octubre = casos["api_octubre"]
    assert octubre["ok"] is True
    assert octubre["banda"] == "octubre 2026"
    assert octubre["filtradoPorIDs"] is False
    assert octubre["sinArea"] == ["Zed Extraño"]
    assert "000.ADMIN" in octubre["sinCatalogo"]
    assert {a["area"] for a in octubre["areas"]} == {"Desarrollo", "QA"}
    assert casos["area_desarrollo_por_ids"]["filtradoPorIDs"] is True
    assert casos["noviembre_sin_columna_de_banda"]["banda"] is None
    assert casos["sin_catalogo"]["catalogoAviso"]
    assert all(
        casos[nombre]["ok"] is False
        for nombre in (
            "agosto_sin_coincidencias",
            "julio_sin_base",
            "mes_invalido",
            "mes_no_texto",
            "area_inexistente",
        )
    )


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
