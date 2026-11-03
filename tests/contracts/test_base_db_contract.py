"""Paquete de datos base (catálogos, Clockify, Azure y EVA) y sus horas.

Un escenario sintético y determinista se exporta con `export_for_genesis` a
`base_db/export/`; Genesis lo importa y debe conservar filas, llaves y
totales. Las horas por mes y proyecto salen de la base con la misma consulta
que repite Genesis y quedan en `base_db/horas_por_mes_proyecto.json`.

Se reescribe solo a propósito: `UPDATE_CONTRACTS=1 pytest tests/contracts`.
"""

import json
import os
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from django.db.models import Count, Sum

from apps.datastore.models import (
    AzureHistoricalCut,
    AzureHistoryFeed,
    AzureIteration,
    AzurePanelSnapshot,
    AzureProject,
    AzureWorkItem,
    AzureWorkItemRevision,
    Client,
    ClientAlias,
    ClockifyCatalog,
    ClockifyMonthSync,
    ClockifyProjectRecord,
    ClockifyTaskRecord,
    ClockifyTimeEntry,
    EvaAzureSource,
    EvaExtraction,
    EvaMonthlyClose,
    EvaMonthlyClosePolicy,
    EvaScopeSnapshot,
    Person,
    PersonAlias,
    Project,
    SheetSnapshot,
    SyncRun,
)
from apps.datastore.services.genesis_export import export_tables, resolve_models

pytestmark = pytest.mark.django_db

CARPETA = Path(__file__).parent / "base_db"
PAQUETE = CARPETA / "export"
MOMENTO = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)
FUENTE = {"engine": "contrato", "app": "dashboard-management"}
GRUPOS = ["catalogos", "clockify", "azure", "eva", "hojas"]
PROYECTOS = ("AER.001", "AER.001_CR1", "IXB.002")
PERSONAS = (("Ana", "u1"), ("Beto", "u2"), ("Carla Díaz", "u3"))


def instante(dia: int, mes: int = 10, hora: int = 9) -> datetime:
    return datetime(2026, mes, dia, hora, 0, tzinfo=UTC)


def crear_catalogos() -> None:
    acme = Client.objects.create(name="Acme", key="acme")
    gnp = Client.objects.create(name="Grupo Nacional", key="grupo nacional")
    for clave, cliente in (("acme", acme), ("acme sa", acme), ("gnp", gnp)):
        ClientAlias.objects.create(
            key=clave,
            client=cliente,
            spellings=[clave.upper()],
            manual=clave == "gnp",
        )
    personas = [
        Person.objects.create(
            name=nombre,
            key=nombre.lower(),
            clockify_user_id=usuario,
            roles=["dm", "resource"],
        )
        for nombre, usuario in PERSONAS
    ]
    for persona in personas:
        PersonAlias.objects.create(
            key=persona.key,
            person=persona,
            spellings=[persona.name],
            manual=False,
        )
    Project.objects.create(
        internal_id="AER.001",
        base_id="AER.001",
        name="Portal AER",
        service="AER",
        client=acme,
        delivery_manager=personas[0],
        sources=["Proyectos"],
        spellings=["Portal AER"],
    )
    Project.objects.create(
        internal_id="AER.001_CR1",
        base_id="AER.001",
        name="Portal AER CR1",
        service="AER",
        client=acme,
        delivery_manager=personas[0],
    )
    Project.objects.create(
        internal_id="IXB.002", base_id="IXB.002", service="IXB"
    )
    SheetSnapshot.objects.create(
        name="Proyectos",
        rows=[
            ["ID", "Nombre"],
            ["AER.001", "Portal AER"],
            ["IXB.002", "Año ñ"],
        ],
        row_count=3,
        synced_at=MOMENTO,
    )
    SheetSnapshot.objects.create(
        name="Vacía", rows=[], row_count=0, synced_at=MOMENTO
    )


def crear_clockify() -> None:
    catalogo = ClockifyCatalog.objects.create(
        workspace_id="ws-1", synced_at=MOMENTO
    )
    proyectos = [
        ClockifyProjectRecord.objects.create(
            catalog=catalogo,
            external_id=f"p{numero}",
            name=nombre,
            client_id="c1",
            position=numero,
            tasks_synced_at=MOMENTO if numero == 1 else None,
        )
        for numero, nombre in enumerate(PROYECTOS, start=1)
    ]
    for posicion, proyecto in enumerate(proyectos[:2], start=1):
        ClockifyTaskRecord.objects.create(
            project=proyecto,
            external_id=f"t{posicion}",
            position=posicion,
            payload={"name": f"Tarea {posicion}", "billable": posicion == 1},
        )
    corridas = [
        SyncRun.objects.create(kind="daily", status="ok") for _ in range(3)
    ]
    for corrida, mes in zip(corridas, (8, 9, 10), strict=True):
        ClockifyMonthSync.objects.create(
            month=date(2026, mes, 1),
            entries_count=12,
            total_seconds=0,
            synced_at=MOMENTO,
            run_id=corrida.pk,
        )
    numero = 0
    for mes in (8, 9, 10):
        for dia in (3, 10, 17, 24):
            for indice, (proyecto, (nombre, usuario)) in enumerate(
                zip(PROYECTOS, PERSONAS, strict=True)
            ):
                numero += 1
                inicio = instante(dia, mes)
                segundos = 1800 * (1 + (numero + indice) % 7)
                ClockifyTimeEntry.objects.create(
                    entry_id=f"e{numero:04d}",
                    project_id=f"p{indice + 1}",
                    project_name=proyecto,
                    task_id="t1" if indice == 0 else "",
                    task_name="Tarea 1" if indice == 0 else "",
                    user_id=usuario,
                    user_name=nombre,
                    tags=["INV_OPERATIVA"] if numero % 5 == 0 else [],
                    description=f"Trabajo «{numero}» año ñ",
                    billable=numero % 3 != 0,
                    start=inicio.isoformat(),
                    end=(inicio + timedelta(seconds=segundos)).isoformat(),
                    entry_date=inicio.date(),
                    month=date(2026, mes, 1),
                    duration_seconds=segundos,
                )
    for resumen in ClockifyMonthSync.objects.all():
        total = ClockifyTimeEntry.objects.filter(month=resumen.month).aggregate(
            total=Sum("duration_seconds")
        )["total"]
        ClockifyMonthSync.objects.filter(pk=resumen.pk).update(
            total_seconds=total
        )


def crear_azure_y_eva() -> None:
    proyectos = [
        AzureProject.objects.create(
            name=nombre,
            position=posicion,
            risk_fields=["Risk.Probability"],
            risk_fields_ok=posicion == 0,
            raid_version=3,
            synced_at=MOMENTO,
        )
        for posicion, nombre in enumerate(("AER.001 Portal", "IXB.002 Datos"))
    ]
    for posicion in range(3):
        AzureIteration.objects.create(
            project=proyectos[0],
            position=posicion,
            name=f"Sprint {posicion + 1}",
            path=f"AER.001 Portal\\Sprint {posicion + 1}",
            start_date=instante(1 + 7 * posicion),
            finish_date=instante(6 + 7 * posicion),
            payload={"id": posicion},
        )
    for numero, clase in enumerate(
        ("latest", "raid", "panel", "latest", "raid", "panel"), start=1
    ):
        AzureWorkItem.objects.create(
            project=proyectos[numero % 2],
            kind=clase,
            position=numero,
            work_item_id=1000 + numero,
            item_type="Risk" if clase == "raid" else "Task",
            state="Active",
            title=f"Elemento {numero} ñ",
            iteration_path="AER.001 Portal\\Sprint 1",
            assigned_to="Ana",
            changed_at=instante(numero) if numero % 2 else None,
            payload={"fields": {"System.Id": 1000 + numero}},
        )
    AzurePanelSnapshot.objects.create(
        project=proyectos[0], total_items=6, synced_at=MOMENTO
    )
    cauce = AzureHistoryFeed.objects.create(
        identity="a" * 64,
        cursor="token=1",
        complete_through=MOMENTO,
        updated_at=MOMENTO,
        error="",
    )
    for revision in range(1, 9):
        AzureWorkItemRevision.objects.create(
            feed=cauce,
            work_item_id=1000 + (revision % 3) + 1,
            revision=revision,
            project_name="AER.001 Portal",
            changed_at=instante(revision),
            deleted=revision == 8,
            fields={
                "System.State": "Active",
                "Microsoft.VSTS.Scheduling.RemainingWork": revision,
            },
        )
    extraccion = EvaExtraction.objects.create(
        cut=date(2026, 10, 28),
        started_at=MOMENTO,
        finished_at=MOMENTO,
        published=True,
        metrics={"proyectos": 2},
    )
    fuentes = [
        EvaAzureSource.objects.create(
            extraction=extraccion,
            azure_id=f"az-{numero}",
            name=f"Summary {numero}",
            payload={"id": numero},
            metrics={"burn": numero * 10},
        )
        for numero in (1, 2)
    ]
    for fuente in fuentes:
        for alcance in ("S1", "CR1"):
            EvaScopeSnapshot.objects.create(
                source=fuente,
                project_id="AER.001",
                scope=alcance,
                row={"scope": alcance},
            )
        AzureHistoricalCut.objects.create(
            feed=cauce,
            source=fuente,
            cut=date(2026, 10, 28),
            feed_through=MOMENTO,
            metrics={"wi": 4},
        )
    EvaMonthlyClosePolicy.objects.update_or_create(
        pk=1, defaults={"first_month": date(2026, 10, 1)}
    )
    EvaMonthlyClose.objects.create(
        month=date(2026, 9, 1),
        cut=date(2026, 9, 30),
        extraction=extraccion,
        source_observed_at=MOMENTO,
        rows=[{"idProyecto": "AER.001", "avance": 80}],
        source_issues=[],
    )
    EvaMonthlyClose.objects.update(closed_at=MOMENTO)


@pytest.fixture
def escenario() -> None:
    crear_catalogos()
    crear_clockify()
    crear_azure_y_eva()


def horas_por_mes_y_proyecto() -> dict[str, dict[str, dict[str, int]]]:
    resultado: dict[str, dict[str, dict[str, int]]] = {}
    consulta = (
        ClockifyTimeEntry.objects.values("month", "project_id", "billable")
        .annotate(segundos=Sum("duration_seconds"), registros=Count("entry_id"))
        .order_by("month", "project_id", "billable")
    )
    for fila in consulta:
        mes = fila["month"].strftime("%Y-%m")
        clase = "facturable" if fila["billable"] else "no_facturable"
        resultado.setdefault(mes, {}).setdefault(fila["project_id"], {})[
            clase
        ] = fila["segundos"]
        resultado[mes][fila["project_id"]][f"{clase}_registros"] = fila[
            "registros"
        ]
    return resultado


def test_las_horas_por_mes_y_proyecto_coinciden_con_el_contrato(
    escenario: None,
) -> None:
    ruta = CARPETA / "horas_por_mes_proyecto.json"
    actual = horas_por_mes_y_proyecto()
    if os.environ.get("UPDATE_CONTRACTS") == "1":
        CARPETA.mkdir(parents=True, exist_ok=True)
        ruta.write_text(
            json.dumps(actual, sort_keys=True, ensure_ascii=False, indent=2)
            + "\n",
            encoding="utf-8",
            newline="\n",
        )

    assert json.loads(ruta.read_text(encoding="utf-8")) == actual
    assert sum(1 for _ in ClockifyTimeEntry.objects.all()) == 36


def test_el_paquete_de_datos_base_no_cambia(
    tmp_path: Path, escenario: None
) -> None:
    destino = tmp_path / "export"
    manifiesto = export_tables(
        resolve_models(GRUPOS, []), destino, created_at=MOMENTO, source=FUENTE
    )

    if os.environ.get("UPDATE_CONTRACTS") == "1":
        PAQUETE.mkdir(parents=True, exist_ok=True)
        for archivo in destino.iterdir():
            (PAQUETE / archivo.name).write_bytes(archivo.read_bytes())
    guardado = json.loads((PAQUETE / "manifest.json").read_text("utf-8"))

    assert manifiesto == guardado
    for tabla in manifiesto["tables"]:
        esperado = (
            (PAQUETE / tabla["file"]).read_bytes().replace(b"\r\n", b"\n")
        )
        assert (destino / tabla["file"]).read_bytes() == esperado
