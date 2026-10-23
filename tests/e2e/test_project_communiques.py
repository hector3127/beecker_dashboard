"""Comunicados del proyecto: cuatro tipos en IXB, dos en AER, mismo diseño."""

from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import PAGE as AER_PAGE
from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_effort import state as capture_state
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_ixs_planning_transport import open_planning
from tests.e2e.test_ixs_planning_transport import planning as planning
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)
THREAD = {
    "id": "19abc123def",
    "subject": "Inicio de proyecto: Order Entry",
    "lastFrom": "Alberto <alberto@beecker.ai>",
    "lastDate": "2026-10-01T10:00:00Z",
    "participants": 3,
    "messageCount": 2,
    "replyTo": ["Alberto <alberto@beecker.ai>"],
    "replyCc": [],
    "suggested": True,
    "remembered": False,
}


@pytest.fixture
def gmail(portal):
    """Gmail conectado y un hilo; guarda lo que se envía a /gmail/reply/."""
    sent = []

    def route(handler):
        url = handler.request.url
        if "/gmail/status/" in url:
            handler.fulfill(
                json={
                    "ok": True,
                    "result": {
                        "configured": True,
                        "connected": True,
                        "email": "yo@beecker.ai",
                        "mode": "draft",
                    },
                }
            )
        elif "/gmail/threads/" in url:
            handler.fulfill(
                json={
                    "ok": True,
                    "result": {"email": "yo@beecker.ai", "threads": [THREAD]},
                }
            )
        elif "/gmail/reply/" in url:
            sent.append(handler.request.post_data_buffer.decode("latin-1"))
            handler.fulfill(
                json={
                    "ok": True,
                    "result": {
                        "mode": "draft",
                        "subject": "Re: x",
                        "to": [],
                        "cc": [],
                        "link": "https://mail.google.com/draft",
                    },
                }
            )
        else:
            handler.fallback()

    portal.route("**/gmail/**", route)
    return sent


def open_modal(portal, previous=False):
    open_planning(portal, previous)
    portal.evaluate("ixsAbrirExtension()")
    expect(portal.locator(".ixe-dialog")).to_be_visible()
    expect(portal.locator(".ixe-thread")).to_have_count(1)
    portal.locator(".ixe-thread input").check()


@pytest.mark.parametrize("width", [1450, 900, 390])
def test_extension_matches_previous(portal, planning, gmail, fixed_day, width):
    portal.set_viewport_size({"width": width, "height": 1000})
    states = []
    directory = Path("tmp/migration/project_detail/communique") / str(width)
    directory.mkdir(parents=True, exist_ok=True)
    for previous in [True, False]:
        open_modal(portal, previous)
        # Los botones de tipo son nuevos y el logo anterior ya no está.
        portal.evaluate(
            "document.querySelectorAll('.ixe-kinds, .ixe-brand')"
            ".forEach(n => n.remove())"
        )
        selector = ".ixe-dialog, .ixe-dialog *"
        states.append(
            [
                {**s, "cls": c}
                for s, c in zip(
                    capture_state(portal, selector),
                    portal.evaluate(
                        "s=>[...document.querySelectorAll(s)].map(e=>String(e.getAttribute('class')||'').trim())",
                        selector,
                    ),
                    strict=True,
                )
            ]
        )
        portal.screenshot(
            path=str(directory / ("old.png" if previous else "new.png"))
        )
    diffs = [
        (
            i,
            a["tag"],
            a["cls"],
            {k: (a[k], b[k]) for k in a if k != "cls" and a[k] != b[k]},
        )
        for i, (a, b) in enumerate(zip(*states, strict=False))
        if a != b
    ]
    assert len(states[0]) == len(states[1]) and not diffs, diffs[:5]


def test_ixb_has_four_buttons_and_each_changes_the_template(
    portal, planning, gmail, fixed_day
):
    open_modal(portal)
    kinds = portal.locator(".ixe-kind")
    expect(kinds).to_have_text(
        ["Extensión", "Suspensión", "Reanudación", "Cierre"]
    )
    for name, text in [
        ("Suspensión", "Informo la suspensión temporal"),
        ("Reanudación", "Informo la reanudación del proyecto"),
        ("Cierre", "comunicado oficial del cierre"),
        ("Extensión", "Informo la extensión del proyecto"),
    ]:
        portal.locator(".ixe-kind", has_text=name).click()
        expect(portal.locator(".ixe-preview")).to_contain_text(text)
        expect(portal.locator(".ixe-kind.on")).to_have_text(name)
    expect(portal.locator(".ixe-subject .v")).to_have_text(
        "Re: Inicio de proyecto: Order Entry"
    )


def fill(portal, **values):
    for key, value in values.items():
        node = portal.locator(f'#ixe-id, [data-key="{key}"]').last
        if key == "link":
            node = portal.locator("#ixe-link")
        elif key == "project":
            node = portal.locator("#ixe-id")
        node.fill(value) if node.evaluate("n=>n.tagName") != "SELECT" else (
            node.select_option(value)
        )


def post(portal, gmail):
    portal.locator("#ixe-send").click()
    expect(portal.locator(".ixe-okbox")).to_be_visible()
    return gmail[-1]


def test_suspension_sends_its_fields_and_links(
    portal, planning, gmail, fixed_day
):
    open_modal(portal)
    portal.locator(".ixe-kind", has_text="Suspensión").click()
    fill(
        portal,
        stage="Development",
        resumeDate="2026-11-02",
        condition="la entrega de accesos",
        reason="El cliente no entregó accesos.",
        link="https://drive.google.com/soporte",
    )
    body = post(portal, gmail)
    for part in [
        'name="kind"\r\n\r\nsuspension',
        'name="stage"\r\n\r\nDevelopment',
        'name="resumeDate"\r\n\r\n2026-11-02',
        'name="condition"\r\n\r\nla entrega de accesos',
        'name="link"\r\n\r\nhttps://drive.google.com/soporte',
        'name="threadId"\r\n\r\n19abc123def',
    ]:
        assert part in body


def test_ixb_close_needs_the_mco_and_accepts_a_file(
    portal, planning, gmail, fixed_day, tmp_path
):
    open_modal(portal)
    portal.locator(".ixe-kind", has_text="Cierre").click()
    fill(portal, closeDate="2026-10-15", projectName="Rutas UNIGIS")
    portal.locator("#ixe-send").click()
    expect(portal.locator("#ixe-toast")).to_have_text(
        "Adjunta la MCO como archivo o pon su enlace."
    )
    assert gmail == []
    mco = tmp_path / "MCO.pdf"
    mco.write_bytes(b"%PDF-1.4")
    portal.locator("#ixe-file").set_input_files(str(mco))
    expect(portal.locator(".ixe-files .ixe-file")).to_have_count(1)
    expect(portal.locator(".ixe-preview")).to_contain_text(
        "La MCO se incluye como archivo adjunto."
    )
    body = post(portal, gmail)
    assert 'name="kind"\r\n\r\ncierre_ixb' in body
    assert 'filename="MCO.pdf"' in body


def test_missing_data_is_named_before_sending(
    portal, planning, gmail, fixed_day
):
    open_modal(portal)
    portal.locator(".ixe-kind", has_text="Reanudación").click()
    portal.locator("#ixe-send").click()
    expect(portal.locator("#ixe-toast")).to_have_text(
        "Falta la fecha de reanudación."
    )
    assert gmail == []


def test_preview_text_is_escaped(portal, planning, gmail, fixed_day):
    open_modal(portal)
    portal.locator(".ixe-kind", has_text="Suspensión").click()
    fill(portal, reason="<img src=x onerror=alert(1)>")
    expect(portal.locator(".ixe-preview img")).to_have_count(0)
    expect(portal.locator(".ixe-preview")).to_contain_text("<img src=x")


def test_aer_shows_only_extension_and_close(
    portal, project_detail, gmail, fixed_day
):
    portal.goto(portal.base + AER_PAGE)
    portal.get_by_role("button", name="Cierre", exact=True).click()
    expect(portal.locator(".ixe-kind")).to_have_text(["Extensión", "Cierre"])
    expect(portal.locator(".ixe-kind.on")).to_have_text("Cierre")
    expect(portal.locator(".ixe-preview")).to_contain_text(
        "El presente es para dar como finalizado"
    )
    expect(portal.locator(".ixe-thread")).to_have_count(1)
    portal.locator(".ixe-thread input").check()
    fill(portal, description="las mejoras del Smart Attendance")
    expect(portal.locator(".ixe-preview")).to_contain_text(
        "afiliado a las mejoras del Smart Attendance"
    )
    body = post(portal, gmail)
    assert 'name="kind"\r\n\r\ncierre_aer' in body
    assert (
        'name="description"\r\n\r\na las mejoras del Smart Attendance' in body
    )


def test_send_mode_asks_with_a_styled_confirmation(
    portal, planning, gmail, fixed_day
):
    portal.route(
        "**/gmail/status/",
        lambda route: route.fulfill(
            json={
                "ok": True,
                "result": {
                    "configured": True,
                    "connected": True,
                    "email": "yo@beecker.ai",
                    "mode": "send",
                },
            }
        ),
    )
    open_modal(portal)
    portal.locator(".ixe-kind", has_text="Reanudación").click()
    fill(portal, resumeDate="2026-11-03")
    portal.locator("#ixe-send").click()
    confirm = portal.locator(".ixe-confirm")
    expect(confirm).to_contain_text("Se enviará un correo a 1 destinatario")
    portal.keyboard.press("Escape")
    expect(confirm).to_have_count(0)
    expect(portal.locator(".ixe-dialog")).to_be_visible()
    assert gmail == []
    portal.locator("#ixe-send").click()
    portal.get_by_role("button", name="Enviar correo").click()
    expect(portal.locator(".ixe-okbox")).to_be_visible()
    assert len(gmail) == 1


def test_suspension_asks_the_reason_before_the_condition(
    portal, planning, gmail, fixed_day
):
    open_modal(portal)
    portal.locator(".ixe-kind", has_text="Suspensión").click()
    keys = portal.locator("[data-key]").evaluate_all(
        "nodes => nodes.map(n => n.dataset.key)"
    )
    assert keys == ["stage", "resumeDate", "reason", "condition"]
