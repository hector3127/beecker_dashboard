"""Aviso de datos faltantes en el Ejecutivo del proyecto."""

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_executive import PAGE
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)


def test_notes_are_listed_as_text_and_absent_without_them(
    portal, ixs, project_detail, fixed_day
):
    data, _ = project_detail
    portal.goto(portal.base + PAGE)
    expect(portal.locator("#ixs-risks-content")).to_be_visible()
    expect(portal.locator(".project-data-notice")).to_have_count(0)

    data["proyecto"]["datosFaltantes"] = [
        "El proyecto no está en Proyectos; se muestra con datos de MPB.",
        "Falta la fecha de fin <b>x</b>",
    ]
    portal.goto(portal.base + PAGE)
    notice = portal.locator(".project-data-notice")
    expect(notice).to_have_count(1)
    expect(notice.locator("li")).to_have_count(2)
    expect(notice).to_contain_text("Falta la fecha de fin <b>x</b>")
