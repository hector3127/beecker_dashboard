"""El proyecto se consulta en el portal sin inicializar el panel anterior."""

from types import SimpleNamespace

from django.test import RequestFactory, override_settings

from apps.portal import views


def test_project_shell_preserves_cr_id_and_uses_portal_header(monkeypatch):
    def source(*args, **kwargs):
        raise AssertionError("Unexpected source query")

    monkeypatch.setattr(views, "load_portfolio", source)
    monkeypatch.setattr(views, "load_project_dashboard", source)
    response = views.proyecto_detalle(RequestFactory().get("/"), "CCO.001 | CR")
    html = response.content.decode()
    assert '"id": "CCO.001 | CR"' in html
    assert 'class="ds project-detail-page"' in html
    assert 'aria-current="page" href="/operativa/"' in html
    assert "portal/js/proyecto_detalle.js" in html
    assert "portal/css/proyecto_detalle.css" in html
    assert "gse-panel" not in html
    assert "ci-panel" not in html
    assert "csrftoken" in response.cookies


@override_settings(PORTAL_LOGIN_REQUIRED=True)
def test_project_shell_requires_login():
    request = RequestFactory().get("/proyectos/AIN.002%20CR/")
    request.user = SimpleNamespace(is_authenticated=False)
    assert views.proyecto_detalle(request, "AIN.002 CR").status_code == 302
