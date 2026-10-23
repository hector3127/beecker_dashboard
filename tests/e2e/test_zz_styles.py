"""Estilos calculados para comparar disenos (temporal)."""

import json
import os

import pytest

pytestmark = pytest.mark.django_db(transaction=True)

PATH = os.environ.get("ST_PATH", "/operativa/")
SELECTORS = json.loads(os.environ.get("ST_SELECTORS", "{}"))
PROPS = [
    "fontSize",
    "fontWeight",
    "color",
    "backgroundColor",
    "paddingTop",
    "paddingRight",
    "paddingBottom",
    "paddingLeft",
    "marginTop",
    "marginBottom",
    "borderRadius",
    "borderTopWidth",
    "borderTopColor",
    "borderBottomColor",
    "gap",
    "height",
    "width",
    "lineHeight",
    "display",
    "letterSpacing",
]


def test_styles(datos, portal):
    portal.set_viewport_size({"width": 1450, "height": 1000})
    portal.goto(portal.base + PATH)
    portal.wait_for_timeout(3000)
    out = {}
    for label, selector in SELECTORS.items():
        out[label] = portal.evaluate(
            """([sel, props]) => {
              const el = document.querySelector(sel);
              if (!el) return null;
              const cs = getComputedStyle(el);
              const r = el.getBoundingClientRect();
              const o = {};
              for (const p of props) o[p] = cs[p];
              o.box = [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)];
              return o;
            }""",
            [selector, PROPS],
        )
    with open(
        os.environ.get("ST_OUT", "styles.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
