"""Contrato de Comercial: backlog de oportunidades, filtros, pipeline, gráficas.

Backlog_Proyectos sale de `SheetSnapshot`, como en producción con el almacén
de hojas activo. La cotización de otras monedas se pide a un servicio externo
que Genesis nunca consulta: aquí falla, y los importes en otra moneda quedan
pendientes. El mismo escenario sale como paquete (`comercial_db/export/`):
Genesis lo importa y debe devolver estos cuerpos.

Se reescribe solo a propósito: `UPDATE_CONTRACTS=1 pytest tests/contracts`.
"""

import json
import os
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from django.core.cache import cache
from django.http import QueryDict

from apps.datastore.models import SheetSnapshot
from apps.datastore.services.genesis_export import export_tables, resolve_models
from apps.portal.api.plain import plain
from apps.portal.services import commercial_view
from core.exceptions import SheetNotFoundError
from core.sheets import store_read_cache

pytestmark = pytest.mark.django_db

CARPETA = Path(__file__).parent / "comercial_db"
PAQUETE = CARPETA / "export"
HOY = date(2026, 10, 14)
MOMENTO = datetime(2026, 10, 14, 17, 0, tzinfo=UTC)
FUENTE = {"engine": "contrato", "app": "dashboard-management"}
TABLAS = ["datastore.SheetSnapshot"]
ENCABEZADO = [
    "Account Name",
    "Opportunity Name",
    "Delivery Manager",
    "Opportunity Stage",
    "Fecha de cierre",
    "Service Type",
    "Invoice Name",
    "Total Hours",
    "Valor",
    "Currency Opportunity",
    "Deal ID",
    "Fecha ultimo seguimiento",
    "Probabilidad",
]


def fila(
    cuenta,
    oportunidad,
    etapa,
    cierre,
    servicio="AER",
    horas=100,
    valor=1000,
    moneda="USD",
    identificador="",
    seguimiento="",
    probabilidad="",
    manager="Ana Ruiz",
):
    return [
        cuenta,
        oportunidad,
        manager,
        etapa,
        cierre,
        servicio,
        "",
        horas,
        valor,
        moneda,
        identificador,
        seguimiento,
        probabilidad,
    ]


BACKLOG = [
    ["Reporte de backlog"],
    ENCABEZADO,
    fila(
        "Acme",
        "Portal",
        "Closed Won",
        "2026-02-10",
        valor=5000,
        identificador="d1",
    ),
    fila(
        "Acme",
        "Portal v2",
        "Proposal Sent",
        "2026-11-15",
        horas=200,
        probabilidad=0.9,
        identificador="d2",
    ),
    fila(
        "Acme",
        "Portal v2",
        "Proposal Sent (Pipeline)",
        "2026-11-20",
        horas=250,
        probabilidad=0.9,
        identificador="d2",
        seguimiento="2026-10-01",
    ),
    fila(
        "Acme",
        "Soporte",
        "Negotiation",
        "2026-12-05",
        servicio="T&M",
        horas=80,
        probabilidad="75%",
        identificador="d3",
    ),
    fila(
        "Beta",
        "Bolsa",
        "Discovery",
        "2027-03-01",
        servicio="T&M",
        horas=120,
        valor=800,
        probabilidad=0.4,
        identificador="d4",
    ),
    fila(
        "Beta",
        "Bolsa fase 2",
        "Intent",
        "2026-12-20",
        servicio="IXB",
        horas=60,
        valor=900,
        moneda="MXN",
        probabilidad=0.2,
        identificador="d5",
    ),
    fila(
        "Beta",
        "Sin fecha",
        "Qualified",
        "",
        horas=30,
        probabilidad=0.8,
        identificador="d6",
    ),
    fila(
        "Beta",
        "Sin horas",
        "Qualified",
        "2026-12-10",
        horas="",
        probabilidad=0.8,
        identificador="d7",
    ),
    fila(
        "Cielo",
        "Perdida",
        "Closed Lost",
        "2026-05-01",
        valor=300,
        identificador="d8",
    ),
    fila(
        "Cielo",
        "Sin probabilidad",
        "Contract Sent",
        "2026-11-30",
        servicio="SaaS",
        horas=40,
        valor="(no value)",
        identificador="d9",
    ),
    fila(
        "Cielo",
        "Negativa",
        "Appointment Scheduled",
        "2026-09-01",
        horas=-5,
        valor=-1,
        probabilidad=150,
        identificador="d10",
    ),
    fila("", "Huérfana", "", "2026-10-30", horas=10, identificador="d11"),
]
HOJAS = {"Backlog_Proyectos": 1}
CASOS = {
    "predeterminado": "",
    "unicas": "unique_opportunities=1",
    "cuenta": "cliente=Acme",
    "etapa": "etapa=Closed+Won",
    "fechas": "desde=2026-10-01&hasta=2026-12-31",
    "fechas_invertidas": "desde=2026-12-31&hasta=2026-10-01",
    "busqueda": "q=ana+ruiz",
    "pipeline_2027": "pipeline_year=2027",
    "pagina_dos": "pagina=2",
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


def sin_cotizacion(hoy):
    raise ValueError("Sin cotización")


@pytest.fixture
def escenario(monkeypatch, settings):
    settings.SHEETS_STORE_ENABLED = True
    settings.GOOGLE_SPREADSHEET_ID = "contrato"
    cache.clear()
    store_read_cache._memory.clear()
    monkeypatch.setattr("django.utils.timezone.localdate", lambda *a: HOY)
    monkeypatch.setattr(commercial_view, "build_sheet_repository", Lector)
    monkeypatch.setattr(commercial_view, "load_rates", sin_cotizacion)
    guardar_hoja("Backlog_Proyectos", BACKLOG)
    guardar_hoja(store_read_cache.SHEET_IDS_NAME, HOJAS)


def pantalla(consulta: str) -> dict:
    contexto = commercial_view.present_commercial_context(
        commercial_view.build_commercial_context(QueryDict(consulta))
    )
    pagina = contexto.pop("page", None)
    if pagina is not None:
        contexto["page"] = {
            "number": pagina.number,
            "num_pages": pagina.paginator.num_pages,
            "rows": list(pagina.object_list),
        }
    for seccion in contexto.get("pipeline", {}).get("sections", []):
        seccion.pop("row_page", None)
    for campo in ("loaded_at", "filter_query"):
        contexto.pop(campo, None)
    for seccion in contexto.get("pipeline", {}).get("sections", []):
        seccion.pop("page_query", None)
    return plain(contexto)


def cuerpo() -> dict:
    casos = {nombre: pantalla(consulta) for nombre, consulta in CASOS.items()}
    guardar_hoja("Backlog_Proyectos", [["Otra", "cosa"]])
    store_read_cache._memory.clear()
    casos["sin_encabezados"] = pantalla("")
    SheetSnapshot.objects.filter(name="Backlog_Proyectos").delete()
    store_read_cache._memory.clear()
    casos["sin_hoja"] = pantalla("")
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


def test_comercial_leido_de_la_hoja_coincide_con_el_contrato(escenario):
    actual = normalizar(cuerpo())

    assert actual == guardar_o_leer(CARPETA / "comercial.json", actual)


def test_el_escenario_cubre_las_ramas_del_motor(escenario):
    casos = cuerpo()

    base = casos["predeterminado"]
    assert base["fx_error"]
    assert base["pending_usd"] >= 1
    assert base["won_count"] == 1
    assert base["missing_id"] is False
    assert casos["unicas"]["duplicates_removed"] == 1
    assert casos["fechas_invertidas"]["error"]
    assert casos["sin_encabezados"]["error"]
    assert casos["sin_hoja"]["error"]
    assert {s["key"] for s in base["pipeline"]["sections"]} == {
        "confirmed",
        "unconfirmed",
        "pending",
    }
    assert casos["pagina_dos"]["page"]["number"] == 1


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
