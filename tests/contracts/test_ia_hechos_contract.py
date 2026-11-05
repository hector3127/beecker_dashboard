"""Contrato de los hechos de la IA IXS (sin llamar al modelo).

Cubre `select_facts`, `question_prefixes` y `validate_claims`.
Se reescribe solo a propósito: `UPDATE_CONTRACTS=1 pytest tests/contracts`.
"""

import json
import os
from pathlib import Path

from apps.daily.services.ixs_ai import question_prefixes, select_facts
from apps.daily.services.ixs_ai_facts import validate_claims

ARCHIVO = Path(__file__).parent / "ia_hechos.json"

ITEMS_ABIERTOS = [
    {
        "id": 100 + n,
        "titulo": f"Tarea {n} de integración",
        "estado": "Active" if n % 3 else "Closed",
        "asignado": "Ana Pérez" if n % 2 else "Luis Gómez",
        "iteracion": "Sprint 1",
        "fechaLimite": f"2026-11-{n:02d}" if n % 4 == 0 else "",
    }
    for n in range(1, 31)
]
CONTEXTO = {
    "proyecto": "IXS.ACM.001",
    "nombreProyecto": "Soporte Acme",
    "fechaCorte": "2026-11-05",
    "avance": {"pct": 42.5},
    "kpis": {"pctCumplimientoFinanciero": 88},
    "presupuesto": {"budget": 1200, "burn": 510.25},
    "fuentesDisponibles": ["azure", "clockify"],
    "etapas": [
        {
            "nombre": "Descubrimiento",
            "inicio": "2026-09-01",
            "fin": "2026-09-30",
            "estado": "Cerrada",
        },
        {
            "nombre": "Construcción",
            "inicio": "2026-10-01",
            "fin": "2026-12-15",
            "estado": "En curso",
        },
    ],
    "workItemsTotal": 30,
    "workItemsSinSeguimiento": 4,
    "workItemsPorEstado": {"Active": 20, "Closed": 10},
    "workItemsPorIteracion": {"Sprint 1": 30},
    "workItemsPorAsignado": {"Ana Pérez": 15, "Luis Gómez": 15, "10": 1},
    "workItems": ITEMS_ABIERTOS,
    "horasClockifyTotal": 510.25,
    "registrosClockifyTotal": 77,
    "horasPorFecha": [
        {"fecha": f"2026-10-{d:02d}", "horas": d / 2} for d in range(1, 11)
    ],
    "recursos": [
        {
            "nombre": "Ana Pérez",
            "rol": "Dev",
            "activo": True,
            "horasEstimadas": 300,
        },
        {
            "nombre": "Luis Gómez",
            "rol": "QA",
            "activo": False,
            "horasEstimadas": 100,
        },
        {"nombre": "Sin horas", "rol": "PM", "horasEstimadas": 0},
    ],
    "horasPorRecurso": [
        {"nombre": "ana pérez", "horas": 310.5},
        {"nombre": "Luis Gómez", "horas": 99.75},
        {"nombre": "Externo", "horas": 5},
    ],
    "vacaciones": [
        {
            "recurso": "Ana Pérez",
            "inicio": "2026-12-20",
            "fin": "2026-12-31",
            "estado": "Aprobada",
        }
    ],
    "compromisos": [
        {
            "actividad": "Entrega UAT",
            "responsable": "Luis",
            "fecha": "2026-11-30",
            "estado": "Abierto",
        }
    ],
    "acciones": [
        {
            "uid": "A1",
            "accion": "Revisar",
            "responsable": "Ana",
            "fechaLimite": "2026-11-10",
            "estado": "Abierta",
        }
    ],
    "raid": [
        {
            "id": 7,
            "tipo": "Risk",
            "titulo": "Retraso proveedor",
            "estado": "Open",
        }
    ],
    "minutas": [
        {
            "tema": "Kickoff",
            "fecha": "2026-09-02",
            "contenido": "Se acordó el alcance",
        }
    ],
    "memoriaAnterior": {
        "fecha": "2026-10-01",
        "analisis": {"resumen": [{"texto": "Previo"}]},
    },
}
PREGUNTAS = [
    "",
    "¿Cuál es el estado general del proyecto?",
    "¿Qué recursos están excedidos?",
    "¿Qué cambió desde el último corte?",
    "¿Qué hay que atender esta semana?",
    "¿Qué bloqueos y retrasos hay?",
    "Dime sobre la tarea 105 y Ana",
    "¿Cómo va la tarea 12?",
]
HECHOS = [
    {"id": "PR-1", "fuente": "dashboard", "texto": "Proyecto X avance 42.5%."},
    {
        "id": "REC-1",
        "fuente": "Recursos / Clockify",
        "texto": "Ana; estimadas 300 h; registradas 310,5 h.",
    },
    {"id": "ET-1", "fuente": "planeación", "texto": "Fase: inicio 2026-09-01."},
]
AFIRMACIONES = [
    ["Avance 42.5% [PR-1]"],
    [{"texto": "Avance 50%", "evidencias": ["PR-1"]}],
    [
        {
            "titulo": "Ana",
            "detalle": "310.5 horas",
            "evidencias": ["REC-1", "PR-1"],
        }
    ],
    [{"texto": "Sin evidencia", "evidencias": ["NO-1"]}],
    [{"texto": "", "evidencias": ["PR-1"]}],
    [{"texto": "x" * 701, "evidencias": ["PR-1"]}],
    [{"texto": "Fase del 2026-09-01", "evidencias": ["ET-1", "ET-1"]}],
    ["a", "b", "c"],
    "no es lista",
    [None, 5, {"evidencias": "PR-1"}],
]


def generar():
    return {
        "prefijos": {p: list(question_prefixes(p)) for p in PREGUNTAS},
        "hechos": {p: select_facts(CONTEXTO, p) for p in PREGUNTAS},
        "afirmaciones": [
            {
                "entrada": a,
                "limite": limite,
                "salida": validate_claims(a, HECHOS, limite),
            }
            for a in AFIRMACIONES
            for limite in (4, 2, 0)
        ],
        "contexto": CONTEXTO,
        "hechos_base": HECHOS,
    }


def test_el_contrato_de_hechos_no_cambia():
    actual = json.loads(json.dumps(generar(), ensure_ascii=False))
    if os.environ.get("UPDATE_CONTRACTS") == "1" or not ARCHIVO.exists():
        ARCHIVO.write_text(
            json.dumps(actual, ensure_ascii=False, indent=1, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
    assert actual == json.loads(ARCHIVO.read_text(encoding="utf-8"))
