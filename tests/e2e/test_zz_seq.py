import json
import os

import pytest

from tests.portal.test_views import stub_history

pytestmark = pytest.mark.django_db(transaction=True)

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
    "borderTopColor",
    "borderBottomColor",
    "gap",
    "lineHeight",
    "display",
    "letterSpacing",
    "boxShadow",
    "textDecorationLine",
    "fontFamily",
    "fontVariantNumeric",
    "textTransform",
    "verticalAlign",
    "whiteSpace",
    "boxSizing",
    "height",
    "width",
    "minHeight",
    "fontStyle",
    "textAlign",
]


def test_seq(monkeypatch, datos, portal):
    stub_history(monkeypatch)
    if os.environ.get("SEQ_COSTS"):
        projects = [
            {
                "id": "AER.001",
                "hours": 120.5,
                "cost": 8000,
                "revenue": 20000,
                "margin": 60,
                "gross_profit": 12000,
                "complete": True,
            },
            {
                "id": "AER.002",
                "hours": 40,
                "cost": 3000,
                "revenue": 3500,
                "margin": 14.2,
                "gross_profit": 500,
                "complete": False,
                "margin_provisional": True,
            },
            {
                "id": "AER.003",
                "hours": None,
                "cost": None,
                "revenue": None,
                "margin": None,
                "gross_profit": None,
                "complete": False,
                "error": "Consulta pendiente",
            },
            {
                "id": "AER.004",
                "hours": None,
                "cost": None,
                "revenue": 500,
                "margin": None,
                "gross_profit": None,
                "complete": False,
                "future": True,
            },
        ]
        summary = {
            "projects": projects,
            "cost": 11000,
            "complete": False,
            "pending": 1,
            "future": 1,
            "deduplicated_entries": 321,
            "band_month": "2026-10",
            "prepared_details": {},
        }
        detail = {
            "id": "AER.001",
            "hours": 120.5,
            "cost": 8000,
            "revenue": 20000,
            "margin": 60,
            "gross_profit": 12000,
            "complete": True,
            "clockify_id": "AER.001",
            "scope_start": "2026-01-01",
            "scope_end": "2026-10-22",
            "people": [
                {
                    "name": "Ana",
                    "hours": 100,
                    "band": "A2",
                    "band_month": "2026-10",
                    "rate": 20,
                    "cost": 2000,
                }
            ],
            "sprints": [],
        }
        monkeypatch.setattr(
            "apps.portal.services.executive_refresh.request_refresh",
            lambda **k: {"state": "idle"},
        )
        monkeypatch.setattr(
            "apps.portal.services.cost_audit_cache.prepared_summary",
            lambda account: summary,
        )
        monkeypatch.setattr(
            "apps.portal.services.cost_audit_cache.prepared_detail",
            lambda pid, account: detail,
        )
    if os.environ.get("SEQ_COMERCIAL"):
        from unittest.mock import MagicMock

        headers = [
            "Account Name",
            "Opportunity Name",
            "Delivery Manager",
            "Opportunity Stage",
            "Fecha de cierre - Diario",
            "Service Type",
            "Invoice Name",
            "Total Hours",
            "Duration_Service",
            "Valor",
            "Currency Opportunity",
            "Account",
            "Fecha inicio",
            "Stage",
            "CIO",
            "Calculadora",
            "Arq",
            "En tiempo",
            "Observaciones",
            "Estimación",
            "Fecha último seguimiento",
            "Probabilidad",
        ]

        def row(acc, op, stage, close, service, hours, value, prob):
            return [
                acc,
                op,
                "Ana",
                stage,
                close,
                service,
                "I",
                hours,
                "12",
                value,
                "USD",
                acc,
                "2026-01-05",
                "Prospectos",
                "Si",
                "Si",
                "No",
                "Nota",
                "",
                "100",
                "2026-10-01",
                prob,
            ]

        data = [
            headers,
            row(
                "ACME",
                "Portal",
                "Confirmed (Pipeline)",
                "2026-11-15",
                "SaaS",
                "120",
                30000,
                "90",
            ),
            row(
                "ACME",
                "App",
                "Discovery (Pipeline)",
                "2026-12-15",
                "AER",
                "80",
                20000,
                "70",
            ),
            row(
                "Beta",
                "ERP",
                "Closed Won",
                "2026-03-10",
                "T&M",
                "200",
                50000,
                "100",
            ),
            row(
                "Beta",
                "CRM",
                "Proposal (Pipeline)",
                "2026-12-20",
                "SaaS",
                "60",
                10000,
                "50",
            ),
            row(
                "Gamma",
                "Bots",
                "Discovery (Pipeline)",
                "2026-11-30",
                "RaaS",
                "40",
                8000,
                "70",
            ),
            row("Delta", "BI", "Lost", "2026-02-02", "AER", "10", 1000, "0"),
        ]
        factory = MagicMock()
        factory.return_value.read_values.return_value = data
        monkeypatch.setattr(
            "apps.portal.services.commercial_view.build_sheet_repository",
            factory,
        )
    if os.environ.get("SEQ_HOURS"):
        months = []
        for i, label in enumerate(
            [
                "Mayo 2026",
                "Junio 2026",
                "Julio 2026",
                "Agosto 2026",
                "Septiembre 2026",
                "Octubre 2026",
            ]
        ):
            projects = [
                {
                    "id": "2",
                    "name": "Portal Pacientes",
                    "client": "Clinica Sur",
                    "service": "T&M",
                    "project_budget": 100,
                    "billable": 20 + i * 5,
                    "operational": 4 + i,
                    "commercial": 2,
                    "total": 26 + i * 6,
                },
                {
                    "id": "3",
                    "name": "HIS",
                    "client": "ACME",
                    "service": "AER",
                    "project_budget": None,
                    "billable": 10,
                    "operational": 1,
                    "commercial": 0,
                    "total": 11,
                },
            ]
            months.append(
                {
                    "label": label,
                    "total": sum(p["total"] for p in projects),
                    "budget": 60 + i * 5,
                    "budget_missing": 1,
                    "billable": sum(p["billable"] for p in projects),
                    "operational": sum(p["operational"] for p in projects),
                    "commercial": sum(p["commercial"] for p in projects),
                    "projects": projects,
                }
            )
        data = {
            "monthly": months,
            "complete": False,
            "error": "Falta HIS.",
            "monthly_has_data": True,
        }
        monkeypatch.setattr(
            "apps.portal.services.operational_sources.manager_monthly_history",
            lambda *a, **k: data,
        )
    portal.set_viewport_size({"width": 1450, "height": 1000})
    urls = os.environ["SEQ_URLS"].split(";")
    for u in urls[:-1]:
        portal.context.request.get(portal.base + u)
    portal.goto(portal.base + urls[-1])
    portal.wait_for_timeout(3000)
    if os.environ.get("SEQ_OUT"):
        portal.screenshot(path=os.environ["SEQ_OUT"], full_page=True)
    sels = json.loads(os.environ.get("SEQ_SEL", "{}"))
    out = {}
    for label, selector in sels.items():
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
    if sels:
        with open(os.environ["SEQ_JSON"], "w", encoding="utf-8") as f:
            json.dump(out, f, indent=1)
