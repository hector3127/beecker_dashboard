"""GSE navega dentro del portal sin cargar el panel anterior."""

import pytest


@pytest.mark.parametrize("previous", [False, True])
def test_area_page_uses_portal_navigation_and_keeps_selected_year(
    client, previous
):
    response = client.get(
        "/operativa/facturabilidad/area/",
        {
            "periodo": "anio",
            "anio": "2025",
            **({"vista": "anterior"} if previous else {}),
        },
    )
    assert response.status_code == 200
    html = response.content.decode()
    assert 'data-year="2025"' in html
    assert "csrftoken" in response.cookies
    assert "app/scripts/pages/billability_area/main.js" in html
    assert "portal/js/facturabilidad_area.js" not in html
    assert "core/js/gas_shim.js" not in html
    assert "Panel anterior" not in html
    assert "ciMontarGSE" not in html
    tabs = html.split('<div class="tabs">', 1)[1].split("</div>", 1)[0]
    assert tabs.count("<a ") == 5
    assert 'aria-current="page"' in tabs
    assert 'target="_blank"' not in tabs


def test_legacy_keeps_project_links_and_redirects_general_view(client):
    response = client.get("/legacy/")
    assert response.status_code == 302
    assert response["Location"] == "/operativa/facturabilidad/area/"
    project = client.get("/legacy/", {"proyecto": "AIN.002 CR"})
    assert project.status_code == 302
    assert project["Location"] == "/proyectos/AIN.002%20CR/"
