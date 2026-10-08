import base64
import email
from email import policy

import pytest

from apps.gmail.exceptions import (
    GmailApiError,
    GmailAuthError,
    GmailNotConnectedError,
    ReplyValidationError,
)
from apps.gmail.services.communique import (
    ExtensionData,
    build_html,
    build_text,
    format_date,
    reason_sentence,
)
from apps.gmail.services.credentials_store import (
    StoredCredentials,
    load_credentials,
    require_credentials,
    save_credentials,
)
from apps.gmail.services.extension_reply import (
    deliver_extension,
    parse_extension,
    validate_files,
)
from apps.gmail.services.gmail_api import GmailApi
from apps.gmail.services.oauth_client import GoogleOAuth
from apps.gmail.services.reply_builder import (
    Attachment,
    build_raw_message,
    build_references,
    compute_reply_all,
    headers_of,
    last_message,
    reply_subject,
)
from apps.gmail.services.thread_finder import (
    build_queries,
    find_threads,
    is_project_thread,
    normalize_text,
    project_name_from_subject,
    strip_reply_prefixes,
)
from apps.gmail.services.thread_memory import recall_thread, remember_thread
from tests.gmail.fakes import (
    ME,
    FakeGmail,
    FakeHttp,
    FakeResponse,
    make_message,
    make_thread,
)

DATA = ExtensionData(
    project="MCC.015_S3",
    stage="Deployment",
    current_date="2026-10-07",
    new_date="2026-10-09",
    reason="En la ultima prueba, se vio la necesidad de robustecer.",
    roadmap_link="https://drive.google.com/roadmap/v2",
    has_attachments=True,
)

FIELDS = {
    "project": "MCC.015_S3",
    "stage": "Deployment",
    "currentDate": "2026-10-07",
    "newDate": "2026-10-09",
    "reason": "Se necesita robustecer las excepciones.",
    "roadmapLink": "https://drive.google.com/roadmap/v2",
    "threadId": "19abc123def",
}


class SessionDouble(dict):
    """Sesion de Django en memoria."""


def project_thread(thread_id="19abc123def"):
    return make_thread(
        thread_id,
        make_message(
            "Inicio de proyecto: Order Entry",
            "Ximena <ximena@beecker.ai>",
            to="Brandon <brandon@beecker.ai>, Platform <platform@beecker.ai>",
            message_id="<a@mail>",
            date=1000,
        ),
        make_message(
            "Re: Inicio de proyecto: Order Entry",
            "Alberto <alberto@beecker.ai>",
            to="Brandon <brandon@beecker.ai>, hector@beecker.ai",
            cc="ROC <roc@beecker.ai>",
            message_id="<b@mail>",
            references="<a@mail>",
            date=2000,
        ),
    )


def test_normalize_and_subject_parsing():
    assert normalize_text("Inicio de Proyecto: Árbol_Ñu") == (
        "inicio de proyecto arbol nu"
    )
    assert strip_reply_prefixes("Re: RV: Fwd: Hola") == "Hola"
    assert (
        project_name_from_subject("Re: Inicio de Proyecto: App p/usuarios.")
        == "App p/usuarios."
    )
    assert is_project_thread("RE: INICIO DE PROYECTO: X")
    assert is_project_thread("Inicio de agente: Bot")
    assert is_project_thread("Re: Inicio de T&M | GNP")
    assert not is_project_thread("Reinicio de servidor")
    assert not is_project_thread("Otro tema")
    assert project_name_from_subject("Inicio de agente: Bot") == "Bot"
    assert project_name_from_subject("Inicio de T&M | GNP") == "GNP"
    assert project_name_from_subject("Inicio de proyecto - ABC") == "ABC"
    assert project_name_from_subject("Inicio de Algo") == "Algo"


def test_build_queries_puts_the_project_name_first():
    queries = build_queries('Order "Entry"', "")

    assert queries[0] == (
        'subject:"Inicio de" subject:"Order  Entry"',
        10,
    )
    assert queries[1] == ('subject:"Inicio de"', 40)
    assert build_queries("", "x")[0][0].endswith("x")


def test_find_threads_marks_suggested_and_remembered_first():
    api = FakeGmail(
        {
            "t1": project_thread("t1"),
            "t2": make_thread(
                "t2",
                make_message(
                    "Inicio de proyecto: Customer Invoices",
                    "A <a@beecker.ai>",
                    to="b@beecker.ai",
                    date=9000,
                ),
            ),
            "t3": make_thread(
                "t3",
                make_message(
                    "Inicio de proyecto: Otro",
                    "A <a@beecker.ai>",
                    to="b@beecker.ai",
                    date=500,
                ),
            ),
        },
    )

    found = find_threads(api, "Order Entry", "", ME)

    assert [item["id"] for item in found] == ["t1", "t2", "t3"]
    assert found[0]["suggested"] is True
    assert found[1]["suggested"] is False
    assert found[0]["messageCount"] == 2
    assert found[0]["participants"] == 6
    assert found[0]["replyTo"] == ["Alberto <alberto@beecker.ai>"]

    remembered = find_threads(api, "Order Entry", "", ME, remembered_id="t3")

    assert remembered[0]["id"] == "t3"
    assert remembered[0]["remembered"] is True


def test_reply_all_to_someone_elses_message():
    headers = headers_of(last_message(project_thread()))

    to_list, cc_list = compute_reply_all(headers, ME)

    assert to_list == ["Alberto <alberto@beecker.ai>"]
    assert cc_list == [
        "Brandon <brandon@beecker.ai>",
        "ROC <roc@beecker.ai>",
    ]


def test_reply_all_when_the_last_message_is_mine_keeps_recipients():
    headers = {
        "from": "Hector <hector@beecker.ai>",
        "to": "a@beecker.ai, b@beecker.ai",
        "cc": "c@beecker.ai",
    }

    assert compute_reply_all(headers, ME) == (
        ["a@beecker.ai", "b@beecker.ai"],
        ["c@beecker.ai"],
    )


def test_reply_all_uses_reply_to_and_removes_duplicates():
    headers = {
        "from": "Lista <lista@beecker.ai>",
        "reply-to": "Ana <ana@beecker.ai>",
        "to": "ANA@beecker.ai, x@beecker.ai, X@beecker.ai",
        "cc": "hector@BEECKER.AI",
    }

    assert compute_reply_all(headers, ME) == (
        ["Ana <ana@beecker.ai>"],
        ["x@beecker.ai"],
    )


def test_subject_and_references_keep_the_thread():
    assert reply_subject("Inicio de proyecto: X") == "Re: Inicio de proyecto: X"
    assert reply_subject("RE: Inicio") == "RE: Inicio"
    assert build_references(
        {"message-id": "<b@mail>", "references": "<a@mail>"},
    ) == ("<b@mail>", "<a@mail> <b@mail>")


def test_raw_message_has_thread_headers_and_attachment():
    raw = build_raw_message(
        sender=ME,
        to_list=["Alberto <alberto@beecker.ai>"],
        cc_list=["roc@beecker.ai"],
        subject="Re: Inicio de proyecto: Órdenes",
        reply_headers=("<b@mail>", "<a@mail> <b@mail>"),
        bodies=("texto", "<p>html</p>"),
        attachments=[Attachment("plan.pdf", b"%PDF-1.4")],
    )
    message = email.message_from_bytes(
        base64.urlsafe_b64decode(raw),
        policy=policy.default,
    )

    assert message["To"] == "Alberto <alberto@beecker.ai>"
    assert message["Cc"] == "roc@beecker.ai"
    assert message["Subject"] == "Re: Inicio de proyecto: Órdenes"
    assert message["In-Reply-To"] == "<b@mail>"
    assert message["References"] == "<a@mail> <b@mail>"
    assert [p.get_filename() for p in message.iter_attachments()] == [
        "plan.pdf",
    ]


def test_communique_matches_the_preview_and_escapes_html():
    text = build_text(DATA)
    html_body = build_html(
        ExtensionData(
            **{**DATA.__dict__, "reason": "Fallo <script>x</script>"}
        ),
    )

    assert (
        "Informo la extensión del proyecto MCC.015_S3 debido a que en" in text
    )
    assert "Fecha actual de cierre: 07/10/2026" in text
    assert "Nueva fecha: 09/10/2026" in text
    assert "También se incluyen archivos de soporte" in text
    assert "<script>" not in html_body
    assert "&lt;script&gt;" in html_body
    assert format_date("2026-01-05") == "05/01/2026"
    assert reason_sentence("Hola mundo.") == "hola mundo"
    assert "archivos de soporte" not in build_text(
        ExtensionData(**{**DATA.__dict__, "has_attachments": False}),
    )


def test_parse_extension_validates_each_field():
    data, thread_id = parse_extension(FIELDS, 2)

    assert data.has_attachments is True
    assert thread_id == "19abc123def"

    for field, value in (
        ("project", ""),
        ("stage", "Otra"),
        ("reason", ""),
        ("reason", "x" * 501),
        ("roadmapLink", "javascript:alert(1)"),
        ("roadmapLink", "https://"),
        ("threadId", "../etc/passwd"),
        ("newDate", "09/10/2026"),
    ):
        with pytest.raises(ReplyValidationError):
            parse_extension({**FIELDS, field: value}, 0)


def test_validate_files_checks_type_size_and_name():
    ok = validate_files([("..\\x/Plan.PDF", b"1"), ("a.png", b"2")])

    assert [a.filename for a in ok] == ["Plan.PDF", "a.png"]

    with pytest.raises(ReplyValidationError):
        validate_files([("virus.exe", b"1")])

    with pytest.raises(ReplyValidationError):
        validate_files([("big.pdf", b"x" * (10 * 1024 * 1024 + 1))])

    with pytest.raises(ReplyValidationError):
        validate_files([(f"{i}.pdf", b"1") for i in range(11)])


def test_deliver_creates_a_draft_by_default_and_never_sends():
    api = FakeGmail({"19abc123def": project_thread("19abc123def")})
    data, thread_id = parse_extension(FIELDS, 0)

    result = deliver_extension(api, ME, data, thread_id, [], "draft")

    assert result["mode"] == "draft"
    assert result["subject"] == "Re: Inicio de proyecto: Order Entry"
    assert result["to"] == ["Alberto <alberto@beecker.ai>"]
    assert result["link"].endswith("#drafts?compose=msgdraft")
    assert len(api.drafts) == 1
    assert api.sent == []
    assert api.drafts[0][1] == "19abc123def"


def test_deliver_in_send_mode_uses_send_message():
    api = FakeGmail({"19abc123def": project_thread("19abc123def")})
    data, thread_id = parse_extension(FIELDS, 0)

    result = deliver_extension(api, ME, data, thread_id, [], "send")

    assert result["mode"] == "send"
    assert len(api.sent) == 1
    assert api.drafts == []


def test_deliver_refuses_threads_that_are_not_project_threads():
    other = make_thread(
        "19abc123def",
        make_message("Cena de equipo", "a@beecker.ai", to="b@beecker.ai"),
    )
    data, thread_id = parse_extension(FIELDS, 0)

    with pytest.raises(ReplyValidationError):
        deliver_extension(
            FakeGmail({"19abc123def": other}),
            ME,
            data,
            thread_id,
            [],
            "draft",
        )


def test_oauth_url_and_code_exchange():
    http = FakeHttp(
        FakeResponse(200, {"access_token": "tok", "expires_in": 3599}),
        FakeResponse(200, {"email": " Hector@Beecker.AI "}),
    )
    oauth = GoogleOAuth("cid", "secret", session=http, clock=lambda: 100.0)

    url = oauth.build_authorization_url("http://x/cb", "estado")

    assert "client_id=cid" in url
    assert "access_type=online" in url
    assert "gmail.compose" in url
    assert "state=estado" in url
    assert "secret" not in url

    token = oauth.exchange_code("codigo", "http://x/cb")

    assert (token.value, token.expires_at) == ("tok", 3699.0)
    assert oauth.fetch_email(token.value) == "hector@beecker.ai"
    assert http.calls[0][2]["data"]["grant_type"] == "authorization_code"


def test_oauth_errors_do_not_leak_the_secret():
    oauth = GoogleOAuth(
        "cid",
        "top-secret",
        session=FakeHttp(FakeResponse(400, {"error": "invalid_grant"})),
    )

    with pytest.raises(GmailAuthError) as error:
        oauth.exchange_code("malo", "http://x/cb")

    assert "top-secret" not in error.value.detail


def test_credentials_expire_and_are_cleared():
    session = SessionDouble()
    save_credentials(session, StoredCredentials(ME, "tok", 1000.0))

    assert load_credentials(session, clock=lambda: 500.0).email == ME
    assert load_credentials(session, clock=lambda: 990.0) is None
    assert session == {}

    with pytest.raises(GmailNotConnectedError):
        require_credentials(session)


def test_gmail_api_maps_http_errors():
    def api_with(status, payload=None):
        return GmailApi("tok", session=FakeHttp(FakeResponse(status, payload)))

    assert api_with(
        200, {"threads": [{"id": "a"}, {"id": "b"}]}
    ).search_thread_ids(
        "q",
        5,
    ) == ["a", "b"]
    assert api_with(200, {}).search_thread_ids("q", 5) == []

    with pytest.raises(GmailNotConnectedError):
        api_with(401).get_thread("x")

    for status in (403, 404, 500):
        with pytest.raises(GmailApiError):
            api_with(status).get_thread("x")

    http = FakeHttp(FakeResponse(200, {"id": "d"}))
    GmailApi("tok", session=http).create_draft("raw", "t1")

    assert http.calls[0][2]["json"] == {
        "message": {"raw": "raw", "threadId": "t1"},
    }
    assert http.calls[0][2]["headers"] == {"Authorization": "Bearer tok"}


def test_thread_memory_remembers_by_normalized_project():
    store = {}

    class Memory:
        def get(self, key, default=None):
            return store.get(key, default)

        def set(self, key, value, timeout=None):
            store[key] = value

    remember_thread(Memory(), "MCC.015_S3", "t9")

    assert recall_thread(Memory(), "mcc 015 s3") == "t9"
    assert recall_thread(Memory(), "otro") == ""
    assert recall_thread(Memory(), "") == ""
