"""Ejecutivo AER: paridad, navegación, fuentes vacías y texto seguro."""

import json
from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)
PAGE = "/proyectos/AER.001/"


@pytest.fixture
def fixed_day(portal):
    portal.add_init_script("""{
      const OriginalDate = Date;
      window.Date = class extends OriginalDate {
        constructor(...args) {
          super(...(args.length ? args : ['2026-10-23T18:00:00Z']));
        }
        static now() { return +new OriginalDate('2026-10-23T18:00:00Z'); }
      };
    }""")


@pytest.mark.parametrize("variant", ["full", "empty", "attention"])
@pytest.mark.parametrize("width", [1450, 900, 390])
def test_all_executive_elements_match(
    portal, project_detail, fixed_day, variant, width
):
    _, data = project_detail
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
    portal.set_viewport_size({"width": width, "height": 1000})

    def state():
        expect(portal.locator(".aer-exec-view")).to_be_visible()
        # Extensión y Cierre son botones nuevos de esta pantalla.
        portal.evaluate(
            "document.querySelector('.project-comm-actions')?.remove()"
        )
        return portal.evaluate("""() => [...document.querySelectorAll(
          '.aer-exec-view, .aer-exec-view *')].map(el => {
            const r = el.getBoundingClientRect(), c = getComputedStyle(el);
            return {tag:el.tagName,
              box:['x','y','width','height'].map(k=>Math.round(r[k]*10)/10),
              css:['fontSize','fontWeight','lineHeight','color','backgroundColor',
                'backgroundImage','paddingTop','paddingBottom','marginTop',
                'marginBottom','display','gap'].map(k=>c[k]),
              text:el.textContent.replace(/\\s+/g,'')};
          })""")

    out = Path(f"tmp/migration/project_detail/aer_executive/{variant}/{width}")
    out.mkdir(parents=True, exist_ok=True)
    portal.goto(portal.base + PAGE + "?vista=anterior")
    before = state()
    portal.screenshot(path=str(out / "previous.png"), full_page=True)
    portal.goto(portal.base + PAGE)
    after = state()
    portal.screenshot(path=str(out / "current.png"), full_page=True)
    (out / "differences.json").write_text(
        json.dumps(
            [
                {"index": i, "previous": a, "current": b}
                for i, (a, b) in enumerate(zip(before, after, strict=True))
                if a != b
            ],
            indent=2,
        ),
        encoding="utf-8",
    )
    assert after == before
    expect(portal.locator(".aer-exec-view")).to_have_attribute(
        "data-renderer", "modular"
    )
    assert portal.locator(".aer-exec-view [onclick]").count() == 0
    assert portal.locator("style#aer-dashboard-styles").count() == 0
    assert portal.locator("link#aer-dashboard-styles").count() == 1


@pytest.mark.parametrize(
    "label,tab",
    [
        ("Ver todas las acciones →", "Acciones"),
        ("Próximos hitos / decisiones (30 días)", "Planeación"),
        ("Riesgos y dependencias", "Riesgos"),
    ],
)
def test_links_keep_tab_navigation_with_keyboard(
    portal, project_detail, label, tab
):
    portal.goto(portal.base + PAGE)
    if label.startswith("Ver todas"):
        link = portal.get_by_role("link", name=label)
    else:
        link = (
            portal.locator(".aer-exec-grid3 .aer-card")
            .filter(has_text=label)
            .get_by_role("link", name="Ver todos →")
        )
    link.focus()
    link.press("Enter")
    expect(portal.locator(".aer-tabs .active")).to_have_text(tab)
    portal.locator(".aer-tabs").get_by_role(
        "button", name="Ejecutivo", exact=True
    ).click()
    expect(portal.locator(".aer-exec-view")).to_have_attribute(
        "data-renderer", "modular"
    )


def test_source_text_is_not_html(portal, project_detail):
    _, data = project_detail
    text = '<img src=x onerror="window.executiveInjected=true">'
    data["kpis"]["healthLabel"] = text
    data["riesgos"]["criticos"][0]["riesgo"] = text
    portal.goto(portal.base + PAGE)
    expect(portal.locator(".aer-exec-view")).to_contain_text(text)
    assert portal.locator(".aer-exec-view img").count() == 0
    assert portal.evaluate("window.executiveInjected") is None
