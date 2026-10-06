"""Pruebas de la validacion de registros de Clockify."""

import json
from datetime import datetime
from types import SimpleNamespace

from apps.clockify.services import entry_validation as validation
from core.exceptions import DashboardError
from core.integrations.claude_client import ClaudeClient
from core.time_entries.models import TimeEntry
from tests.fakes import InMemorySheetRepository

NOW = datetime(2026, 10, 3, 12, 0)


def make_entry(entry_id, name, start, end, tags=("S1",), hours=1.5):
    """Registro con inicio y fin locales."""
    return TimeEntry(
        entry_id=entry_id,
        project_id="P1",
        resource_name=name,
        entry_date=start,
        duration_hours=hours,
        is_billable=True,
        costing_rate=0,
        description=f"desc {entry_id}",
        tags=tuple(tags),
        started_at=start,
        ended_at=end,
    )


def test_area_rules_sheet_is_created_with_examples():
    repo = InMemorySheetRepository({})

    assert validation.list_area_rules(repo, repo) == {"ok": True, "areas": []}
    assert [row[0] for row in repo.sheets["Areas_Reglas"]] == [
        "Area",
        "Developer",
        "QA",
        "Arquitecto",
    ]

    areas = validation.list_area_rules(repo, repo)["areas"]
    assert [area["area"] for area in areas] == ["Developer", "QA", "Arquitecto"]


def test_save_and_delete_area_rule():
    repo = InMemorySheetRepository({"Areas_Reglas": [["Area", "Regla_Texto"]]})

    assert validation.save_area_rule(repo, repo, "  ", "x") == {
        "ok": False,
        "error": "Falta el nombre del área.",
    }
    assert validation.save_area_rule(repo, repo, " QA ", " uno ")["ok"]
    assert validation.save_area_rule(repo, repo, "qa", "dos")["ok"]
    assert repo.sheets["Areas_Reglas"][1:] == [["QA", "dos"]]

    assert validation.delete_area_rule(repo, repo, "Dev") == {
        "ok": False,
        "error": 'No se encontró el área "Dev".',
    }
    assert validation.delete_area_rule(repo, repo, " qa ") == {"ok": True}
    assert repo.sheets["Areas_Reglas"] == [["Area", "Regla_Texto"]]


def test_clear_validations_keeps_headers():
    repo = InMemorySheetRepository(
        {
            "Validaciones_IA_Clockify": [
                list(validation.VALIDATIONS_HEADERS),
                ["e1", True, "ok", NOW],
                ["e2", False, "no", NOW],
            ],
        },
    )

    assert validation.clear_validations(repo, repo) == {"ok": True}
    assert repo.sheets["Validaciones_IA_Clockify"] == [
        list(validation.VALIDATIONS_HEADERS),
    ]


def test_bad_entries_flags_tags_and_schedule():
    resources = [
        {"Proyecto": "P1", "Nombre del recurso": "Ana López", "Posición": "QA"},
        {"Proyecto": "P2", "Nombre del recurso": "Beto", "Posición": "Dev"},
    ]
    entries = [
        make_entry(
            "ok", "Ana López", datetime(2026, 9, 1, 9), datetime(2026, 9, 1, 18)
        ),
        make_entry(
            "tag",
            "ana lopez",
            datetime(2026, 9, 2, 9),
            datetime(2026, 9, 2, 10),
            tags=(),
        ),
        make_entry(
            "late", "Beto", datetime(2026, 9, 3, 18), datetime(2026, 9, 3, 19)
        ),
        make_entry("both", "Beto", datetime(2026, 9, 4, 7), None, tags=()),
    ]
    hours = SimpleNamespace(entries=entries, project_name="Clockify P1")

    result = validation.bad_entries(" P1 ", resources, lambda project: hours)

    assert result["contadores"] == {
        "sinTag": 2,
        "fueraHorario": 2,
        "reglaArea": 0,
    }
    assert result["proyectoClockify"] == "Clockify P1"
    assert [alert["fecha"] for alert in result["alertas"]] == [
        "2026-09-02",
        "2026-09-03",
        "2026-09-04",
    ]
    assert result["alertas"][0]["area"] == "QA"
    assert result["alertas"][1]["area"] == "Sin área asignada"
    assert result["alertas"][1]["problemas"] == [
        {
            "tipo": "fuera_horario",
            "color": "rojo",
            "mensaje": "Fuera de horario (18:00 - 19:00)",
        },
    ]
    assert (
        result["alertas"][2]["problemas"][1]["mensaje"]
        == "Fuera de horario (7:00 - ?)"
    )


def test_bad_entries_returns_clockify_error():
    def fail(project):
        raise DashboardError("No se encontró el proyecto en Clockify.")

    result = validation.bad_entries("P1", [], fail)

    assert result["ok"] is False
    assert result["alertas"] == []
    assert result["contadores"] == {
        "sinTag": 0,
        "fueraHorario": 0,
        "reglaArea": 0,
    }


class FakeSession:
    """Respuesta fija de Claude; guarda los cuerpos enviados."""

    def __init__(self, status, text):
        self.status = status
        self.text = text
        self.posts = []

    def post(self, url, json, headers, timeout):
        self.posts.append(json)
        return SimpleNamespace(status_code=self.status, text=self.text)


def build_context(repo, session, api_key="sk-test"):
    return validation.AreaRuleContext(
        reader=repo,
        writer=repo,
        api_key=api_key,
        model="claude-haiku-4-5-20251001",
        build_client=lambda: ClaudeClient(api_key, session),
        now=NOW,
    )


def detailed(entry_id="e9"):
    return validation.DetailedEntry(
        entry_id, "Ana", "QA", "", None, None, 0.5, ()
    )


def test_area_rule_asks_claude_and_saves_result():
    repo = InMemorySheetRepository({})
    answer = {
        "content": [
            {
                "type": "text",
                "text": 'Ok {"cumple": false, "motivo": "Sin detalle"}',
            }
        ]
    }
    session = FakeSession(200, json.dumps(answer))

    result = validation.validate_area_rule(
        build_context(repo, session), detailed(), "Regla QA", {}
    )

    assert result == {"cumple": False, "motivo": "Sin detalle"}
    prompt = session.posts[0]["messages"][0]["content"]
    assert session.posts[0]["max_tokens"] == 150
    assert 'el área "QA":\n"Regla QA"' in prompt
    assert '- Descripción del registro: "(sin descripción)"' in prompt
    assert "- Duración: 0.5 horas\n- Tags asignados: (ninguno)" in prompt
    assert repo.sheets["Validaciones_IA_Clockify"][1] == [
        "e9",
        False,
        "Sin detalle",
        NOW,
    ]


def test_area_rule_skips_without_rule_key_or_valid_answer():
    repo = InMemorySheetRepository({})
    session = FakeSession(
        200, json.dumps({"content": [{"type": "text", "text": "nada"}]})
    )
    done = {"e9": {"cumple": True, "motivo": "ya"}}

    assert (
        validation.validate_area_rule(
            build_context(repo, session), detailed(), "", {}
        )
        is None
    )
    assert (
        validation.validate_area_rule(
            build_context(repo, session), detailed(), "R", done
        )
        == done["e9"]
    )
    assert (
        validation.validate_area_rule(
            build_context(repo, session, ""), detailed(), "R", {}
        )
        is None
    )
    assert (
        validation.validate_area_rule(
            build_context(repo, session), detailed(), "R", {}
        )
        is None
    )
    assert (
        validation.validate_area_rule(
            build_context(repo, FakeSession(500, "{}")), detailed(), "R", {}
        )
        is None
    )


def test_validations_map_reads_saved_results():
    repo = InMemorySheetRepository(
        {
            "Validaciones_IA_Clockify": [
                list(validation.VALIDATIONS_HEADERS),
                ["e1", "TRUE", "bien", NOW],
                ["e2", False, "", NOW],
                ["", True, "x", NOW],
            ],
        },
    )

    assert validation.validations_map(repo, repo) == {
        "e1": {"cumple": True, "motivo": "bien"},
        "e2": {"cumple": False, "motivo": ""},
    }
