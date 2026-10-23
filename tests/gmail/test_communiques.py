"""Suspension, reanudacion y cierres: validacion, texto y entrega."""

from datetime import datetime

import pytest

from apps.gmail.exceptions import ReplyValidationError
from apps.gmail.services.communique import (
    build_other_html,
    build_other_text,
    greeting,
)
from apps.gmail.services.extension_reply import (
    deliver_communique,
    parse_communique,
)
from tests.gmail.fakes import FakeGmail
from tests.gmail.test_services import ME, project_thread

THREAD = {"threadId": "19abc123def", "project": "MCC.015_S3"}
SUSPENSION = {
    **THREAD,
    "reason": "El cliente no entregó accesos.",
    "stage": "Development",
    "resumeDate": "2026-11-02",
    "condition": "la entrega de accesos",
}


def parse(kind, fields, files=0):
    return parse_communique(kind, {**THREAD, **fields}, files)[0]


def test_suspension_text_follows_the_template_and_addresses_roc():
    data = parse("suspension", SUSPENSION)

    text = build_other_text(data, 9, "2026-10-23")

    assert text.startswith("Buenos días ROC,\n\nInformo la suspensión temporal")
    assert "del proyecto MCC.015_S3, debido a:" in text
    assert "El cliente no entregó accesos." in text
    assert "la etapa Development y avanzar conforme al plan" in text
    assert (
        "La fecha tentativa de reanudación es 02/11/2026, siempre que se "
        "confirme la entrega de accesos."
    ) in text
    assert text.endswith("Quedamos atentos a tus comentarios o confirmación.")
    assert greeting(15) == "Buenas tardes"


def test_resumption_and_close_texts():
    resume = parse("reanudacion", {"resumeDate": "2026-11-03"})
    assert "fecha efectiva de reanudación es 03/11/2026" in build_other_text(
        resume, 15, "2026-10-23"
    )

    ixb = parse(
        "cierre_ixb",
        {
            "closeDate": "2026-10-15",
            "projectName": "Planificación de Rutas - UNIGIS",
            "link": "https://drive.google.com/mco",
        },
    )
    text = build_other_text(ixb, 9, "2026-10-23")
    assert (
        'cierre del proyecto MCC.015_S3 "Planificación de Rutas - UNIGIS" '
        "el día 15/10/2026"
    ) in text
    assert "Adjunto la MCO" in text and "MCO: https://drive" in text

    aer = parse(
        "cierre_aer",
        {
            "closeDate": "2026-10-23",
            "description": "a las mejoras del Smart Attendance",
        },
    )
    text = build_other_text(aer, 9, "2026-10-23")
    assert "finalizado el día de hoy - 23/10/2026 - el cierre" in text
    assert "MCC.015_S3 - afiliado a las mejoras del Smart Attendance." in text
    assert "el día 22/10/2026" in build_other_text(
        parse("cierre_aer", {"closeDate": "2026-10-22"}), 9, "2026-10-23"
    )


def test_html_escapes_what_was_typed_and_links_are_anchors():
    data = parse(
        "suspension",
        {
            **SUSPENSION,
            "reason": "<script>x</script>",
            "link": "https://a.example/?q=1&r=2",
        },
        files=1,
    )

    html = build_other_html(data, 9, "2026-10-23")

    assert "<script>" not in html and "&lt;script&gt;" in html
    assert 'href="https://a.example/?q=1&amp;r=2"' in html
    assert "archivos de soporte" in html


@pytest.mark.parametrize(
    ("kind", "fields", "files", "message"),
    [
        ("nope", {}, 0, "Tipo"),
        ("suspension", {**SUSPENSION, "reason": ""}, 0, "el motivo"),
        ("suspension", {**SUSPENSION, "stage": "Otra"}, 0, "etapa"),
        ("suspension", {**SUSPENSION, "resumeDate": "02/11"}, 0, "AAAA-MM-DD"),
        ("suspension", {**SUSPENSION, "condition": ""}, 0, "condición"),
        ("reanudacion", {}, 0, "fecha de reanudación"),
        (
            "cierre_aer",
            {"closeDate": "2026-10-23", "link": "ftp://x"},
            0,
            "http",
        ),
        ("cierre_ixb", {"closeDate": "2026-10-23"}, 0, "MCO"),
        ("cierre_aer", {"closeDate": ""}, 0, "fecha de cierre"),
    ],
)
def test_validation_errors(kind, fields, files, message):
    with pytest.raises(ReplyValidationError, match=message):
        parse(kind, fields, files)


def test_ixb_close_accepts_a_file_instead_of_a_link_and_thread_is_required():
    assert parse("cierre_ixb", {"closeDate": "2026-10-23"}, files=1)
    with pytest.raises(ReplyValidationError, match="hilo"):
        parse_communique(
            "reanudacion", {"project": "X", "resumeDate": "2026-11-03"}, 0
        )


def test_delivery_replies_in_the_project_thread_as_a_draft():
    api = FakeGmail({"19abc123def": project_thread()})
    data, thread_id = parse_communique(
        "suspension", {**THREAD, **SUSPENSION}, 0
    )

    result = deliver_communique(
        api, ME, data, thread_id, [], "draft", datetime(2026, 10, 23, 9, 0)
    )

    assert result["mode"] == "draft"
    assert result["subject"] == "Re: Inicio de proyecto: Order Entry"
    assert len(api.drafts) == 1 and api.sent == []
