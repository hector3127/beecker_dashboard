"""La capacidad mensual abre fuera del HTML y del JavaScript de legacy."""

from types import SimpleNamespace

from django.test import RequestFactory, override_settings

from apps.portal import views


def test_standalone_page_needs_no_source_read_and_sets_csrf_cookie(monkeypatch):
    monkeypatch.setattr(
        views,
        "load_capacity",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("Source read")
        ),
    )
    response = views.capacidad_detalle(
        RequestFactory().get("/capacidad-instalada/")
    )
    html = response.content.decode()
    assert response.status_code == 200
    assert "portal/js/capacidad_instalada.js" in html
    assert "Regresar a Operativa" in html
    assert 'class="ds"' in html
    assert "ci-general-tabs" not in html
    assert "tpl-dashboard" not in html
    assert "legacy_skin.css" not in html
    assert "csrftoken" in response.cookies


@override_settings(PORTAL_LOGIN_REQUIRED=True)
def test_standalone_page_requires_login():
    request = RequestFactory().get("/capacidad-instalada/")
    request.user = SimpleNamespace(is_authenticated=False)
    assert views.capacidad_detalle(request).status_code == 302
