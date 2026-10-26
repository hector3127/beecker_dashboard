"""Obsolete panel links resolve without loading the retired template tree."""

import pytest


@pytest.mark.parametrize(
    "query,expected",
    [
        ({}, "/operativa/facturabilidad/area/"),
        ({"proyecto": "TYM.AAU.001"}, "/proyectos/TYM.AAU.001/"),
        ({"cuenta": "Acme"}, "/cuenta/acme/?nombre=Acme"),
        (
            {"proyecto": "TYM.AAU.001", "cuenta": "Acme"},
            "/proyectos/TYM.AAU.001/",
        ),
    ],
)
def test_legacy_alias_redirects_without_rendering(
    client, settings, query, expected
):
    settings.PORTAL_LOGIN_REQUIRED = False
    response = client.get("/legacy/", query)
    assert response.status_code == 302
    assert response["Location"] == expected
    assert not response.templates


def test_legacy_alias_keeps_login_and_does_not_redirect_anonymous_people(
    client, settings
):
    settings.PORTAL_LOGIN_REQUIRED = True
    response = client.get("/legacy/", {"proyecto": "TYM.AAU.001"})
    assert response.status_code == 302
    assert response["Location"].startswith("/admin/login/?next=")
    assert not response.templates
