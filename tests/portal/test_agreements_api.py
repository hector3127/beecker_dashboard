"""Acuerdos: consulta y cambios con capacidad y alcance, API y vista."""

import pytest

from apps.access.scope import AccessScope
from apps.portal.models import ExecutiveAgreement

pytestmark = pytest.mark.django_db

API = "/api/v1/agreements/"
LEGACY = "/ejecutiva/acuerdos/"
READ = frozenset({"view_agreements"})
EDIT = frozenset({"edit_agreements"})
BOTH = READ | EDIT


def agreement(account="ACME", title="Revisar alcance", **extra):
    return ExecutiveAgreement.objects.create(
        account=account, title=title, **extra
    )


@pytest.fixture
def three():
    return {
        "acme": agreement("ACME", "Acuerdo ACME"),
        "cagsa": agreement("Cagsa", "Acuerdo Cagsa"),
        "sin": agreement("", "Sin clasificar"),
    }


def titles(response):
    return sorted(item["title"] for item in response.json()["data"]["items"])


def create(client, **values):
    body = {"account": "ACME", "title": "Nuevo", "meeting_date": "2026-10-01"}
    return client.post(API, {**body, **values}, content_type="application/json")


def patch(client, pk, **values):
    return client.patch(f"{API}{pk}/", values, content_type="application/json")


# ---------- Contrato ----------


def test_list_has_items_with_actions_and_can_edit(client, three):
    body = client.get(API).json()["data"]

    assert body["can_edit"] is True
    first = body["items"][0]
    assert {"id", "account", "title", "status", "notes", "updated_at"} <= set(
        first
    )
    assert first["actions"] == {"edit": True, "change_status": True}


def test_list_filters_by_account_and_pending(client, three):
    ExecutiveAgreement.objects.filter(pk=three["acme"].pk).update(status="done")

    assert titles(client.get(API, {"account": "cagsa"})) == ["Acuerdo Cagsa"]
    assert "Acuerdo ACME" not in titles(client.get(API, {"pending_only": "1"}))
    assert "Acuerdo ACME" in titles(client.get(API))


def test_create_returns_the_saved_record(client):
    response = create(client, kind="agreement", owner="Ana")

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["id"] and data["owner"] == "Ana" and data["kind"] == "agreement"
    assert ExecutiveAgreement.objects.get(pk=data["id"]).title == "Nuevo"


def test_create_validation_errors_name_the_fields(client):
    response = create(client, title="")

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "validation"
    assert "title" in error["fields"]
    assert ExecutiveAgreement.objects.count() == 0


def test_create_rejects_a_body_that_is_not_an_object(client):
    response = client.post(API, [1, 2], content_type="application/json")

    assert response.status_code == 400


def test_unknown_fields_are_ignored_not_saved(client):
    response = create(client, id=999, updated_at="2000-01-01")

    assert response.status_code == 201
    assert response.json()["data"]["id"] != 999


def test_patch_status_only_changes_the_status(client, three):
    before = three["acme"].title

    response = patch(client, three["acme"].pk, status="done")

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "done"
    saved = ExecutiveAgreement.objects.get(pk=three["acme"].pk)
    assert (saved.status, saved.title) == ("done", before)


def test_patch_edits_only_the_fields_sent(client, three):
    response = patch(client, three["acme"].pk, notes="Nueva nota")

    saved = ExecutiveAgreement.objects.get(pk=three["acme"].pk)
    assert response.status_code == 200
    assert (saved.notes, saved.title, saved.account) == (
        "Nueva nota",
        "Acuerdo ACME",
        "ACME",
    )


def test_patch_rejects_an_invalid_status_and_an_empty_change(client, three):
    pk = three["acme"].pk

    bad = patch(client, pk, status="archivado")
    empty = patch(client, pk)

    assert bad.status_code == 400
    assert bad.json()["error"]["fields"]["status"]
    assert empty.status_code == 400
    assert ExecutiveAgreement.objects.get(pk=pk).status == "open"


def test_patch_of_a_missing_record_is_404(client):
    response = patch(client, 9999, status="done")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


# ---------- Con los accesos apagados nada cambia ----------


def test_off_everyone_reads_and_writes_everything(client, three):
    assert len(client.get(API).json()["data"]["items"]) == 3
    assert create(client, account="Cagsa").status_code == 201
    assert patch(client, three["cagsa"].pk, status="done").status_code == 200


# ---------- Capacidades ----------


def test_without_capabilities_nothing_is_readable_or_writable(
    client, enforced, three
):
    enforced("sin", caps=frozenset({"view_operations"}))

    assert client.get(API).status_code == 403
    assert create(client).status_code == 403
    assert patch(client, three["acme"].pk, status="done").status_code == 403


def test_anonymous_people_are_rejected(client, enforced, three):
    assert client.get(API).status_code == 403
    assert create(client).status_code == 403


def test_view_only_reads_but_cannot_change_anything(client, enforced, three):
    enforced("lectora", caps=READ)

    body = client.get(API).json()["data"]
    assert len(body["items"]) == 3
    assert body["can_edit"] is False
    assert all(
        item["actions"] == {"edit": False, "change_status": False}
        for item in body["items"]
    )
    assert create(client).status_code == 403
    assert patch(client, three["acme"].pk, status="done").status_code == 403
    assert ExecutiveAgreement.objects.get(pk=three["acme"].pk).status == "open"
    assert ExecutiveAgreement.objects.count() == 3


def test_edit_alone_can_also_read_and_write(client, enforced, three):
    enforced("editora", caps=EDIT)

    assert client.get(API).status_code == 200
    assert create(client).status_code == 201
    assert patch(client, three["acme"].pk, status="done").status_code == 200


# ---------- Alcance de datos ----------


def test_limited_scope_only_sees_its_accounts(client, enforced, three):
    enforced("ana", caps=BOTH, scope=AccessScope.limited(accounts=["ACME"]))

    assert titles(client.get(API)) == ["Acuerdo ACME"]
    # Pedir otra cuenta por la direccion no amplia lo que se ve.
    assert titles(client.get(API, {"account": "Cagsa"})) == []


def test_unclassified_agreements_are_only_for_the_whole_portfolio(
    client, enforced, three
):
    enforced("ana", caps=BOTH, scope=AccessScope.limited(accounts=["ACME"]))
    assert "Sin clasificar" not in titles(client.get(API))
    client.logout()
    enforced("jefa", caps=BOTH)

    assert "Sin clasificar" in titles(client.get(API))


def test_create_in_an_account_outside_the_scope_is_403_and_saves_nothing(
    client, enforced, three
):
    enforced("ana", caps=BOTH, scope=AccessScope.limited(accounts=["ACME"]))

    ok = create(client, account="ACME")
    denied = create(client, account="Cagsa")
    blank = create(client, account="")

    assert ok.status_code == 201
    assert denied.status_code == 403 and blank.status_code == 403
    assert denied.json()["error"]["code"] == "forbidden"
    assert ExecutiveAgreement.objects.filter(title="Nuevo").count() == 1


def test_a_record_outside_the_scope_looks_like_it_does_not_exist(
    client, enforced, three
):
    enforced("ana", caps=BOTH, scope=AccessScope.limited(accounts=["ACME"]))
    pk = three["cagsa"].pk

    changed = patch(client, pk, status="done")
    missing = patch(client, 9999, status="done")

    assert changed.status_code == missing.status_code == 404
    assert changed.json() == missing.json()  # no confirma que existe
    assert ExecutiveAgreement.objects.get(pk=pk).status == "open"


def test_moving_a_record_to_another_account_needs_that_account(
    client, enforced, three
):
    enforced("ana", caps=BOTH, scope=AccessScope.limited(accounts=["ACME"]))

    response = patch(client, three["acme"].pk, account="Cagsa")

    assert response.status_code == 403
    assert ExecutiveAgreement.objects.get(pk=three["acme"].pk).account == "ACME"


def test_account_aliases_count_as_the_same_account(client, enforced):
    agreement("Heineken", "Acuerdo Heineken")
    enforced(
        "ana",
        caps=BOTH,
        scope=AccessScope.limited(accounts=["Heineken México"]),
    )

    assert titles(client.get(API)) == ["Acuerdo Heineken"]
    assert create(client, account="Heineken").status_code == 201


# ---------- La vista actual usa las mismas reglas ----------


def test_legacy_view_reports_can_edit(client, three):
    assert client.get(LEGACY).json()["can_edit"] is True


def test_legacy_view_view_only_cannot_change(client, enforced, three):
    enforced("lectora", caps=READ)

    read = client.get(LEGACY).json()
    status = client.post(
        LEGACY, {"id": three["acme"].pk, "action": "status", "status": "done"}
    )
    new = client.post(LEGACY, {"account": "ACME", "title": "X"})

    assert read["can_edit"] is False and len(read["items"]) == 3
    assert status.status_code == new.status_code == 403
    assert ExecutiveAgreement.objects.get(pk=three["acme"].pk).status == "open"


def test_legacy_view_without_capabilities_is_403(client, enforced, three):
    enforced("sin", caps=frozenset())

    assert client.get(LEGACY).status_code == 403


def test_legacy_account_parameter_cannot_widen_the_scope(
    client, enforced, three
):
    enforced("ana", caps=BOTH, scope=AccessScope.limited(accounts=["ACME"]))

    own = client.get(LEGACY).json()["items"]
    forged = client.get(LEGACY, {"account": "Cagsa"}).json()["items"]

    assert [item["title"] for item in own] == ["Acuerdo ACME"]
    assert forged == []


def test_legacy_view_cannot_touch_records_outside_the_scope(
    client, enforced, three
):
    enforced("ana", caps=BOTH, scope=AccessScope.limited(accounts=["ACME"]))
    pk = three["cagsa"].pk

    status = client.post(
        LEGACY, {"id": pk, "action": "status", "status": "done"}
    )
    edit = client.post(LEGACY, {"id": pk, "title": "Cambiado"})
    form = {"kind": "pending", "status": "open", "meeting_date": ""}
    created = client.post(
        LEGACY, {**form, "account": "Cagsa", "title": "Nuevo"}
    )
    forced_account = client.post(
        LEGACY + "?account=Cagsa", {**form, "title": "Otro"}
    )

    assert status.status_code == edit.status_code == 404
    assert created.status_code == forced_account.status_code == 403
    saved = ExecutiveAgreement.objects.get(pk=pk)
    assert (saved.status, saved.title) == ("open", "Acuerdo Cagsa")
    assert not ExecutiveAgreement.objects.filter(title__in=["Nuevo", "Otro"])
