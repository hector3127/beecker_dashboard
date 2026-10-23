"""/api/rpc/: capacidad por funcion y alcance en las de cuenta."""

import pytest

from apps.access.rpc_policy import ACCOUNT_READ, POLICY
from apps.access.scope import AccessScope
from core.rpc.registry import RPC_FUNCTIONS

pytestmark = pytest.mark.django_db

OPS = frozenset({"view_operations"})


def call(client, name, *args):
    return client.post(
        f"/api/rpc/{name}/",
        {"args": list(args)},
        content_type="application/json",
    )


def test_every_registered_function_has_a_policy():
    import apps.ejecutivo.account_rpc  # noqa: F401  registra las funciones

    missing = sorted(set(RPC_FUNCTIONS) - set(POLICY))

    assert not missing, missing


def test_the_policy_names_only_registered_functions():
    assert not sorted(set(POLICY) - set(RPC_FUNCTIONS))


def test_a_write_needs_its_own_capability(client, enforced):
    enforced("lectora", caps=OPS)

    assert call(client, "agregarPendienteDaily", "P1", {}).status_code == 403


def test_settings_need_manage_integrations(client, enforced):
    enforced("ana", caps=OPS)

    assert call(client, "obtenerConfigAzureDevOps").status_code == 403


def test_anonymous_is_refused_when_enforced(client, enforced):
    enforced("x", caps=OPS)
    client.logout()

    assert call(client, "getFiltrosDisponibles").status_code == 403


def test_limited_scope_only_reaches_its_accounts(client, enforced, monkeypatch):
    monkeypatch.setattr(
        "apps.ejecutivo.account_rpc.account_view.build_account_view",
        lambda *a, **k: {"ok": True, "proyectos": []},
    )
    monkeypatch.setattr(
        "apps.ejecutivo.account_rpc.build_sheet_repository", lambda: None
    )
    enforced("ana", caps=OPS, scope=AccessScope.limited(accounts=["Acme"]))

    assert call(client, "obtenerVistaCuentaBeecker", "Acme").status_code == 200
    assert call(client, "obtenerVistaCuentaBeecker", "Otra").status_code == 404
    # Las funciones de proyectos o del equipo no se abren con alcance limitado.
    assert call(client, "getFiltrosDisponibles").status_code == 403
    assert "obtenerVistaCuentaBeecker" in ACCOUNT_READ


def test_off_everything_still_works(client):
    assert call(client, "nombreQueNoExiste").status_code == 404
