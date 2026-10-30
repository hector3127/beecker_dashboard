"""IA AER: paridad de pantalla, formularios, lectura y controles seguros."""

import json
from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_ai_sources import enter
from tests.e2e.test_aer_ai_sources import ia as ia
from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_effort import state
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def rich(ia):
    _, responses, _ = ia
    responses["analisis"]["resultado"] = {
        "analisis": {
            "resumen": ["Proyecto estable", "Revisar compromisos"],
            "recomendaciones": [
                {
                    "titulo": "Acordar fechas",
                    "detalle": "Validar el plan",
                    "area": "Planeación",
                }
            ],
        },
        "guardadoEn": "2026-10-22 14:30",
        "persistido": False,
    }
    responses["resumen"]["resumen"] = {
        "contenido": "***Estado del proyecto***\n**Avance:** estable\n"
        "- Revisar acuerdos\n<script>alert(1)</script>",
        "guardado": "22/10/2026 14:30",
    }
    responses["minutas"]["filas"] = [
        {
            "tema": f"Comité {i}",
            "fecha": "2026-10-21",
            "guardado": "22/10/2026",
            "contenido": "**RESUMEN**\nAvance estable\n\n"
            "**PENDIENTES**\nDetalle " + "largo " * 35,
        }
        for i in range(7)
    ]
    responses["config"]["config"] = {
        "folderUrl": "https://drive.google.com/drive/folders/demo",
        "nombreFrecuente": "Comité",
        "nombreBusqueda": "ACME",
        "promptMinuta": "Prompt <texto> & detalles",
    }
    responses["archivos"] = {
        "ok": True,
        "totalEncontradas": 7,
        "carpeta": "ACME",
        "busqueda": "ACME",
        "patron": "Comité",
        "limitado": True,
        "filas": [
            {
                "id": f"f{i}",
                "nombre": f"Transcripción {i}",
                "fecha": "21/10/2026",
                "legible": i < 6,
                "url": "https://example.test/doc",
            }
            for i in range(7)
        ],
    }
    return ia


def compare(page, label, selector, prepare):
    directory = Path("tmp/migration/project_detail/aer_ai_view") / label
    directory.mkdir(parents=True, exist_ok=True)
    snapshots = []
    for previous in [True, False]:
        enter(page, previous)
        prepare(page)
        page.mouse.move(0, 0)
        # Filling a low field scrolls the page; compare at the same viewport.
        page.evaluate("""async () => {
          window.scrollTo(0, 0);
          await new Promise(requestAnimationFrame);
          await new Promise(requestAnimationFrame);
        }""")
        snapshots.append(
            (
                state(page, selector),
                page.locator(selector.split(",")[0]).first.evaluate(
                    "r=>[...r.querySelectorAll('input,select,textarea')].map(x=>[x.id,x.value,x.checked])"
                ),
            )
        )
        page.screenshot(
            path=str(directory / ("old.png" if previous else "new.png")),
            full_page=True,
        )
    differences = [
        (i, a, b)
        for i, (a, b) in enumerate(
            zip(snapshots[0][0], snapshots[1][0], strict=True)
        )
        if a != b
    ]
    (directory / "differences.json").write_text(
        json.dumps(differences, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    assert snapshots[0] == snapshots[1], differences[:2]


def test_history_selection_questions_and_safe_text(portal, rich, fixed_day):
    payload = '<img src=x onerror="alert(1)">'
    rich[1]["minutas"]["filas"][0]["tema"] = payload
    rich[1]["archivos"]["filas"][0]["nombre"] = payload
    rich[1]["archivos"]["filas"][0]["url"] = "javascript:alert(1)"
    enter(portal)
    portal.evaluate("""() => {
      const fail=()=>{throw Error('old renderer')};
      aerIAVista=aerIAMinutasTable=aerIAArchivosEnIA=aerIAKpi=aerIAMetro=
        aerIAHtmlLine=aerIAChatResumenHTML=aerIAFormatoResumen=
        aerIAResumenDeUltimaMinuta=_aerModal=fail;
      _aerRenderTab();
    }""")
    assert portal.locator(".aeri img, .aeri script").count() == 0
    expect(portal.locator(".aeri-driveitem a").first).to_have_attribute(
        "href", "#"
    )
    assert portal.locator(".aeri-minuta-row").count() == 5
    portal.get_by_role("button", name="Ver historial →", exact=True).click()
    assert portal.locator(".aeri-minuta-row").count() == 7
    checks = portal.locator(".aeri-driveitem input")
    for i in range(5):
        checks.nth(i).check()
    checks.nth(5).click()
    expect(checks.nth(5)).not_to_be_checked()
    assert len(portal.evaluate("aerIAState.seleccion")) == 5
    portal.get_by_role(
        "button", name="Ocultar resultados ×", exact=True
    ).click()
    assert portal.locator(".aeri-driveitem").count() == 0
    portal.get_by_role(
        "button", name="Mostrar resultados ▾", exact=True
    ).click()
    expect(
        portal.get_by_role(
            "button", name="¿Quién está sobreasignado?", exact=True
        )
    ).to_be_visible()
    portal.get_by_role(
        "button", name="¿Quién está sobreasignado?", exact=True
    ).click()
    expect(portal.locator("#aeri-question")).to_have_value(
        "¿Quién está sobreasignado?"
    )
    expect(portal.locator("#aeri-question")).to_be_focused()
    portal.locator(".aeri-minuta-row").first.focus()
    portal.keyboard.press("Enter")
    expect(portal.locator("#aeri-minuta-read")).to_be_visible()
    portal.get_by_role("button", name="Cerrar minuta", exact=True).click()
    portal.evaluate("aerIACorreo()")
    expect(portal.locator("#aeri-mail-in")).to_be_visible()


def test_recommendation_opens_migrated_action_and_preserves_text(
    portal, rich, fixed_day
):
    enter(portal)
    portal.locator(".aeri-rec button").click()
    expect(portal.locator("#aa-a")).to_have_value("Acordar fechas")
    expect(portal.locator("#aa-n")).to_have_value("Validar el plan")
