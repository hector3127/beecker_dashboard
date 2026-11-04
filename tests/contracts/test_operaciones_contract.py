"""Contrato de las operaciones de Business Overview: población anual.

MPB y Historico_Proyectos salen de `SheetSnapshot`, como en producción con el
almacén de hojas activo. El mismo escenario sale como paquete
(`operaciones_db/export/`): Genesis lo importa y debe devolver estos cuerpos.

Se reescribe solo a propósito: `UPDATE_CONTRACTS=1 pytest tests/contracts`.
"""

import json
import os
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from django.core.cache import cache

from apps.datastore.models import (
    ClockifyCatalog,
    ClockifyMonthSync,
    ClockifyProjectRecord,
    ClockifyTimeEntry,
    SheetSnapshot,
    SyncRun,
)
from apps.datastore.services.genesis_export import export_tables, resolve_models
from apps.portal.api.plain import plain
from apps.portal.services import (
    executive_operations,
    executive_period,
    executive_population,
)
from core.exceptions import DashboardError, SheetNotFoundError
from core.sheets import store_read_cache

pytestmark = pytest.mark.django_db

CARPETA = Path(__file__).parent / "operaciones_db"
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
PROYECTOS_CLOCKIFY = [
    ("p-acm", "AER.ACM.001"),
    ("p-bet", "TYM.BET.001"),
    ("p-fox", "IXB.FOX.001"),
    ("p-gam", "RAAS.GAM.001"),
    ("p-can", "IXB.CAN.001"),
]
REGISTROS = [
    ("p-acm", "Ana", "General", [], True, date(2026, 5, 20), 5.0),
    ("p-acm", "Ana", "General", [], False, date(2026, 6, 10), 2.5),
    (
        "p-acm",
        "Beto",
        "Sprint _S1",
        ["INV_OPERATIVA"],
        True,
        date(2026, 9, 2),
        3.25,
    ),
    ("p-bet", "Ana", "General", [], True, date(2026, 9, 15), 4.0),
    (
        "p-bet",
        "Carla",
        "General",
        ["INV_COMERCIAL"],
        False,
        date(2026, 10, 1),
        1.5,
    ),
    ("p-fox", "Ana", "General", [], True, date(2026, 3, 10), 6.0),
    ("p-fox", "Ana", "S2 trabajo", [], True, date(2026, 4, 10), 4.0),
    ("p-fox", "Beto", "General", ["S1"], True, date(2026, 5, 4), 2.5),
    ("p-fox", "Beto", "General", ["CR1"], True, date(2026, 5, 5), 1.0),
    (
        "p-fox",
        "Carla",
        "General",
        ["INV_OPERATIVA"],
        True,
        date(2026, 6, 5),
        3.0,
    ),
    ("p-fox", "Carla", "General", [], False, date(2026, 6, 6), 8.0),
    ("p-fox", "Ana", "General", [], True, date(2026, 2, 1), 9.0),
    ("p-fox", "Ana", "General", [], True, date(2026, 9, 1), 7.0),
    ("p-gam", "Ana", "General", [], True, date(2026, 8, 20), 6.5),
    (
        "p-gam",
        "Beto",
        "General",
        ["INV_OPERATIVA"],
        True,
        date(2026, 10, 5),
        2.0,
    ),
    ("p-can", "Ana", "General", [], True, date(2026, 1, 20), 3.0),
]
MESES_SINCRONIZADOS = tuple(range(1, 11))
POSICIONES = {
    "cliente": 1,
    "id": 2,
    "nombre": 4,
    "servicio": 5,
    "inicio": 6,
    "fin": 8,
    "estatus": 19,
    "manager": 20,
    "presupuesto": 32,
}


def fila_mpb(**valores):
    celdas = [""] * 64
    for nombre, valor in valores.items():
        celdas[POSICIONES[nombre]] = valor
    return celdas


ENCABEZADO_MPB = fila_mpb(
    cliente="CLIENTE",
    id="ID",
    nombre="NOMBRE",
    servicio="SERVICE",
    inicio="INICIO",
    fin="FIN",
    estatus="ESTATUS",
    manager="Delivery Manager",
    presupuesto="HORAS",
)
MPB = [
    ENCABEZADO_MPB,
    fila_mpb(
        cliente="Acme",
        id="AER.ACM.001",
        nombre="Portal",
        servicio="AER",
        inicio="2026-02-01",
        fin="2026-12-01",
        estatus="En progreso",
        manager="Ana Ruiz",
        presupuesto=300,
    ),
    fila_mpb(
        cliente="Acme",
        id="AER.ACM.001",
        nombre="Portal fase 2",
        servicio="AER",
        inicio="2026-06-01",
        fin="2026-12-31",
        estatus="En progreso",
        manager="Ana Ruiz",
        presupuesto=400,
    ),
    fila_mpb(
        cliente="Beta",
        id="TYM.BET.001",
        nombre="Bolsa",
        servicio="T&M",
        inicio="2026-09-01",
        fin="2027-03-01",
        estatus="En progreso",
        manager="Beto Soto",
        presupuesto="80",
    ),
    fila_mpb(
        cliente="Eco",
        id="AER.OLD.001",
        nombre="Viejo",
        servicio="AER",
        inicio="2024-02-01",
        fin="2025-03-01",
        estatus="Finalizado",
        presupuesto=50,
    ),
    fila_mpb(
        cliente="Fut",
        id="TYM.FUT.001",
        nombre="Futuro",
        servicio="T&M",
        inicio="2027-02-01",
        fin="2027-08-01",
        estatus="Planeado",
        presupuesto=10,
    ),
]
ENCABEZADO_HISTORICO = [
    "",
    "Client",
    "Project ID",
    "Service",
    "Project Name",
    "Delivery Manager",
    "Status",
    "Start",
    "Finish",
    "Budget (Hrs)",
]


def evento(
    identificador,
    servicio,
    estado,
    inicio,
    fin="",
    presupuesto="",
    cliente="Fox",
):
    return [
        "",
        cliente,
        identificador,
        servicio,
        f"Proyecto {identificador}",
        "Carla Díaz",
        estado,
        inicio,
        fin,
        presupuesto,
    ]


HISTORICO = [
    ENCABEZADO_HISTORICO,
    evento(
        "IXB.FOX.001", "IXB", "Discovery OP", "2026-03-02", "2026-03-31", 500
    ),
    evento("IXB.FOX.001", "IXB", "Development", "2026-04-01", "2026-05-31"),
    evento("IXB.FOX.001", "IXB", "Deployment", "2026-06-01", "2026-07-31"),
    evento(
        "RAAS.GAM.001", "RaaS", "Discovery", "2026-08-03", "2026-08-31", "120"
    ),
    evento("RAAS.GAM.001", "RaaS", "Development", "2026-09-01"),
    evento("SAAS.HOT.001", "SaaS", "Discovery EST", "2027-01-05", "", 40),
    evento("IXB.CAN.001", "IXB", "Discovery", "2026-01-05", "2026-01-31", 60),
    evento("IXB.CAN.001", "IXB", "Cancelled", "2026-02-01"),
    evento(
        "IXB.DON.001", "IXB", "Discovery OP", "2025-01-01", "2025-02-01", 70
    ),
    evento("IXB.DON.001", "IXB", "Completed", "2025-06-01"),
    evento("IXB.SUS.001", "IXB", "Discovery", "2026-02-02", "2026-02-28", 90),
    evento("IXB.SUS.001", "IXB", "Suspendido", "2026-03-01"),
    evento("AER.ACM.001", "AER", "Discovery", "2026-02-01", "2026-02-15"),
]
HOJAS = {"MPB": 1, "Historico_Proyectos": 2}
PERIODOS = {
    "predeterminado": None,
    "octubre": {"periodo": "mes", "anio": "2026", "mes": "10"},
    "primer_trimestre": {
        "periodo": "trimestre",
        "anio": "2026",
        "trimestre": "1",
    },
}


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
    settings.GOOGLE_SPREADSHEET_ID = "contrato"
    cache.clear()
    store_read_cache._memory.clear()
    monkeypatch.setattr("django.utils.timezone.localdate", lambda *a: HOY)
    monkeypatch.setattr(executive_population, "build_sheet_repository", Lector)
    monkeypatch.setattr(executive_operations, "build_sheet_repository", Lector)
    settings.CLOCKIFY_STORE_ENABLED = True
    settings.CLOCKIFY_API_KEY = "contrato"
    settings.CLOCKIFY_WORKSPACE_ID = ESPACIO
    guardar_hoja("MPB", MPB)
    guardar_hoja("Historico_Proyectos", HISTORICO)
    guardar_hoja(store_read_cache.SHEET_IDS_NAME, HOJAS)
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
    for mes in MESES_SINCRONIZADOS:
        corrida = SyncRun.objects.create(kind="daily", status="ok")
        ClockifyMonthSync.objects.create(
            month=date(2026, mes, 1),
            entries_count=1,
            total_seconds=1,
            synced_at=MOMENTO,
            run_id=corrida.pk,
        )
    nombres = dict(PROYECTOS_CLOCKIFY)
    for indice, (
        proyecto,
        persona,
        tarea,
        etiquetas,
        facturable,
        dia,
        horas,
    ) in enumerate(REGISTROS, 1):
        ClockifyTimeEntry.objects.create(
            entry_id=f"e{indice:03d}",
            project_id=proyecto,
            project_name=nombres[proyecto],
            task_name=tarea,
            user_id=f"u-{persona}",
            user_name=persona,
            tags=etiquetas,
            billable=facturable,
            start=f"{dia.isoformat()}T15:00:00Z",
            end=f"{dia.isoformat()}T16:00:00Z",
            entry_date=dia,
            month=dia.replace(day=1),
            duration_seconds=int(horas * 3600),
        )


def poblacion(periodo):
    cache.clear()
    if periodo is None:
        return plain(executive_population.population(Lector()))
    with executive_period.applied(executive_period.parse(periodo, HOY)):
        return plain(executive_population.population(Lector()))


def cuerpo() -> dict:
    return {nombre: poblacion(periodo) for nombre, periodo in PERIODOS.items()}


def consumo() -> dict:
    cache.clear()
    resultado = {}
    for proyecto in executive_population.population(Lector()):
        try:
            resultado[proyecto["id"]] = plain(
                executive_operations.calculate_burn(proyecto["id"])
            )
        except DashboardError as error:
            resultado[proyecto["id"]] = {"error": error.detail}
    return resultado


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


def test_la_poblacion_leida_de_las_hojas_coincide_con_el_contrato(escenario):
    actual = normalizar(cuerpo())

    assert actual == guardar_o_leer(CARPETA / "poblacion.json", actual)


def test_el_consumo_por_proyecto_coincide_con_el_contrato(escenario):
    actual = normalizar(consumo())

    assert actual == guardar_o_leer(CARPETA / "consumo.json", actual)


def test_el_escenario_cubre_las_ramas_del_consumo(escenario):
    casos = consumo()

    assert casos["IXB.FOX.001"]["burn"] == 11.5
    assert casos["AER.ACM.001"]["burn"] == 5.75
    assert "error" in casos["IXB.SUS.001"]
    operativas = [
        e
        for e in casos["IXB.FOX.001"]["metric_entries"].values()
        if e["operational"]
    ]
    assert len(operativas) == 1


def test_el_escenario_cubre_las_ramas_de_la_poblacion(escenario):
    casos = cuerpo()

    ids = [p["id"] for p in casos["predeterminado"]]
    assert "AER.ACM.001" in ids
    assert "TYM.FUT.001" not in ids
    assert "AER.OLD.001" not in ids
    assert "IXB.FOX.001" in ids
    assert "IXB.CAN.001" in ids
    assert "IXB.DON.001" not in ids
    assert "SAAS.HOT.001" not in ids
    portal = next(
        p for p in casos["predeterminado"] if p["id"] == "AER.ACM.001"
    )
    assert portal["budget"] == 400
    assert casos["octubre"] != casos["predeterminado"]


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
