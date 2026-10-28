"""Native EVA cut, responsive controls and extraction polling on real routes."""

from pathlib import Path

import pytest
from django.utils import timezone
from playwright.sync_api import expect

from apps.datastore.models import (
    EvaAzureSource,
    EvaExtraction,
    EvaScopeSnapshot,
)
from tests.portal import test_eva_native as native_fixtures

observed = native_fixtures.observed

pytestmark = [pytest.mark.usefixtures("transactional_db", "enforced_csp")]


@pytest.fixture
def native_site(settings, monkeypatch, observed):
    settings.ROOT_URLCONF = "config.urls"
    settings.PORTAL_LOGIN_REQUIRED = False
    monkeypatch.setattr(
        "apps.portal.views.timezone.localdate", lambda: observed.cut
    )
    observed.metrics["kind"] = "summary_inventory"
    observed.save()
    block = EvaScopeSnapshot.objects.get(source__extraction=observed)
    native = block.row
    block.source.payload = {"summary": {"eva_evidence": {}}}
    block.source.save()
    block.row = {
        "azure_project": "AMK.012",
        "project_id": native["idProyecto"],
        "scope": "S1",
        "fields": {
            "delivery_manager": "Ana",
            "service": "IXB",
            "project_name": "Demo",
        },
        "budget": "10",
        "issues": [],
        "unknown_labels": [],
        "stages": [
            {
                "stage": "Discovery",
                "start": "2026-10-01",
                "finish": "2026-10-15",
            },
            {
                "stage": "Deployment",
                "start": "2026-10-16",
                "finish": "2026-10-31",
            },
        ],
        "iteration_start": "2026-10-01",
        "iteration_finish": "2026-10-31",
        "eva_metrics": native,
        "metrics_observed_date": observed.cut.isoformat(),
    }
    block.save()
    return observed


@pytest.mark.parametrize("width", [1450, 900, 390])
def test_native_eva_filter_export_and_refresh(
    page, live_server, native_site, width
):
    page.set_viewport_size({"width": width, "height": 950})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(live_server.url + "/operativa/eva-1/")
    page.locator("#eva-table tbody tr[data-manager]").first.wait_for()
    assert page.locator("#eva-table tbody tr[data-manager]").count() == 1
    assert page.locator("#eva-table").inner_text().find("AMK.012_S1") >= 0
    path = Path("tmp/eva-native")
    path.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(path / f"eva-{width}.png"), full_page=True)
    _controls(page, errors, width)


def _controls(page, errors, width):
    assert page.evaluate(
        "document.documentElement.scrollWidth <= innerWidth"
    ), page.evaluate(
        "[...document.querySelectorAll('body *')]"
        ".filter(e=>e.getBoundingClientRect().right>innerWidth+1)"
        ".slice(0,8).map(e=>[e.tagName,e.className,"
        "e.getBoundingClientRect().width])"
    )
    with page.expect_download() as download:
        page.locator("#eva-export").click()
    assert download.value.suggested_filename == "EVA1_IXB_RaaS.csv"
    assert not errors
    path = Path("tmp/eva-native")
    path.mkdir(parents=True, exist_ok=True)
    page.evaluate("window.scrollTo(0,0)")
    page.screenshot(path=str(path / f"eva-{width}.png"), full_page=True)


@pytest.mark.parametrize("width", [1450, 390])
def test_automatic_hours_note_on_receiving_project(
    page, live_server, native_site, width
):
    from copy import deepcopy

    first = EvaScopeSnapshot.objects.get(source__extraction=native_site)
    first.row["eva_metrics"]["clockify_project_id"] = "provider"
    first.save()
    second = deepcopy(first.row)
    second.update(
        project_id="AMK.012_S2", scope="S2", iteration_start="2026-10-02"
    )
    second["eva_metrics"].update(
        scope="S2", idProyecto="AMK.012_S2", fechaInicio="2026-10-02"
    )
    EvaScopeSnapshot.objects.create(
        source=first.source, project_id="AMK.012_S2", scope="S2", row=second
    )
    source = first.source
    source.payload["summary"]["eva_evidence"] = {
        "observed_date": native_site.cut.isoformat(),
        "clockify": {"provider": [native_fixtures.entry(task="")]},
    }
    source.save()
    page.set_viewport_size({"width": width, "height": 950})
    page.goto(live_server.url + "/operativa/eva-1/")
    note = page.locator(".eva-allocation-note")
    expect(note).to_have_count(1)
    expect(note).not_to_be_visible()
    toggle = page.get_by_label("Ver nota de atribución automática de horas")
    toggle.click()
    expect(note).to_be_visible()
    expect(note).to_contain_text("1 h sin tarea/tag atribuidas")
    expect(note).to_contain_text("primero en iniciar")
    assert "AMK.012_S1" in note.locator("xpath=ancestor::tr").inner_text()
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.screenshot(
        path=f"tmp/eva-native/allocation-note-{width}.png", full_page=True
    )
    toggle.focus()
    page.keyboard.press("Enter")
    expect(note).not_to_be_visible()


def test_cut_form_works_without_javascript_while_extraction_runs(
    browser, live_server, native_site
):
    from datetime import timedelta

    old_day = native_site.cut - timedelta(days=1)
    run = EvaExtraction.objects.create(
        cut=old_day,
        started_at=timezone.now(),
        finished_at=timezone.now(),
        published=True,
    )
    source = EvaAzureSource.objects.create(
        extraction=run, azure_id="old", name="AMK.012", payload={}
    )
    original = EvaScopeSnapshot.objects.get(source__extraction=native_site)
    target = {
        **original.row,
        "fields": {
            **original.row["fields"],
            "project_name": "Proyecto del corte anterior",
        },
    }
    EvaScopeSnapshot.objects.create(
        source=source, project_id=original.project_id, scope="S1", row=target
    )
    run.metrics = {"kind": "summary_inventory"}
    run.save()
    source.payload = original.source.payload
    source.save()
    EvaExtraction.objects.create(
        cut=native_site.cut,
        started_at=timezone.now(),
        metrics={"kind": "summary_inventory"},
    )
    context = browser.new_context(java_script_enabled=False)
    try:
        page = context.new_page()
        posts = []
        page.on(
            "request",
            lambda request: (
                posts.append(request.url) if request.method == "POST" else None
            ),
        )
        page.goto(live_server.url + "/operativa/eva-1/")
        page.locator("#eva-cut").fill(old_day.isoformat())
        page.locator("#eva-manager").select_option(label="Ana")
        page.locator("#eva-service").select_option(label="IXB")
        page.locator("[data-eva-refresh]").click()
        expect(page).to_have_url(
            __import__("re").compile("corte=" + old_day.isoformat())
        )
        expect(page.locator("#eva-table")).to_contain_text(
            "Proyecto del corte anterior"
        )
        expect(page.locator("#eva-manager")).to_have_value("Ana")
        expect(page.locator("#eva-service")).to_have_value("IXB")
        assert not posts
    finally:
        context.close()
