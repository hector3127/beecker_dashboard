"""Exportación verificable de tablas propias para importarlas en Genesis.

Cada tabla sale como JSONL (una fila por línea, llaves ordenadas, filas por
llave primaria) y el manifiesto guarda filas, columnas y SHA-256 de cada
archivo. La verificación recalcula todo desde los archivos, sin la base.
No exporta usuarios, sesiones, secretos ni tablas operativas. La huella
ignora CRLF/LF: un checkout de Windows no invalida el paquete.
"""

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from django.apps import apps
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models

FORMAT = 1
MANIFEST = "manifest.json"
CHUNK = 2000

GROUPS: Mapping[str, tuple[str, ...]] = {
    "kpi": (
        "datastore.EvaExtraction",
        "datastore.DmKpiPeriod",
        "datastore.DmKpiObservation",
        "datastore.DmKpiMetric",
    ),
    "eva": (
        "datastore.EvaExtraction",
        "datastore.EvaMonthlyClosePolicy",
        "datastore.EvaMonthlyClose",
        "datastore.EvaAzureSource",
        "datastore.EvaScopeSnapshot",
    ),
    "catalogos": (
        "datastore.Client",
        "datastore.ClientAlias",
        "datastore.Person",
        "datastore.PersonAlias",
        "datastore.Project",
    ),
    "clockify": (
        "datastore.ClockifyCatalog",
        "datastore.ClockifyProjectRecord",
        "datastore.ClockifyTaskRecord",
        "datastore.ClockifyMonthSync",
        "datastore.ClockifyTimeEntry",
    ),
    "azure": (
        "datastore.AzureProject",
        "datastore.AzureWorkItem",
        "datastore.AzureIteration",
        "datastore.AzurePanelSnapshot",
        "datastore.AzureHistoryFeed",
        "datastore.AzureWorkItemRevision",
        "datastore.AzureHistoricalCut",
    ),
    "hojas": ("datastore.SheetSnapshot",),
    "acuerdos": ("portal.ExecutiveAgreement",),
}

EXCLUDED = {
    "datastore.SyncRun": "operativa: bitácora de corridas",
    "datastore.SyncLock": "operativa: candados de proceso",
    "datastore.DataRevision": "operativa: generación de caché",
    "portal.AccountLogo": "binaria: los logos viajan por otro camino",
    "access.Capability": "permisos: pendiente de definir con Genesis",
}

UNSUPPORTED_FIELDS = ("BinaryField", "FileField", "ImageField")


class ExportError(ValueError):
    """La exportación no se puede hacer o el destino no es seguro."""


@dataclass(frozen=True, slots=True)
class ExportedTable:
    """Una tabla ya escrita: archivo, filas y huella."""

    label: str
    file: str
    rows: int
    sha256: str


def resolve_models(
    groups: Iterable[str], tables: Iterable[str]
) -> list[type[models.Model]]:
    """Modelos pedidos, sin repetir y en el orden de la solicitud."""
    labels: list[str] = []
    for group in groups:
        if group not in GROUPS:
            raise ExportError(f"Grupo desconocido: {group}")
        labels.extend(GROUPS[group])
    labels.extend(tables)
    selected: list[type[models.Model]] = []
    for label in dict.fromkeys(labels):
        if label in EXCLUDED:
            raise ExportError(f"{label} no se exporta: {EXCLUDED[label]}")
        try:
            model = apps.get_model(label)
        except (LookupError, ValueError) as exc:
            raise ExportError(f"Tabla desconocida: {label}") from exc
        unsupported = [
            field.name
            for field in model._meta.concrete_fields
            if field.get_internal_type() in UNSUPPORTED_FIELDS
        ]
        if unsupported:
            raise ExportError(
                f"{label} tiene campos que no se exportan: {unsupported}"
            )
        selected.append(model)
    if not selected:
        raise ExportError("Indica al menos un grupo o una tabla.")
    return selected


def _columns(model: type[models.Model]) -> list[dict[str, Any]]:
    columns: list[dict[str, Any]] = []
    for field in model._meta.concrete_fields:
        column: dict[str, Any] = {
            "name": field.attname,
            "type": field.get_internal_type(),
            "null": field.null,
        }
        related = field.related_model
        if isinstance(field, models.ForeignKey) and related is not None:
            if not isinstance(related, str):
                column["to"] = related._meta.label
        columns.append(column)
    return columns


class _Encoder(DjangoJSONEncoder):
    """Como el de Django, pero conserva los microsegundos de las fechas."""

    def default(self, o: Any) -> Any:
        if isinstance(o, datetime):
            text = o.isoformat()
            return (
                text.removesuffix("+00:00") + "Z"
                if text.endswith("+00:00")
                else text
            )
        return super().default(o)


def _line(model: type[models.Model], row: models.Model) -> bytes:
    values = {
        field.attname: field.value_from_object(row)
        for field in model._meta.concrete_fields
    }
    text = json.dumps(values, cls=_Encoder, sort_keys=True, ensure_ascii=False)
    return text.encode("utf-8") + b"\n"


def _write_table(model: type[models.Model], folder: Path) -> ExportedTable:
    label = model._meta.label
    path = folder / f"{label}.jsonl"
    digest = hashlib.sha256()
    rows = 0
    with path.open("wb") as handle:
        for row in model._default_manager.order_by("pk").iterator(
            chunk_size=CHUNK
        ):
            line = _line(model, row)
            handle.write(line)
            digest.update(line)
            rows += 1
    return ExportedTable(label, path.name, rows, digest.hexdigest())


def export_tables(
    selected: Iterable[type[models.Model]],
    folder: Path,
    *,
    created_at: datetime,
    source: Mapping[str, Any],
) -> dict[str, Any]:
    """Escribe las tablas y el manifiesto; el destino debe estar vacío."""
    if folder.exists() and any(folder.iterdir()):
        raise ExportError(f"El destino no está vacío: {folder}")
    folder.mkdir(parents=True, exist_ok=True)
    tables = []
    for model in selected:
        exported = _write_table(model, folder)
        tables.append(
            {
                "label": exported.label,
                "db_table": model._meta.db_table,
                "pk": model._meta.pk.attname if model._meta.pk else "id",
                "file": exported.file,
                "rows": exported.rows,
                "sha256": exported.sha256,
                "columns": _columns(model),
            }
        )
    manifest = {
        "format": FORMAT,
        "created_at": created_at.isoformat(),
        "source": dict(source),
        "tables": tables,
    }
    (folder / MANIFEST).write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def verify_export(folder: Path) -> list[str]:
    """Problemas al recalcular filas y SHA-256 desde los archivos."""
    manifest_path = folder / MANIFEST
    if not manifest_path.exists():
        return [f"Falta {MANIFEST}"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format") != FORMAT:
        return [f"Formato no soportado: {manifest.get('format')}"]
    problems: list[str] = []
    for table in manifest["tables"]:
        path = folder / table["file"]
        if not path.exists():
            problems.append(f"{table['label']}: falta {table['file']}")
            continue
        digest = hashlib.sha256()
        rows = 0
        keys: set[object] = set()
        with path.open("rb") as handle:
            for line in handle:
                digest.update(line.replace(b"\r\n", b"\n"))
                rows += 1
                keys.add(json.loads(line).get(table["pk"]))
        if rows != table["rows"]:
            problems.append(
                f"{table['label']}: {rows} filas y el manifiesto dice "
                f"{table['rows']}"
            )
        if digest.hexdigest() != table["sha256"]:
            problems.append(f"{table['label']}: el SHA-256 no coincide")
        if len(keys) != rows:
            problems.append(f"{table['label']}: hay llaves primarias repetidas")
    return problems
