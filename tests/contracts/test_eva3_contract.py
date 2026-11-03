"""Contrato de EVA 3 (AER y T&M) leído de la hoja MPB y las horas guardadas.

MPB sale de `SheetSnapshot`, el catálogo de proyectos de `ClockifyProjectRecord`
y las horas de `ClockifyTimeEntry`, como en producción con las dos banderas de
almacén activas. El mismo escenario sale como paquete de exportación
(`eva3_db/export/`): Genesis lo importa y debe devolver este cuerpo.

Se reescribe solo a propósito: `UPDATE_CONTRACTS=1 pytest tests/contracts`.
"""

import json
import os
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from django.core.cache import cache

from apps.clockify.provider import build_clockify_loader
from apps.datastore.models import (
    ClockifyCatalog,
    ClockifyMonthSync,
    ClockifyProjectRecord,
    ClockifyTimeEntry,
    SheetSnapshot,
    SyncRun,
)
from apps.datastore.services.genesis_export import export_tables, resolve_models
from apps.portal import views
from apps.portal.api.plain import plain
from core.exceptions import DashboardError, SheetNotFoundError
from core.sheets import store_read_cache

pytestmark = pytest.mark.django_db

CARPETA = Path(__file__).parent / "eva3_db"
PAQUETE = CARPETA / "export"
HOY = date(2026, 10, 14)
MOMENTO = datetime(2026, 10, 14, 17, 0, tzinfo=UTC)
FUENTE = {"engine": "contrato", "app": "dashboard-management"}
TABLAS = [
    "datastore.SheetSnapshot",
    "datastore.ClockifyCatalog",
    "datastore.ClockifyProjectRecord",
    "datastore.ClockifyMonthSync",
    "datastore.ClockifyTimeEntry",
]
ESPACIO = "ws-contrato"
COLUMNAS = {
    "cliente": 1,
    "id": 2,
    "nombre": 4,
    "servicio": 5,
    "inicio": 6,
    "fin": 8,
    "estatus": 19,
    "manager": 20,
    "fte": 22,
    "dev": 23,
    "arq": 24,
    "ia": 25,
    "sm": 26,
    "ba": 27,
    "tt": 28,
    "cr": 29,
    "dm": 30,
    "horas": 32,
    "consumo": 63,
}
ENCABEZADOS = {
    "cliente": "CLIENTE",
    "id": "ID",
    "nombre": "NOMBRE",
    "servicio": "SERVICE",
    "inicio": "INICIO",
    "fin": "FIN",
    "estatus": "ESTATUS",
    "manager": "Delivery Manager",
    "fte": "FTE",
    "horas": "HORAS",
    "consumo": "Horas consumidas",
}


def fila(**valores) -> list:
    celdas = [""] * 64
    for nombre, valor in valores.items():
        celdas[COLUMNAS[nombre]] = valor
    return celdas


def encabezado() -> list:
    celdas = [""] * 64
    for nombre, texto in ENCABEZADOS.items():
        celdas[COLUMNAS[nombre]] = texto
    return celdas


PROGRESO = "En progreso"
MPB = [
    encabezado(),
    fila(
        cliente="Acme",
        id="AER.ACM.001",
        nombre="Portal de clientes",
        servicio="AER",
        inicio="2026-08-03",
        fin="2026-11-20",
        estatus=PROGRESO,
        manager="Ana Ruiz",
        fte=2,
        dev=1,
        arq=1,
        horas=300,
    ),
    fila(
        cliente="Beta",
        id="TYM.BET.001",
        nombre="Soporte mensual",
        servicio="T&M",
        inicio="2026-09-01",
        fin="2026-10-20",
        estatus=PROGRESO,
        manager="Ana Ruiz",
        fte=1,
        dev=1,
        horas=80,
    ),
    fila(
        cliente="Cielo",
        id="TYM.CIE.001",
        nombre="Bolsa de horas",
        servicio="T & M",
        inicio="2026-10-01",
        fin="2027-02-01",
        estatus="In progress",
        manager="Beto Soto",
        fte=0.5,
        ia=0.5,
        horas=100,
        consumo=25,
    ),
    fila(
        cliente="Delta",
        id="AER.DEL.001",
        nombre="Sin fechas",
        servicio="AER",
        inicio="",
        fin="",
        estatus=PROGRESO,
        manager="",
        fte=1,
        sm=1,
        horas=40,
    ),
    fila(
        cliente="Eco",
        id="TYM.ECO.001",
        nombre="Sin proyecto en Clockify",
        servicio="TYM",
        inicio="2026-09-01",
        fin="2026-12-31",
        estatus="En desarrollo",
        manager="Beto Soto",
        fte=1,
        ba=1,
        horas=60,
    ),
    fila(
        cliente="Foxtrot",
        id="AER.FOX.001",
        nombre="Cerrado con horas",
        servicio="AER",
        inicio="15/02/2026",
        fin="15/03/2026",
        estatus="Finalizado",
        manager="Ana Ruiz",
        fte=1,
        dev=1,
        horas=50,
    ),
    fila(
        cliente="Golf",
        id="TYM.GOL.001",
        nombre="Cerrado con consumo guardado",
        servicio="T&M",
        inicio="2026-01-05",
        fin="2026-04-30",
        estatus="Completed",
        manager="Beto Soto",
        fte=1,
        tt=1,
        horas=120,
        consumo=118.5,
    ),
    fila(
        cliente="Hotel",
        id="AER.HOT.001",
        nombre="Cancelado",
        servicio="AER",
        inicio="2026-02-01",
        fin="2026-05-01",
        estatus="Cancelado",
        manager="Ana Ruiz",
        fte=1,
        cr=1,
        horas=30,
    ),
    fila(
        cliente="India",
        id="AER.IND.001",
        nombre="Cerrado en 2025",
        servicio="AER",
        inicio="2025-02-01",
        fin="2025-05-01",
        estatus="Finalizado",
        manager="Ana Ruiz",
        fte=1,
        horas=30,
    ),
    fila(
        cliente="Juliet",
        id="ROC.JUL.001",
        nombre="Otro servicio",
        servicio="ROC",
        inicio="2026-02-01",
        fin="2026-12-01",
        estatus=PROGRESO,
        manager="Ana Ruiz",
        fte=1,
        horas=30,
    ),
]
PROYECTOS_CLOCKIFY = [
    ("p-acm", "AER.ACM.001"),
    ("p-bet", "TYM.BET.001"),
    ("p-fox", "AER.FOX.001"),
    ("p-gol", "TYM.GOL.001"),
]
HORAS = [
    ("p-acm", date(2026, 8, 4), 4 * 3600 + 900),
    ("p-acm", date(2026, 9, 15), 8 * 3600),
    ("p-acm", date(2026, 10, 2), 3 * 3600 + 1800),
    ("p-bet", date(2026, 9, 3), 5 * 3600),
    ("p-bet", date(2026, 9, 3), 5 * 3600),
    ("p-bet", date(2026, 10, 9), 7200),
    ("p-fox", date(2026, 2, 20), 6 * 3600),
    ("p-fox", date(2026, 3, 10), 10 * 3600 + 1800),
    ("p-gol", date(2026, 2, 3), 9 * 3600),
]


class Lector:
    def read_values(self, nombre):
        filas = store_read_cache.read_snapshot(nombre)
        if not isinstance(filas, list):
            raise SheetNotFoundError(f"No existe la hoja {nombre}.")
        return [list(f) for f in filas]

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
    settings.CLOCKIFY_API_KEY = "contrato"
    settings.CLOCKIFY_WORKSPACE_ID = ESPACIO
    cache.clear()
    store_read_cache._memory.clear()
    monkeypatch.setattr("django.utils.timezone.localdate", lambda *a: HOY)
    monkeypatch.setattr("apps.ejecutivo.rpc.build_sheet_repository", Lector)
    monkeypatch.setattr(
        "apps.portal.services.eva_loader.build_sheet_repository", Lector
    )
    monkeypatch.setattr("core.sheets.factory.build_sheet_repository", Lector)
    for nombre, filas in (
        ("MPB", MPB),
        (store_read_cache.SHEET_IDS_NAME, {"MPB": 1}),
    ):
        SheetSnapshot.objects.create(
            name=nombre,
            rows=filas,
            row_count=len(filas) if isinstance(filas, list) else 0,
            synced_at=MOMENTO,
        )
    catalogo = ClockifyCatalog.objects.create(
        workspace_id=ESPACIO, synced_at=MOMENTO
    )
    for posicion, (identificador, nombre) in enumerate(PROYECTOS_CLOCKIFY):
        ClockifyProjectRecord.objects.create(
            catalog=catalogo,
            external_id=identificador,
            name=nombre,
            client_id="",
            position=posicion,
        )
    for mes in (2, 3, 8, 9, 10):
        corrida = SyncRun.objects.create(kind="daily", status="ok")
        ClockifyMonthSync.objects.create(
            month=date(2026, mes, 1),
            entries_count=1,
            total_seconds=1,
            synced_at=MOMENTO,
            run_id=corrida.pk,
        )
    nombres = dict(PROYECTOS_CLOCKIFY)
    for indice, (proyecto, dia, segundos) in enumerate(HORAS, 1):
        ClockifyTimeEntry.objects.create(
            entry_id=f"e{indice:03d}",
            project_id=proyecto,
            project_name=nombres[proyecto],
            task_name="Trabajo",
            tags=["Desarrollo"],
            billable=True,
            start=f"{dia.isoformat()}T15:00:00Z",
            end=f"{dia.isoformat()}T16:00:00Z",
            entry_date=dia,
            month=dia.replace(day=1),
            duration_seconds=segundos,
        )


def consumo_de_cerrado(item: dict) -> object:
    if item["burn"] is not None:
        return item["burn"]
    inicio = date.fromisoformat(item["fechaInicio"])
    fin = date.fromisoformat(item["fechaFin"])
    cargador = build_clockify_loader(Lector())
    try:
        entradas = cargador.load_project(item["idProyecto"], (inicio, fin))
    except DashboardError as error:
        return {"error": error.detail}
    return round(sum(entrada.duration_hours for entrada in entradas), 2)


def cuerpo() -> dict:
    principal = views.eva3_data()
    cerrados = views.eva3_closed_data()
    return {
        "error": principal["error"],
        "eva": plain(principal["eva"]),
        "renewal_average": principal["renewal_average"],
        "closed_projects": plain(cerrados["projects"]),
        "closed_rows": plain(cerrados["historic_rows"]),
        "closed_error": cerrados["error"],
        "closed_burn": {
            fila["idProyecto"]: consumo_de_cerrado(fila)
            for fila in cerrados["historic_rows"]
        },
    }


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


def test_eva3_leido_de_las_tablas_coincide_con_el_contrato(escenario):
    actual = normalizar(cuerpo())

    assert actual == guardar_o_leer(CARPETA / "pantalla.json", actual)


def test_el_escenario_separa_vigentes_cerrados_y_errores_de_consumo(escenario):
    pantalla = cuerpo()

    ids = [p["project_id"] for p in pantalla["eva"]["projects"]]
    assert ids == [
        "TYM.BET.001",
        "AER.ACM.001",
        "TYM.ECO.001",
        "TYM.CIE.001",
        "AER.DEL.001",
    ]
    assert (
        "AER.DEL.001" in pantalla["error"]
        and "TYM.ECO.001" in pantalla["error"]
    )
    assert sorted(pantalla["closed_burn"]) == [
        "AER.FOX.001",
        "AER.HOT.001",
        "TYM.GOL.001",
    ]
    assert pantalla["closed_burn"]["TYM.GOL.001"] == 118.5


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
