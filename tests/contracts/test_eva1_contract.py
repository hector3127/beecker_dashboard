"""Contrato de EVA 1 leído de las tablas guardadas, y su paquete de datos.

Un corte guardado con seis fuentes de Azure: cuatro proyectos abiertos (uno con
horas repartidas entre sprint y CR, uno sin Clockify, uno suspendido), uno
cerrado y confirmado, uno de otro servicio y uno que empieza después del corte.
El mismo escenario sale como paquete de exportación (`eva1_db/export/`): Genesis
lo importa y debe devolver estos mismos cuerpos.

Se reescribe solo a propósito: `UPDATE_CONTRACTS=1 pytest tests/contracts`.
"""

import json
import os
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from apps.datastore.models import (
    EvaAzureSource,
    EvaExtraction,
    EvaScopeSnapshot,
)
from apps.datastore.services.genesis_export import export_tables, resolve_models
from apps.portal.api.plain import plain
from apps.portal.services.eva1_screen import build_eva1_screen

pytestmark = pytest.mark.django_db

CARPETA = Path(__file__).parent / "eva1_db"
PAQUETE = CARPETA / "export"
HOY = date(2026, 10, 28)
MOMENTO = datetime(2026, 10, 28, 17, 0, tzinfo=UTC)
FUENTE = {"engine": "contrato", "app": "dashboard-management"}
TABLAS = ["datastore.EvaExtraction", "datastore.EvaAzureSource"]
TABLAS.append("datastore.EvaScopeSnapshot")

CASOS = {
    "corte_por_omision": (HOY, "", ""),
    "con_dm": (HOY, "Beto Soto", ""),
    "con_servicio": (HOY, "", "RaaS"),
    "dm_sin_proyectos": (HOY, "Nadie", ""),
    "corte_anterior": (date(2026, 10, 12), "", ""),
}


def hora(dia: int, horas: float, **extra) -> dict:
    """Entrada de Clockify de un día de octubre, con su duración en segundos."""
    return {
        "_id": f"e{dia}-{extra.pop('clave', '')}",
        "billable": extra.pop("billable", True),
        "timeInterval": {
            "start": f"2026-10-{dia:02d}T14:00:00Z",
            "duration": int(horas * 3600),
        },
        **extra,
    }


def etapa(nombre: str, scope: str, inicio: str, fin: str) -> dict:
    return {
        "name": f"{nombre}_{scope}",
        "identifier": f"{nombre.lower()}-{scope.lower()}",
        "attributes": {
            "startDate": f"{inicio}T00:00:00Z",
            "finishDate": f"{fin}T00:00:00Z",
        },
    }


def arbol(*scopes: tuple[str, list[dict]]) -> dict:
    return {
        "name": "raiz",
        "children": [
            {"name": f"General_{scope}", "children": etapas}
            for scope, etapas in scopes
        ],
    }


def metricas(proyecto: str, **extra) -> dict:
    base = {
        "idProyecto": proyecto,
        "azure_pending": False,
        "budget_pending": False,
        "closed": False,
        "closure_confirmed": False,
        "wi": {
            "general": {"total": 10, "cerrados": 4, "pendientes": 6},
            "discovery": {"total": 3, "cerrados": 3, "pendientes": 0},
            "development": {"total": 5, "cerrados": 1, "pendientes": 4},
            "deployment": {"total": 2, "cerrados": 0, "pendientes": 2},
        },
        "riesgos": [],
        "burn": None,
        "etc": None,
        "avance": None,
        "hours_pending": True,
        "progress_pending": True,
    }
    base.update(extra)
    return base


def alcance(
    fuente: EvaAzureSource,
    scope: str,
    *,
    dm: str,
    servicio: str,
    nombre: str,
    cliente: str,
    presupuesto: float,
    inicio: str,
    fin: str,
    estado_azure: str = "Development",
    **extra_metricas,
) -> None:
    proyecto = f"{fuente.name}_{scope}"
    EvaScopeSnapshot.objects.create(
        source=fuente,
        project_id=proyecto,
        scope=scope,
        row={
            "azure_project": fuente.name,
            "project_id": proyecto,
            "scope": scope,
            "fields": {
                "project_name": nombre,
                "client": cliente,
                "delivery_manager": dm,
                "service": servicio,
                "budget": str(presupuesto),
            },
            "start": inicio,
            "finish": fin,
            "budget": str(presupuesto),
            "issues": [],
            "unknown_labels": [],
            "metadata": {},
            "ready": True,
            "iteration_start": inicio,
            "iteration_finish": fin,
            "calendar_stage": "",
            "stages": [],
            "iteration_issues": [],
            "metrics_observed_date": HOY.isoformat(),
            "business_status": extra_metricas.pop("business_status", ""),
            "eva_metrics": metricas(
                proyecto,
                deliveryManager=dm,
                servicio=servicio,
                nombre=nombre,
                cliente=cliente,
                fechaInicio=inicio,
                fechaFin=fin,
                budget=presupuesto,
                status=estado_azure,
                scope=scope,
                summary_scope=scope,
                scope_aliases=[scope],
                **extra_metricas,
            ),
        },
    )


def fuente(extraccion, azure_id, nombre, tree, clockify=None) -> EvaAzureSource:
    return EvaAzureSource.objects.create(
        extraction=extraccion,
        azure_id=azure_id,
        name=nombre,
        payload={
            "summary": {
                "id": azure_id,
                "name": nombre,
                "state": "wellFormed",
                "iteration_tree": tree,
                "eva_evidence": {
                    "observed_date": HOY.isoformat(),
                    "clockify": clockify or {},
                },
            }
        },
    )


@pytest.fixture
def escenario(monkeypatch):
    monkeypatch.setattr("django.utils.timezone.localdate", lambda *a: HOY)
    extraccion = EvaExtraction.objects.create(
        cut=HOY,
        started_at=MOMENTO,
        finished_at=MOMENTO,
        published=True,
        metrics={
            "kind": "summary_inventory",
            "source_observed_at": MOMENTO.isoformat(),
            "eva_enriched": True,
            "projects": 6,
        },
    )
    acm = fuente(
        extraccion,
        "az-acm",
        "ACM.001",
        arbol(
            (
                "S1",
                [
                    etapa("Discovery", "S1", "2026-08-17", "2026-08-28"),
                    etapa("Development", "S1", "2026-08-31", "2026-11-20"),
                    etapa("Deployment", "S1", "2026-11-23", "2026-12-18"),
                ],
            ),
            (
                "CR1",
                [
                    etapa("Discovery", "CR1", "2026-10-01", "2026-10-02"),
                    etapa("Development", "CR1", "2026-10-05", "2026-10-23"),
                ],
            ),
        ),
        {
            "clk-acm": [
                hora(5, 20, clave="auto"),
                hora(6, 100, clave="s1", tags=[{"name": "S1"}]),
                hora(7, 50, clave="cr1", tags=[{"name": "CR1"}]),
                hora(7, 10, clave="no", billable=False),
            ]
        },
    )
    alcance(
        acm,
        "S1",
        dm="Ana Ruiz",
        servicio="IXB",
        nombre="Portal de clientes",
        cliente="Acme",
        presupuesto=200,
        inicio="2026-08-17",
        fin="2026-12-18",
        clockify_project_id="clk-acm",
    )
    alcance(
        acm,
        "CR1",
        dm="Ana Ruiz",
        servicio="RaaS",
        nombre="Portal de clientes CR",
        cliente="Acme",
        presupuesto=40,
        inicio="2026-10-01",
        fin="2026-10-23",
        clockify_project_id="clk-acm",
    )
    bta = fuente(
        extraccion,
        "az-bta",
        "BTA.002",
        arbol(("S1", [etapa("Discovery", "S1", "2026-10-19", "2026-10-30")])),
    )
    alcance(
        bta,
        "S1",
        dm="Beto Soto",
        servicio="SaaS",
        nombre="Tablero comercial",
        cliente="Beta",
        presupuesto=100,
        inicio="2026-10-19",
        fin="2026-10-30",
        estado_azure="Discovery",
    )
    clx = fuente(
        extraccion,
        "az-clx",
        "CLX.003",
        arbol(
            (
                "S1",
                [
                    etapa("Discovery", "S1", "2026-09-01", "2026-09-11"),
                    etapa("Development", "S1", "2026-09-14", "2026-11-30"),
                ],
            )
        ),
    )
    alcance(
        clx,
        "S1",
        dm="Beto Soto",
        servicio="IXB",
        nombre="Migración de datos",
        cliente="Cielo",
        presupuesto=300,
        inicio="2026-09-01",
        fin="2026-11-30",
        business_status="Suspendido",
    )
    delta = fuente(
        extraccion,
        "az-del",
        "DEL.004",
        arbol(("S1", [etapa("Deployment", "S1", "2026-06-01", "2026-09-30")])),
    )
    alcance(
        delta,
        "S1",
        dm="Ana Ruiz",
        servicio="RaaS",
        nombre="Soporte cerrado",
        cliente="Delta",
        presupuesto=80,
        inicio="2026-06-01",
        fin="2026-09-30",
        closed=True,
        closure_confirmed=True,
    )
    aer = fuente(
        extraccion,
        "az-aer",
        "AER.005",
        arbol(("S1", [etapa("Development", "S1", "2026-09-01", "2026-12-01")])),
    )
    alcance(
        aer,
        "S1",
        dm="Ana Ruiz",
        servicio="AER",
        nombre="Otro servicio",
        cliente="Eco",
        presupuesto=50,
        inicio="2026-09-01",
        fin="2026-12-01",
    )
    futuro = fuente(
        extraccion,
        "az-fut",
        "FUT.006",
        arbol(("S1", [etapa("Discovery", "S1", "2026-11-02", "2026-11-13")])),
    )
    alcance(
        futuro,
        "S1",
        dm="Beto Soto",
        servicio="IXB",
        nombre="Aún no empieza",
        cliente="Futuro",
        presupuesto=60,
        inicio="2026-11-02",
        fin="2026-11-13",
        estado_azure="Discovery",
    )
    return extraccion


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


@pytest.mark.parametrize("nombre", list(CASOS))
def test_eva1_leido_de_las_tablas_coincide_con_el_contrato(escenario, nombre):
    corte, dm, servicio = CASOS[nombre]

    actual = normalizar(plain(build_eva1_screen(corte, dm, servicio)))

    assert actual == guardar_o_leer(CARPETA / f"{nombre}.json", actual)


def test_el_corte_por_omision_cuenta_solo_los_proyectos_abiertos(escenario):
    pantalla = build_eva1_screen(HOY, "", "")

    ids = [p.project_id for p in pantalla["eva"].projects]

    assert sorted(ids) == [
        "ACM.001_CR1",
        "ACM.001_S1",
        "BTA.002_S1",
        "CLX.003_S1",
    ]


def test_el_paquete_de_exportacion_del_escenario_no_cambia(tmp_path, escenario):
    destino = tmp_path / "export"
    manifiesto = export_tables(
        resolve_models([], TABLAS),
        destino,
        created_at=MOMENTO,
        source=FUENTE,
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
