"""Carga manual acotada: inspección sin red y publicación atómica."""

import copy
import json
from io import StringIO
from unittest.mock import Mock

import pytest
from django.core.management import CommandError, call_command
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.datastore.management.commands import sync_project_sheets as command
from apps.datastore.models import SheetSnapshot, SyncLock
from apps.datastore.services import project_sheets as service
from apps.datastore.services.genesis_export import (
    export_tables,
    resolve_models,
    verify_export,
)
from apps.datastore.services.locks import sync_lock
from core.exceptions import ConfigurationError, SheetsError
from core.sheets.repository import GoogleSheetRepository
from core.sheets.store_read_cache import (
    SHEET_IDS_NAME,
    STORED_SHEETS,
    SnapshotValidationError,
    read_snapshot,
)
from tests.core.test_repository import build_service

pytestmark = pytest.mark.django_db


def valid_rows(name):
    if name == "Comunicados":
        return [["UID", "Fecha", "Título", "", "", "", "", "Proyecto"]]
    return [sorted(service.PROJECT_SHEETS[name])]


class Reader:
    def __init__(self, values):
        self.values = values
        self.prefetched = []
        self.read = []

    def sheet_exists(self, name):
        return name in self.values

    def prefetch(self, names):
        self.prefetched.append(list(names))

    def read_values(self, name):
        self.read.append(name)
        return self.values[name]

    def sheet_ids(self):
        return {name: index for index, name in enumerate(self.values)}


def snapshot(name, rows):
    return SheetSnapshot.objects.create(
        name=name, rows=rows, row_count=len(rows), synced_at=timezone.now()
    )


@pytest.mark.parametrize("name", service.PROJECT_SHEETS)
def test_cada_hoja_admitida_se_guarda_sin_transformar(name):
    rows = valid_rows(name)
    before = copy.deepcopy(rows)
    reader = Reader({name: rows})
    assert service.sync_project_sheets(reader, [name]) == {name: 0}
    assert read_snapshot(name) == before
    assert reader.prefetched == [[name]]
    assert reader.read == [name]
    assert rows == before


def test_el_alcance_manual_no_cambia_las_hojas_automaticas():
    assert len(service.PROJECT_SHEETS) == 12
    assert not set(service.PROJECT_SHEETS) & set(STORED_SHEETS)


def test_seleccion_repetida_no_descarga_dos_veces():
    reader = Reader({"IXS_Acciones": valid_rows("IXS_Acciones")})
    result = service.sync_project_sheets(reader, ["IXS_Acciones"] * 2)
    assert result == {"IXS_Acciones": 0}
    assert reader.read == ["IXS_Acciones"]


@pytest.mark.parametrize(
    "names", [[], ["MPB"], ["DataRevenue"], ["IXS_Acciones", "Otra"]]
)
def test_rechaza_hojas_ajenas_antes_de_leer(names):
    reader = Mock()
    with pytest.raises(service.ProjectSheetError, match="hoja de proyectos"):
        service.sync_project_sheets(reader, names)
    reader.sheet_exists.assert_not_called()
    assert SheetSnapshot.objects.count() == 0


@pytest.mark.parametrize(
    "rows", [[], [["Otra"]], [["UID", "ID_Proyecto"]], [["#REF!"]]]
)
def test_copia_invalida_conserva_el_corte_completo_anterior(rows):
    old = snapshot("IXS_Acciones", valid_rows("IXS_Acciones"))
    before = list(SheetSnapshot.objects.values())
    with pytest.raises((service.ProjectSheetError, SnapshotValidationError)):
        service.sync_project_sheets(
            Reader({"IXS_Acciones": rows}), ["IXS_Acciones"]
        )
    assert list(SheetSnapshot.objects.values()) == before
    assert read_snapshot(old.name) == old.rows


def test_si_falta_una_hoja_no_borra_la_copia_previa_ni_descarga_otras():
    snapshot("IXS_Acciones", [["dato anterior"]])
    before = list(SheetSnapshot.objects.values())
    reader = Reader({"Comunicados": valid_rows("Comunicados")})
    with pytest.raises(service.ProjectSheetError, match="IXS_Acciones"):
        service.sync_project_sheets(reader, ["Comunicados", "IXS_Acciones"])
    assert not reader.prefetched
    assert list(SheetSnapshot.objects.values()) == before


def test_valida_todo_antes_de_guardar_el_primer_elemento(monkeypatch):
    save = Mock()
    monkeypatch.setattr(service, "save_snapshot", save)
    values = {
        "IXS_Acciones": valid_rows("IXS_Acciones"),
        "Comunicados": [["ID", "Título"]],
    }
    with pytest.raises(service.ProjectSheetError):
        service.sync_project_sheets(Reader(values), values)
    save.assert_not_called()


def test_error_de_red_no_reemplaza_copias(monkeypatch):
    snapshot("IXS_Acciones", valid_rows("IXS_Acciones"))
    before = list(SheetSnapshot.objects.values())
    reader = Reader({"IXS_Acciones": valid_rows("IXS_Acciones")})
    monkeypatch.setattr(reader, "prefetch", Mock(side_effect=SheetsError()))
    with pytest.raises(SheetsError):
        service.sync_project_sheets(reader, ["IXS_Acciones"])
    assert list(SheetSnapshot.objects.values()) == before


def test_error_al_guardar_revierte_todas_las_hojas(monkeypatch):
    snapshot("IXS_Acciones", [["anterior"]])
    snapshot("Comunicados", [["anterior"]])
    before = list(SheetSnapshot.objects.order_by("name").values())
    original = service.save_snapshot

    def fail_on_second(name, rows):
        if name == "Comunicados":
            raise RuntimeError("Fallo simulado")
        original(name, rows)

    monkeypatch.setattr(service, "save_snapshot", fail_on_second)
    values = {
        name: valid_rows(name) for name in ["IXS_Acciones", "Comunicados"]
    }
    with pytest.raises(RuntimeError, match="simulado"):
        service.sync_project_sheets(Reader(values), values)
    assert list(SheetSnapshot.objects.order_by("name").values()) == before


def test_carga_solo_lo_elegido_y_conserva_otras_hojas():
    other = snapshot("MPB", [["horas"], [123]])
    snapshot("IXS_Cliente_Info", [["corte anterior"]])
    reader = Reader({"IXS_Acciones": valid_rows("IXS_Acciones")})
    service.sync_project_sheets(reader, ["IXS_Acciones"])
    other.refresh_from_db()
    assert other.rows == [["horas"], [123]]
    assert read_snapshot("IXS_Cliente_Info") == [["corte anterior"]]
    assert read_snapshot(SHEET_IDS_NAME) == {"IXS_Acciones": 0}


def test_catalogo_inconsistente_impide_publicar(monkeypatch):
    reader = Reader({"IXS_Acciones": valid_rows("IXS_Acciones")})
    monkeypatch.setattr(reader, "sheet_ids", lambda: {})
    with pytest.raises(service.ProjectSheetError, match="catálogo"):
        service.sync_project_sheets(reader, ["IXS_Acciones"])
    assert not SheetSnapshot.objects.exists()


def test_registros_y_json_se_guardan_sin_reescribirlos():
    rows = [
        ["UID", "ID_Proyecto", "DatosJSON"],
        ["a", "AMK.001_S1", '{"notas":" Texto ","horas":0}'],
    ]
    assert service.sync_project_sheets(
        Reader({"IXS_Acciones": rows}), ["IXS_Acciones"]
    ) == {"IXS_Acciones": 1}
    assert read_snapshot("IXS_Acciones") == rows


def test_inspeccion_predeterminada_no_pide_credenciales_ni_escribe(monkeypatch):
    factory = Mock(side_effect=AssertionError("No crear cliente Google"))
    monkeypatch.setattr(command, "build_sheet_repository", factory)
    snapshot(SHEET_IDS_NAME, {"IXS_Acciones": 12})
    before = list(SheetSnapshot.objects.values())
    output = StringIO()
    with CaptureQueriesContext(connection) as queries:
        call_command("sync_project_sheets", stdout=output)
    assert "sin copia local" in output.getvalue()
    assert "sin conexión a Google" in output.getvalue()
    assert "Pendientes_Minutas" in output.getvalue()
    assert list(SheetSnapshot.objects.values()) == before
    assert not SyncLock.objects.exists()
    assert all(
        query["sql"].lstrip().upper().startswith("SELECT") for query in queries
    )
    factory.assert_not_called()


def test_inspeccion_acotada_muestra_fecha_original(monkeypatch):
    factory = Mock(side_effect=AssertionError("No consultar origen"))
    monkeypatch.setattr(command, "build_sheet_repository", factory)
    copy = snapshot("IXS_Acciones", valid_rows("IXS_Acciones"))
    output = StringIO()
    call_command("sync_project_sheets", hoja=["IXS_Acciones"], stdout=output)
    assert copy.synced_at.isoformat() in output.getvalue()
    assert "Pendientes_Minutas" not in output.getvalue()
    assert "origen sin confirmar" in output.getvalue()


def test_aplicar_exige_y_reutiliza_el_candado_de_hojas(monkeypatch):
    factory = Mock()
    monkeypatch.setattr(command, "build_sheet_repository", factory)
    with sync_lock("hojas", 15 * 60):
        with pytest.raises(CommandError, match="Otra sincronización"):
            call_command("sync_project_sheets", aplicar=True, stdout=StringIO())
    factory.assert_not_called()


def test_aplicar_usa_cliente_sin_cache_y_solo_el_alcance_elegido(monkeypatch):
    reader = Reader({"IXS_Acciones": valid_rows("IXS_Acciones")})
    factory = Mock(return_value=reader)
    monkeypatch.setattr(command, "build_sheet_repository", factory)
    output = StringIO()
    call_command(
        "sync_project_sheets",
        hoja=["IXS_Acciones"],
        aplicar=True,
        stdout=output,
    )
    factory.assert_called_once_with(use_store=False)
    assert read_snapshot("IXS_Acciones") == valid_rows("IXS_Acciones")
    assert not SyncLock.objects.exists()
    assert "0 registros guardados" in output.getvalue()


def test_configuracion_faltante_libera_candado_y_conserva_copias(monkeypatch):
    factory = Mock(side_effect=ConfigurationError("Falta configuración"))
    monkeypatch.setattr(command, "build_sheet_repository", factory)
    with pytest.raises(CommandError, match="Falta configuración"):
        call_command("sync_project_sheets", aplicar=True, stdout=StringIO())
    assert not SyncLock.objects.exists()
    assert not SheetSnapshot.objects.exists()


def test_repositorio_real_solo_usa_lecturas_y_un_lote():
    values = {name: valid_rows(name) for name in service.PROJECT_SHEETS}
    client = build_service(values)
    repository = GoogleSheetRepository(client, "sheet-test")
    result = service.sync_project_sheets(repository, values)
    assert set(result) == set(service.PROJECT_SHEETS)
    google = client.spreadsheets.return_value
    assert google.values.return_value.batchGet.call_count == 1
    google.values.return_value.update.assert_not_called()
    google.batchUpdate.assert_not_called()


def test_las_copias_nuevas_entran_en_el_export_existente(tmp_path):
    values = {name: valid_rows(name) for name in service.PROJECT_SHEETS}
    service.sync_project_sheets(Reader(values), values)
    folder = tmp_path / "hojas"
    manifest = export_tables(
        resolve_models(["hojas"], []),
        folder,
        created_at=timezone.now(),
        source={"engine": "test"},
    )
    verify_export(folder)
    assert len(manifest["tables"]) == 1
    assert manifest["tables"][0]["rows"] == 13
    rows = [
        json.loads(line)
        for line in (folder / "datastore.SheetSnapshot.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert {row["name"] for row in rows} == set(values) | {SHEET_IDS_NAME}
