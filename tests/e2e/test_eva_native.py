"""Native EVA cut, responsive controls and extraction polling on real routes."""

from pathlib import Path
from unittest.mock import patch

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
        "apps.portal.api.eva_native.request_refresh", lambda: False
    )
    monkeypatch.setattr(
        "apps.portal.views.timezone.localdate", lambda: observed.cut
    )
    observed.full_inventory = False
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
    expect(page.locator("#eva-extraction-status")).to_contain_text(
        "Última extracción"
    )
    assert page.locator("#eva-table tbody tr[data-manager]").count() == 1
    assert page.locator("#eva-table").inner_text().find("AMK.012_S1") >= 0
    path = Path("tmp/eva-native")
    path.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(path / f"eva-{width}.png"), full_page=True)
    _controls(page, errors, width)


def test_completed_extraction_reloads_new_local_cut(
    page, live_server, native_site
):
    page.goto(live_server.url + "/operativa/eva-1/")
    expect(page.locator("#eva-extraction-status")).to_contain_text(
        "Última extracción"
    )
    created = []

    def queue():
        run = EvaExtraction.objects.create(
            cut=native_site.cut,
            started_at=timezone.now(),
            full_inventory=False,
            metrics={"kind": "summary_inventory"},
        )
        created.append(run)
        return True

    with patch("apps.portal.api.eva_native.request_refresh", side_effect=queue):
        with page.expect_response(
            lambda r: (
                "/eva1/extraccion/" in r.url and r.request.method == "POST"
            )
        ):
            page.locator("#eva-extract").click()
        expect(page.locator("#eva-extraction-status")).to_contain_text(
            "Extrayendo"
        )
    run = created[0]
    old = EvaScopeSnapshot.objects.get(source__extraction=native_site)
    source = EvaAzureSource.objects.create(
        extraction=run,
        azure_id="new",
        name="AMK.012",
        payload=old.source.payload,
    )
    updated = {
        **old.row,
        "burn": 2,
        "etc": 8,
        "hoursDeviation": 0,
        "avance": 20,
    }
    updated["eva_metrics"] = {
        **old.row["eva_metrics"],
        "clockify_project_id": "clock",
    }
    source.payload = {
        "summary": {
            "eva_evidence": {
                "observed_date": native_site.cut.isoformat(),
                "clockify": {"clock": [native_fixtures.entry(seconds=7200)]},
            }
        }
    }
    source.save()
    EvaScopeSnapshot.objects.create(
        source=source, project_id=old.project_id, scope="S1", row=updated
    )
    run.published, run.finished_at = True, timezone.now()
    run.metrics = {"total_seconds": 4, "kind": "summary_inventory"}
    run.save()
    expect(page.locator("#eva-extraction-status")).to_contain_text("4 s")
    assert page.locator("#eva-table tbody tr[data-manager]").count() == 1
    expect(page.locator("#eva-table")).to_contain_text("20%")


def test_failed_extraction_keeps_table_and_allows_retry(
    page, live_server, native_site
):
    page.goto(live_server.url + "/operativa/eva-1/")
    expect(page.locator("#eva-extraction-status")).to_contain_text(
        "Última extracción"
    )

    def fail():
        EvaExtraction.objects.create(
            cut=native_site.cut,
            started_at=timezone.now(),
            finished_at=timezone.now(),
            issues=["Azure no disponible"],
            full_inventory=False,
            metrics={"kind": "summary_inventory"},
        )
        return True

    with patch("apps.portal.api.eva_native.request_refresh", side_effect=fail):
        with page.expect_response(
            lambda r: (
                "/eva1/extraccion/" in r.url and r.request.method == "POST"
            )
        ):
            page.locator("#eva-extract").click()
        expect(page.locator("#eva-extraction-status")).to_contain_text("falló")
    assert page.locator("#eva-extract").is_enabled()
    assert page.locator("#eva-table tbody tr[data-manager]").count() == 1


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
    with patch(
        "apps.portal.api.eva_native.request_refresh", return_value=True
    ) as refresh:
        with page.expect_response(
            lambda r: (
                "/eva1/extraccion/" in r.url and r.request.method == "POST"
            )
        ) as response:
            page.locator("#eva-extract").click()
        assert response.value.status == 202
        refresh.assert_called_once()
    assert not errors
    path = Path("tmp/eva-native")
    path.mkdir(parents=True, exist_ok=True)
    page.evaluate("window.scrollTo(0,0)")
    page.screenshot(path=str(path / f"eva-{width}.png"), full_page=True)


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
    run.full_inventory = False
    run.save()
    source.payload = original.source.payload
    source.save()
    EvaExtraction.objects.create(
        cut=native_site.cut,
        started_at=timezone.now(),
        full_inventory=False,
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
        expect(page.locator("#eva-extraction-status")).to_contain_text(
            "Extracción en curso"
        )
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


def test_status_failure_does_not_block_saved_cut(
    page, live_server, native_site
):
    page.route(
        "**/api/v1/screens/eva1/extraccion/",
        lambda route: route.fulfill(
            status=503,
            json={
                "error": {
                    "code": "unavailable",
                    "message": "Estado no disponible",
                }
            },
        ),
    )
    page.goto(live_server.url + "/operativa/eva-1/")
    expect(page.locator("#eva-extraction-status")).to_have_text(
        "Estado no disponible"
    )
    page.locator("[data-eva-refresh]").click()
    expect(page).to_have_url(
        __import__("re").compile("corte=" + native_site.cut.isoformat())
    )
    expect(page.locator("#eva-table")).to_contain_text("AMK.012_S1")
