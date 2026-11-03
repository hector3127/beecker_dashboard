"""Shared test inputs and the unchanged DOM/style measurement for the pilot."""

import hashlib
import json
from pathlib import Path

import pytest
from playwright.sync_api import expect

PAGE = "/proyectos/AER.001/"
FIXED_DAY = "2026-10-23T18:00:00Z"


def prepare(data, variant):
    if variant == "empty":
        data.clear()
        data.update(
            {
                "ok": True,
                "backendVersion": "fixture",
                "proyecto": {"id": "AER.001"},
            }
        )
    elif variant == "attention":
        data["kpis"].update(
            {"healthScore": 92, "healthLabel": "Saludable", "consumoPct": 140}
        )
        data["plan"].update(
            {"vencidosAbiertos": 0, "vencenHoy": 2, "pctCerradosATiempo": 0}
        )
        data["plan"]["filas"].extend(
            [
                {
                    "actividad": "Hoy",
                    "finPlan": "2026-10-23",
                    "estado": "Por validar",
                    "dependencia": "Datos",
                },
                {
                    "actividad": "Hito cercano",
                    "finPlan": "2026-10-24",
                    "tipo": "Hito",
                    "dependencia": "DATOS",
                },
            ]
        )


def input_digest(data):
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def state(page):
    expect(page.locator(".aer-exec-view")).to_be_visible()
    page.evaluate("document.fonts.ready")
    return page.evaluate(r"""() => [...document.querySelectorAll(
      '.aer-exec-view, .aer-exec-view *')].map(el => {
        const r = el.getBoundingClientRect(), c = getComputedStyle(el);
        return {tag:el.tagName,
          box:['x','y','width','height'].map(k=>Math.round(r[k]*10)/10),
          css:['fontSize','fontWeight','lineHeight','color','backgroundColor',
            'backgroundImage','paddingTop','paddingBottom','marginTop',
            'marginBottom','display','gap'].map(k=>c[k]),
          text:el.textContent.replace(/\s+/g,'')};
      })""")


@pytest.fixture
def production_site(settings):
    """Permanent comparisons do not depend on reference routes or assets."""
    reference = Path(__file__).resolve().parents[2] / "reference"
    settings.ROOT_URLCONF = "config.urls"
    settings.TEMPLATES = [
        {
            **engine,
            "DIRS": [
                directory
                for directory in engine["DIRS"]
                if Path(directory).resolve() != reference / "templates"
            ],
        }
        for engine in settings.TEMPLATES
    ]
    settings.STATICFILES_DIRS = [
        entry
        for entry in settings.STATICFILES_DIRS
        if Path(
            entry[1] if isinstance(entry, (tuple, list)) else entry
        ).resolve()
        != reference / "static"
    ]
