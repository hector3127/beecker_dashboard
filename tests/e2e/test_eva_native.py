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
            cut=native_site.cut, started_at=timezone.now()
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
        extraction=run, azure_id="new", name="AMK.012", payload={}
    )
    updated = {
        **old.row,
        "burn": 2,
        "etc": 8,
        "hoursDeviation": 0,
        "avance": 20,
    }
    EvaScopeSnapshot.objects.create(
        source=source, project_id=old.project_id, scope="S1", row=updated
    )
    run.published, run.finished_at = True, timezone.now()
    run.metrics = {"total_seconds": 4}
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
    page.locator("#eva-closed-box summary").click()
    expect(page.locator("#eva-closed-body")).not_to_contain_text(
        "Cargando proyectos"
    )
    assert not errors
    path = Path("tmp/eva-native")
    path.mkdir(parents=True, exist_ok=True)
    page.evaluate("window.scrollTo(0,0)")
    page.screenshot(path=str(path / f"eva-{width}.png"), full_page=True)
