"""Regresiones de respuestas contextualizadas y verificadas."""

from types import SimpleNamespace

from apps.daily.services.ixs_ai import (
    answer_result,
    effort_evidence,
    fact_rank,
    question_prefixes,
)


def test_question_intent_prioritizes_relevant_sources():
    assert "REC-" in question_prefixes("¿Qué recursos están excedidos?")
    assert "MEM-" in question_prefixes("¿Qué cambió desde el corte?")
    assert fact_rank({"id": "ACC-1"}, "Qué debo atender esta semana") == -1


def test_numbered_recommendation_is_not_dropped_for_list_number():
    facts = [{"id": "CL-RES", "fuente": "Clockify", "texto": "105.25 h"}]
    result = answer_result(
        SimpleNamespace(model="test"),
        "1. Revisar las 105.25 h registradas. [CL-RES]",
        facts,
    )
    assert result["respuestaVerificada"]
    assert "Revisar" in result["texto"]


def test_invalid_answer_does_not_hide_behind_single_progress_fact():
    facts = [
        {"id": "PR-1", "fuente": "dashboard", "texto": "avance 55.2%"},
        {"id": "CL-RES", "fuente": "Clockify", "texto": "105.25 h"},
    ]
    result = answer_result(
        SimpleNamespace(model="test"), "999 h [CL-RES]", facts
    )
    assert not result["respuestaVerificada"]
    assert "No se pudo validar" in result["texto"]
    assert "[PR-1]" in result["texto"] and "[CL-RES]" in result["texto"]
    assert "999" not in result["texto"]


def test_effort_difference_keeps_project_scope_and_missing_estimates():
    facts = effort_evidence(
        {
            "recursos": [
                {"nombre": "Ana", "horasEstimadas": 22},
                {"nombre": "Luis", "horasEstimadas": 0},
            ],
            "horasPorRecurso": [
                {"nombre": "Ana", "horas": 36.25},
                {"nombre": "Luis", "horas": 8},
            ],
        }
    )
    assert len(facts) == 1
    assert "-14.25 h" in facts[0]["texto"]
    assert "ID consultado" in facts[0]["texto"]
