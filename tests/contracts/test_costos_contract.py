"""Contrato del motor de costos por proyecto (`revenue_costs`).

DataRevenue, MPB, Historico_Proyectos, Bandas/rol y Master rates salen de
`SheetSnapshot`; el catálogo de proyectos y las horas, de las tablas de
Clockify, como en producción con las dos banderas de almacén activas. El
mismo escenario sale como paquete (`costos_db/export/`): Genesis lo importa y
debe devolver estos cuerpos.

Se reescribe solo a propósito: `UPDATE_CONTRACTS=1 pytest tests/contracts`.
"""

import json
import os
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from django.core.cache import cache

from apps.access.scope import AccessScope
from apps.datastore.models import (
    ClockifyCatalog,
    ClockifyMonthSync,
    ClockifyProjectRecord,
    ClockifyTimeEntry,
    SheetSnapshot,
    SyncRun,
)
from apps.datastore.services.genesis_export import export_tables, resolve_models
from apps.ejecutivo.services.account_view import account_matches
from apps.portal.api.plain import plain
from apps.portal.services import (
    account_profitability,
    commercial_view,
    executive_commercial,
    executive_screen,
    monthly_profitability,
    opportunity_profitability,
    revenue_costs,
)
from apps.portal.services.executive_commercial import commercial_summary
from apps.portal.services.project_profitability import add_project_revenue
from apps.portal.services.revenue import load_revenue
from core.exceptions import DashboardError, SheetNotFoundError
from core.sheets import store_read_cache
from tests.contracts.test_comercial_contract import BACKLOG

pytestmark = pytest.mark.django_db

CARPETA = Path(__file__).parent / "costos_db"
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


def datos_revenue(
    cuenta,
    identificador,
    fecha,
    estado="Confirmed",
    monto="",
    oportunidad="",
    servicio="AER",
    margen="",
):
    return [
        estado,
        cuenta,
        oportunidad,
        servicio,
        identificador,
        "",
        fecha,
        monto,
        margen,
    ]


DATA_REVENUE = [
    [
        "Estado",
        "Cuenta",
        "Oportunidad",
        "Servicio",
        "ID",
        "",
        "Fecha",
        "Monto",
        "Margen",
    ],
    datos_revenue(
        "Acme",
        "AER.ACM.001",
        "2026-02-10",
        monto=5000,
        oportunidad="Portal",
        margen=0.6,
    ),
    datos_revenue(
        "Acme",
        "AER.ACM.001_S1",
        "2026-03-10",
        "Invoiced",
        "$1,250.50",
        "Portal",
        margen=0.6,
    ),
    datos_revenue(
        "Acme",
        "AER.ACM.002",
        "2026-02-10",
        "Collected",
        800,
        "Mantenimiento",
        margen="50%",
    ),
    datos_revenue(
        "Acme",
        "AER.ACM.002",
        "2026-03-11",
        "Invoiced factoring",
        200,
        "Otra",
        margen=0.3,
    ),
    datos_revenue(
        "Acme", "AER.ACM.002.03", "2026-03-10", "Pending", 100, "Mantenimiento"
    ),
    datos_revenue(
        "Beta",
        "TYM.BET.001",
        "2026-04-10",
        monto=300,
        oportunidad="Bolsa",
        margen=0.4,
    ),
    datos_revenue(
        "Beta", "TYM.BET.001", "2026-05-10", monto="abc", oportunidad="Bolsa"
    ),
    datos_revenue(
        "Beta",
        "TYM.BET.001",
        "2026-06-10",
        monto=100,
        oportunidad="Lic",
        servicio="Licencias",
    ),
    datos_revenue(
        "Beta",
        "AER.BET.003.12",
        "2026-12-10",
        monto=900,
        oportunidad="Bolsa",
        margen=0.4,
    ),
    datos_revenue(
        "Beta", "Total", "2026-04-10", monto=999, oportunidad="Bolsa"
    ),
    datos_revenue(
        "Cielo", "ROC.CIE.001", "2025-04-10", monto=50, oportunidad="Vieja"
    ),
    datos_revenue(
        "Fox", "IXB.FOX.001", "2026-09-10", monto=700, servicio="IXB"
    ),
]


def fila_mpb(**valores):
    celdas = [""] * 64
    posiciones = {
        "cliente": 1,
        "id": 2,
        "nombre": 4,
        "servicio": 5,
        "inicio": 6,
        "fin": 8,
    }
    for nombre, valor in valores.items():
        celdas[posiciones[nombre]] = valor
    return celdas


ENCABEZADO_MPB = fila_mpb(
    cliente="CLIENTE",
    id="ID",
    nombre="NOMBRE",
    servicio="SERVICE",
    inicio="INICIO",
    fin="FIN",
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
    ),
    fila_mpb(
        cliente="Dora",
        id="TYM.DOR.001",
        nombre="Bolsa",
        servicio="T&M",
        inicio="2026-06-01",
        fin="2026-12-31",
    ),
    fila_mpb(
        cliente="Eco",
        id="AER.ECO.001",
        nombre="Viejo",
        servicio="AER",
        inicio="2024-02-01",
        fin="2025-03-01",
    ),
]
HISTORICO = [
    ["", "Cuenta", "ID", "Servicio", "", "", "Estado", "Inicio", "Fin"],
    ["", "Fox", "IXB.FOX.001", "IXB", "", "", "Discovery", "2026-05-04", ""],
    [
        "",
        "Fox",
        "IXB.FOX.001",
        "IXB",
        "",
        "",
        "Completed",
        "2026-05-04",
        "2026-09-30",
    ],
]
BANDAS = [
    ["Nombre", "ROL", "ID Clockify", "septiembre 2026", "octubre 2026"],
    ["Ana Ruiz", "Desarrollo", "u1", "B1", "B2"],
    ["Beto Soto", "Desarrollo", "u2", "B3", "BAJA"],
    ["Carla Díaz", "QA", "u3", "BAJA", "BAJA"],
    ["Dani Paz", "QA", "u4", "B9", "B9"],
]
MASTER_RATES = [
    ["Banda", "", "", "Costing Rate"],
    ["B1", "", "", 10],
    ["b2 ", "", "", 20.5],
    ["B3", "", "", "30"],
    ["B9", "", "", 0],
]
HOJAS = {
    "DataRevenue": 1,
    "MPB": 2,
    "Historico_Proyectos": 3,
    "Bandas/rol": 4,
    "Master rates": 5,
    "Backlog_Proyectos": 6,
}
CONTENIDO = {
    "DataRevenue": DATA_REVENUE,
    "MPB": MPB,
    "Historico_Proyectos": HISTORICO,
    "Bandas/rol": BANDAS,
    "Master rates": MASTER_RATES,
    "Backlog_Proyectos": BACKLOG,
}
PROYECTOS_CLOCKIFY = [
    ("p-acm1", "AER.ACM.001"),
    ("p-acm2", "AER.ACM.002"),
    ("p-bet", "TYM.BET.001"),
    ("p-dor", "TYM.DOR.001"),
    ("p-fox", "IXB.FOX.001"),
]
REGISTROS = [
    ("p-acm1", "Ana Ruiz", "General", date(2026, 2, 12), 4.0),
    ("p-acm1", "Ana Ruiz", "Sprint 1 _S1", date(2026, 3, 12), 2.5),
    ("p-acm1", "Beto Soto", "Sprint 1 _S1", date(2026, 4, 2), 3.0),
    ("p-acm1", "Carla Díaz", "General", date(2026, 9, 30), 1.0),
    ("p-acm1", "Zed Extraño", "General", date(2026, 10, 5), 2.0),
    ("p-acm1", "Ana Ruiz", "", date(2026, 10, 6), 1.5),
    ("p-acm2", "Ana Ruiz", "General", date(2026, 2, 20), 5.0),
    ("p-acm2", "Beto Soto", "General", date(2026, 3, 4), 6.0),
    ("p-acm2", "Ana Ruiz", "General", date(2026, 3, 18), 2.0),
    ("p-bet", "Ana Ruiz", "General", date(2026, 5, 4), 8.0),
    ("p-bet", "Dani Paz", "General", date(2026, 10, 9), 3.0),
    ("p-dor", "Beto Soto", "General", date(2026, 7, 7), 7.25),
    ("p-fox", "Ana Ruiz", "General", date(2026, 8, 7), 5.5),
]
MESES_SINCRONIZADOS = tuple(range(1, 11))


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


def sin_cotizacion(hoy):
    raise ValueError("Sin cotización")


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
    settings.GOOGLE_SPREADSHEET_ID = "contrato"
    settings.CLOCKIFY_API_KEY = "contrato"
    settings.CLOCKIFY_WORKSPACE_ID = ESPACIO
    cache.clear()
    store_read_cache._memory.clear()
    monkeypatch.setattr("django.utils.timezone.localdate", lambda *a: HOY)
    monkeypatch.setattr(commercial_view, "load_rates", sin_cotizacion)
    monkeypatch.setattr("core.sheets.factory.build_sheet_repository", Lector)
    monkeypatch.setattr(revenue_costs, "build_sheet_repository", Lector)
    monkeypatch.setattr(commercial_view, "build_sheet_repository", Lector)
    monkeypatch.setattr(executive_commercial, "build_sheet_repository", Lector)
    for nombre, filas in CONTENIDO.items():
        guardar_hoja(nombre, filas)
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
    for indice, (proyecto, persona, tarea, dia, horas) in enumerate(
        REGISTROS, 1
    ):
        ClockifyTimeEntry.objects.create(
            entry_id=f"e{indice:03d}",
            project_id=proyecto,
            project_name=nombres[proyecto],
            task_name=tarea,
            user_id=f"u-{persona}",
            user_name=persona,
            tags=[],
            billable=True,
            start=f"{dia.isoformat()}T15:00:00Z",
            end=f"{dia.isoformat()}T16:00:00Z",
            entry_date=dia,
            month=dia.replace(day=1),
            duration_seconds=int(horas * 3600),
        )


def financiera(lector, identificadores) -> dict:
    cuentas = account_profitability.account_profitability(lector)
    for fila in cuentas["accounts"]:
        fila.pop("url", None)
    for grupo in ("healthy", "unhealthy"):
        for fila in cuentas[grupo]:
            fila.pop("url", None)
    return {
        "revenue": plain(load_revenue()),
        "profitability": plain(
            monthly_profitability.load_monthly_profitability(
                lector, identificadores
            )
        ),
        "accounts": plain(cuentas),
    }


def ejecutiva(lector, identificadores) -> dict:
    financiero = {
        "revenue": load_revenue(),
        "costs": revenue_costs.cost_summary(identificadores),
        "profitability": monthly_profitability.load_monthly_profitability(
            lector, identificadores
        ),
        "accounts": account_profitability.account_profitability(lector),
        "commercial": commercial_summary(),
    }
    alcance = AccessScope.everything()
    return plain(
        {
            **executive_screen.company_figures(financiero, {}, alcance),
            "accounts": executive_screen.visible_accounts(financiero, alcance),
        }
    )


def margenes(lector) -> dict:
    datos = opportunity_profitability.build_opportunities(lector)
    resultado = {}
    for nombre, cuenta in (("todas", ""), ("acme", "Acme")):
        filas = [
            fila
            for fila in datos["opportunities"]
            if not cuenta or account_matches(fila["account"], cuenta)
        ]
        resultado[nombre] = plain(
            {
                "opportunities": filas,
                "accounts": [
                    a
                    for a in datos["accounts"]
                    if a["account"] in {f["account"] for f in filas}
                ],
                "summary": opportunity_profitability.opportunity_summary(filas),
                "start": datos["start"],
                "end": datos["end"],
                "excluded": datos["excluded"],
            }
        )
    return resultado


def cuerpo() -> dict:
    lector = Lector()
    identificadores = revenue_costs.project_ids(lector)
    contexto = revenue_costs.prepare_cost_context(lector, identificadores)
    proyectos = {}
    for identificador in identificadores:
        try:
            proyectos[identificador] = plain(
                revenue_costs.calculate_project_cost(identificador, contexto)
            )
        except (DashboardError, ValueError) as error:
            mensaje = (
                error.detail
                if isinstance(error, DashboardError)
                else str(error)
            )
            cache.set(revenue_costs.key(identificador) + ":error", mensaje, 300)
            proyectos[identificador] = {"error": mensaje}
    return {
        "ids": identificadores,
        "ids_de_acme": revenue_costs.project_ids(lector, "Acme"),
        "bandas": {
            nombre: list(valor) for nombre, valor in contexto.bands.items()
        },
        "tarifas": contexto.rates,
        "proyectos": proyectos,
        "resumen": plain(revenue_costs.cost_summary(identificadores)),
        "futuro": {
            identificador: revenue_costs.future_project_month(identificador)
            for identificador in identificadores
        },
        "margenes": margenes(lector),
        "financiera": financiera(lector, identificadores),
        "ejecutiva": ejecutiva(lector, identificadores),
        "pantalla": {
            "todas": plain(
                add_project_revenue(
                    revenue_costs.cost_summary(identificadores), lector
                )
            ),
            "acme": plain(
                add_project_revenue(
                    revenue_costs.cost_summary(
                        revenue_costs.project_ids(lector, "Acme"), "Acme"
                    ),
                    lector,
                    "Acme",
                )
            ),
            "detalle": {
                identificador: plain(
                    add_project_revenue(
                        revenue_costs.calculate_project_cost(
                            identificador, contexto
                        ),
                        lector,
                    )
                )
                for identificador in identificadores
                if "error" not in proyectos[identificador]
            },
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


def test_costos_leidos_de_las_tablas_coinciden_con_el_contrato(escenario):
    actual = normalizar(cuerpo())

    assert actual == guardar_o_leer(CARPETA / "costos.json", actual)


def test_el_escenario_cubre_las_ramas_del_motor(escenario):
    pantalla = cuerpo()

    assert "ROC.CIE.001" not in pantalla["ids"]
    assert "AER.ECO.001" not in pantalla["ids"]
    assert pantalla["futuro"]["AER.BET.003.12"] is True
    assert pantalla["proyectos"]["AER.ACM.001"]["missing_hours"] > 0
    assert pantalla["proyectos"]["AER.ACM.001"]["complete"] is False
    assert pantalla["proyectos"]["AER.ACM.002.03"]["scope_month"] == 3
    assert "AER.ACM.001_S1" in pantalla["proyectos"]
    assert "error" in pantalla["proyectos"]["AER.BET.003.12"]
    assert pantalla["resumen"]["future"] == 1


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
