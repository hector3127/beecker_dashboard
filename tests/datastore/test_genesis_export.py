"""Exportación de tablas para Genesis: contenido, manifiesto y verificación."""

import hashlib
import json
from datetime import UTC, date, datetime
from io import StringIO
from pathlib import Path

import pytest
from django.apps import apps
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.datastore.models import (
    DmKpiMetric,
    DmKpiObservation,
    DmKpiPeriod,
    EvaExtraction,
)
from apps.datastore.services.genesis_export import (
    EXCLUDED,
    GROUPS,
    ExportError,
    export_tables,
    resolve_models,
    verify_export,
)

pytestmark = pytest.mark.django_db

NOW = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)
SOURCE = {"engine": "test", "app": "dashboard-management"}


@pytest.fixture
def kpi_rows():
    extraction = EvaExtraction.objects.create(
        cut=date(2026, 10, 29),
        started_at=NOW,
        published=True,
        metrics={"proyectos": 9, "nota": "Año ñ"},
    )
    period = DmKpiPeriod.objects.create(
        month=date(2026, 10, 1),
        closing_day=date(2026, 10, 29),
        status="closed",
        closed_at=NOW,
    )
    observation = DmKpiObservation.objects.create(
        period=period,
        cut=date(2026, 10, 29),
        source=extraction,
        source_observed_at=NOW,
        issues=[],
    )
    period.latest_observation = observation
    period.save()
    for name, total in (("Beto", 4), ("Ana", 5)):
        DmKpiMetric.objects.create(
            observation=observation,
            manager=name,
            slug=name.lower(),
            total=total,
            on_time=total,
            late=0,
            over_budget=0,
        )
    return observation


def export(tmp_path, groups=("kpi",), tables=(), name="out"):
    folder = tmp_path / name
    manifest = export_tables(
        resolve_models(groups, tables),
        folder,
        created_at=NOW,
        source=SOURCE,
    )
    return folder, manifest


def rows(folder, label):
    path = folder / f"{label}.jsonl"
    return [json.loads(line) for line in path.read_text("utf-8").splitlines()]


def test_the_kpi_group_writes_every_table_with_its_counts(tmp_path, kpi_rows):
    folder, manifest = export(tmp_path)

    counts = {t["label"]: t["rows"] for t in manifest["tables"]}
    assert counts == {
        "datastore.EvaExtraction": 1,
        "datastore.DmKpiPeriod": 1,
        "datastore.DmKpiObservation": 1,
        "datastore.DmKpiMetric": 2,
    }
    assert manifest["format"] == 1
    assert manifest["created_at"] == NOW.isoformat()
    assert manifest["source"] == SOURCE
    assert (folder / "manifest.json").exists()


def test_each_hash_is_the_sha256_of_its_file(tmp_path, kpi_rows):
    folder, manifest = export(tmp_path)

    for table in manifest["tables"]:
        data = (folder / table["file"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == table["sha256"]


def test_rows_keep_keys_dates_json_and_unicode(tmp_path, kpi_rows):
    folder, _ = export(tmp_path)

    period = rows(folder, "datastore.DmKpiPeriod")[0]
    assert period["month"] == "2026-10-01"
    assert period["status"] == "closed"
    assert period["latest_observation_id"] == kpi_rows.pk
    assert period["closed_at"].startswith("2026-11-02T12:00:00")
    extraction = rows(folder, "datastore.EvaExtraction")[0]
    assert extraction["metrics"] == {"proyectos": 9, "nota": "Año ñ"}
    observation = rows(folder, "datastore.DmKpiObservation")[0]
    assert observation["source_id"] == extraction["id"]
    assert observation["period_id"] == period["id"]


def test_rows_are_ordered_by_primary_key(tmp_path, kpi_rows):
    folder, _ = export(tmp_path)

    ids = [row["id"] for row in rows(folder, "datastore.DmKpiMetric")]
    assert ids == sorted(ids)
    assert [r["manager"] for r in rows(folder, "datastore.DmKpiMetric")] == [
        "Beto",
        "Ana",
    ]


def test_the_manifest_describes_columns_and_foreign_keys(tmp_path, kpi_rows):
    _, manifest = export(tmp_path)

    metric = next(
        t for t in manifest["tables"] if t["label"] == "datastore.DmKpiMetric"
    )
    columns = {c["name"]: c for c in metric["columns"]}
    assert metric["pk"] == "id"
    assert metric["db_table"] == "datastore_dmkpimetric"
    assert columns["observation_id"]["to"] == "datastore.DmKpiObservation"
    assert columns["manager"]["type"] == "CharField"
    period = next(
        t for t in manifest["tables"] if t["label"] == "datastore.DmKpiPeriod"
    )
    nullable = {c["name"]: c["null"] for c in period["columns"]}
    assert nullable["latest_observation_id"] is True


def test_the_same_data_exports_identical_files(tmp_path, kpi_rows):
    _, first = export(tmp_path, name="a")
    _, second = export(tmp_path, name="b")

    assert first == second


def test_a_clean_export_verifies(tmp_path, kpi_rows):
    folder, _ = export(tmp_path)

    assert verify_export(folder) == []


def test_verification_detects_a_changed_value(tmp_path, kpi_rows):
    folder, _ = export(tmp_path)
    path = folder / "datastore.DmKpiMetric.jsonl"
    path.write_text(
        path.read_text("utf-8").replace('"total": 5', '"total": 6'),
        encoding="utf-8",
        newline="\n",
    )

    problems = verify_export(folder)

    assert problems == ["datastore.DmKpiMetric: el SHA-256 no coincide"]


def test_verification_detects_a_missing_or_extra_row(tmp_path, kpi_rows):
    folder, _ = export(tmp_path)
    path = folder / "datastore.DmKpiMetric.jsonl"
    first = path.read_text("utf-8").splitlines()[0]
    path.write_text(first + "\n", encoding="utf-8", newline="\n")

    problems = verify_export(folder)

    assert any("1 filas y el manifiesto dice 2" in p for p in problems)
    assert any("SHA-256" in p for p in problems)


def test_verification_detects_a_missing_file_and_manifest(tmp_path, kpi_rows):
    folder, _ = export(tmp_path)
    (folder / "datastore.DmKpiPeriod.jsonl").unlink()

    assert verify_export(folder) == [
        "datastore.DmKpiPeriod: falta datastore.DmKpiPeriod.jsonl"
    ]
    assert verify_export(tmp_path / "vacia") == ["Falta manifest.json"]


def test_verification_detects_repeated_primary_keys(tmp_path, kpi_rows):
    folder, manifest = export(tmp_path)
    path = folder / "datastore.DmKpiMetric.jsonl"
    line = path.read_text("utf-8").splitlines()[0]
    data = (line + "\n") * 2
    path.write_text(data, encoding="utf-8", newline="\n")
    metric = next(
        t for t in manifest["tables"] if t["label"] == "datastore.DmKpiMetric"
    )
    metric["sha256"] = hashlib.sha256(data.encode("utf-8")).hexdigest()
    (folder / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8", newline="\n"
    )

    assert verify_export(folder) == [
        "datastore.DmKpiMetric: hay llaves primarias repetidas"
    ]


def test_an_unknown_manifest_format_is_rejected(tmp_path, kpi_rows):
    folder, manifest = export(tmp_path)
    manifest["format"] = 99
    (folder / "manifest.json").write_text(json.dumps(manifest), "utf-8")

    assert verify_export(folder) == ["Formato no soportado: 99"]


def test_it_refuses_a_destination_that_is_not_empty(tmp_path, kpi_rows):
    folder = tmp_path / "ocupada"
    folder.mkdir()
    (folder / "algo.txt").write_text("x", encoding="utf-8")

    with pytest.raises(ExportError, match="no está vacío"):
        export_tables(
            resolve_models(["kpi"], []), folder, created_at=NOW, source=SOURCE
        )
    assert (folder / "algo.txt").exists()


@pytest.mark.parametrize(
    "groups,tables,message",
    [
        (["nada"], [], "Grupo desconocido"),
        ([], ["datastore.NoExiste"], "Tabla desconocida"),
        ([], ["sin_punto"], "Tabla desconocida"),
        ([], ["portal.AccountLogo"], "no se exporta"),
        ([], ["datastore.SyncLock"], "no se exporta"),
        ([], [], "al menos un grupo"),
    ],
)
def test_it_rejects_bad_selections(groups, tables, message):
    with pytest.raises(ExportError, match=message):
        resolve_models(groups, tables)


def test_a_table_is_exported_once_even_if_two_groups_list_it():
    selected = resolve_models(["kpi", "eva"], ["datastore.EvaExtraction"])

    labels = [model._meta.label for model in selected]
    assert labels.count("datastore.EvaExtraction") == 1


def test_groups_only_hold_the_dashboard_tables_never_users_or_sessions():
    apps_in_groups = {
        label.split(".")[0] for g in GROUPS.values() for label in g
    }

    assert apps_in_groups <= {"datastore", "portal"}
    assert not any(
        label.startswith(("auth.", "sessions.")) for label in EXCLUDED
    )


def test_every_group_resolves_to_exportable_models():
    assert resolve_models(GROUPS, [])


def test_every_dashboard_table_is_in_a_group_or_explicitly_excluded():
    grouped = {label for labels in GROUPS.values() for label in labels}
    own = {
        model._meta.label
        for name in ("datastore", "portal")
        for model in apps.get_app_config(name).get_models()
    }

    assert own - grouped - set(EXCLUDED) == set()


def test_the_command_exports_and_verifies(tmp_path, kpi_rows, settings):
    settings.BASE_DIR = tmp_path / "repo"
    folder = tmp_path / "fuera"
    out = StringIO()

    call_command(
        "export_for_genesis", out=str(folder), group=["kpi"], stdout=out
    )
    call_command("export_for_genesis", verify=str(folder), stdout=out)

    text = out.getvalue()
    assert "datastore.DmKpiMetric: 2 filas" in text
    assert "Export verificado" in text


def test_the_command_fails_when_verification_finds_problems(
    tmp_path, kpi_rows, settings
):
    settings.BASE_DIR = tmp_path / "repo"
    folder = tmp_path / "fuera"
    call_command(
        "export_for_genesis", out=str(folder), group=["kpi"], stdout=StringIO()
    )
    (folder / "datastore.DmKpiPeriod.jsonl").unlink()

    with pytest.raises(CommandError, match="1 problemas"):
        call_command(
            "export_for_genesis",
            verify=str(folder),
            stdout=StringIO(),
            stderr=StringIO(),
        )


def test_the_command_refuses_a_destination_inside_the_repository(
    tmp_path, kpi_rows, settings
):
    repo = tmp_path / "repo"
    settings.BASE_DIR = repo

    with pytest.raises(CommandError, match="dentro del repositorio"):
        call_command(
            "export_for_genesis", out=str(repo / "datos"), group=["kpi"]
        )
    assert not (repo / "datos").exists()


def test_the_command_allows_the_ignored_tmp_folder(
    tmp_path, kpi_rows, settings
):
    repo = tmp_path / "repo"
    settings.BASE_DIR = repo

    call_command(
        "export_for_genesis",
        out=str(repo / "tmp" / "export"),
        group=["kpi"],
        stdout=StringIO(),
    )

    assert Path(repo / "tmp" / "export" / "manifest.json").exists()


def test_the_command_needs_an_action_and_lists_groups():
    with pytest.raises(CommandError, match="Indica --out"):
        call_command("export_for_genesis")
    out = StringIO()

    call_command("export_for_genesis", list=True, stdout=out)

    assert "kpi: datastore.EvaExtraction" in out.getvalue()
    assert "No se exporta portal.AccountLogo" in out.getvalue()


def test_verification_ignores_windows_line_endings(tmp_path, kpi_rows):
    folder, _ = export(tmp_path)
    for path in folder.glob("*.jsonl"):
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))

    assert verify_export(folder) == []
