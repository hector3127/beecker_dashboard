"""La capacidad diaria abre fuera del HTML y del JavaScript de legacy."""

from types import SimpleNamespace

from django.test import RequestFactory, override_settings

from apps.portal import pages, views


def test_standalone_page_needs_no_source_read_and_sets_csrf_cookie(monkeypatch):
    monkeypatch.setattr(
        views,
        "load_capacity",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("Source read")
        ),
    )
    response = pages.capacity_daily(
        RequestFactory().get("/capacidad-instalada/")
    )
    html = response.content.decode()
    assert response.status_code == 200
    assert "app/scripts/pages/capacity_daily/main.js" in html
    assert "portal/js/capacidad_instalada.js" not in html
    assert "Regresar a Operativa" in html
    assert 'class="ds capacity-daily-page"' in html
    assert "ci-general-tabs" not in html
    assert "tpl-dashboard" not in html
    assert "legacy_skin.css" not in html
    assert "csrftoken" in response.cookies


@override_settings(PORTAL_LOGIN_REQUIRED=True)
def test_standalone_page_requires_login():
    request = RequestFactory().get("/capacidad-instalada/")
    request.user = SimpleNamespace(is_authenticated=False)
    assert pages.capacity_daily(request).status_code == 302
