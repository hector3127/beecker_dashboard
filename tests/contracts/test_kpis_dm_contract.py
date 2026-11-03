"""Contrato de la API de KPIs de Delivery Managers.

Guarda la respuesta completa de `GET /api/v1/screens/kpis-dm/` para entradas
fijas y la compara campo por campo. Es el contrato que el módulo de Genesis
tiene que devolver: si una cifra, un nombre de campo o un nulo cambian, esta
prueba falla.

Los archivos de `kpis_dm/` se reescriben solo a propósito, revisando el cambio:
`UPDATE_CONTRACTS=1 pytest tests/contracts`. En esta pantalla `meta` suele
venir vacío, así que solo se comparan sus claves.
"""

import json
import os
from pathlib import Path

import pytest

from tests.portal.test_kpis_api import history  # noqa: F401

pytestmark = pytest.mark.django_db

URL = "/api/v1/screens/kpis-dm/"
CONTRATOS = Path(__file__).parent / "kpis_dm"

CASOS = {
    "anio_por_omision": {},
    "corte_con_dm": {"corte": "2026-09-30", "dm": ["Ana"]},
    "anios_independientes": {
        "corte": "2026-02-15",
        "chart_year": "2025",
        "history_year": "2026",
    },
    "sin_dms": {"dm": "__none__"},
    "dos_dms": {"dm": ["Ana", "Beto"]},
}

ERRORES = {
    "error_corte_futuro": {"corte": "2027-01-01"},
    "error_anio_invalido": {"history_year": "bad"},
}


def normalizar(cuerpo: object) -> object:
    texto = json.dumps(cuerpo, sort_keys=True, ensure_ascii=False)
    return json.loads(texto)


def guardar_o_leer(nombre: str, actual: object) -> object:
    ruta = CONTRATOS / f"{nombre}.json"
    if os.environ.get("UPDATE_CONTRACTS") == "1":
        CONTRATOS.mkdir(exist_ok=True)
        texto = json.dumps(actual, sort_keys=True, ensure_ascii=False, indent=2)
        ruta.write_text(texto + "\n", encoding="utf-8", newline="\n")
    assert ruta.exists(), (
        f"Falta {ruta.name}: corre con UPDATE_CONTRACTS=1 y revisa el cambio"
    )
    return json.loads(ruta.read_text(encoding="utf-8"))


@pytest.mark.parametrize("nombre", CASOS)
def test_la_respuesta_coincide_con_el_contrato(client, nombre):
    respuesta = client.get(URL, CASOS[nombre])
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert set(cuerpo) == {"data", "meta"}

    actual = normalizar(
        {"data": cuerpo["data"], "meta_claves": sorted(cuerpo["meta"])}
    )

    assert actual == guardar_o_leer(nombre, actual)


@pytest.mark.parametrize("nombre", ERRORES)
def test_los_errores_de_validacion_coinciden_con_el_contrato(client, nombre):
    respuesta = client.get(URL, ERRORES[nombre])
    assert respuesta.status_code == 400

    actual = normalizar(
        {"status": respuesta.status_code, "cuerpo": respuesta.json()}
    )

    assert actual == guardar_o_leer(nombre, actual)
