"""Verificaciones de acceso: bandera apagada, capacidades y alcance."""

import json

import pytest
from django.contrib.auth.models import AnonymousUser, Group, Permission
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView

from apps.access.capabilities import CODES
from apps.access.checks import (
    capability_permission,
    require_capability,
    resolve,
    scope_for,
)
from apps.access.scope import AccessScope

pytestmark = pytest.mark.django_db

FAKE = "tests.access.test_checks.FixedProvider"


class FixedProvider:
    """Proveedor de pruebas: cada usuario trae sus capacidades y alcance."""

    def capabilities(self, user):
        return frozenset(getattr(user, "caps", ()))

    def scope(self, user):
        return getattr(user, "limits", AccessScope.limited())


@pytest.fixture
def enforced(settings):
    settings.ACCESS_ENFORCED = True
    settings.ACCESS_PROVIDER = FAKE


def person(django_user_model, name="ana", caps=(), limits=None):
    user = django_user_model.objects.create_user(name)
    user.caps = caps
    if limits is not None:
        user.limits = limits
    return user


def get(user):
    request = RequestFactory().get("/pantalla/")
    request.user = user
    return request


@require_capability("view_costs")
def costs_view(request):
    return HttpResponse("costos")


# ---------- Bandera apagada: igual que antes de existir la app ----------


def test_off_everyone_can_everything_even_anonymous():
    for user in (AnonymousUser(),):
        access = resolve(get(user))
        assert not access.enforced
        assert access.capabilities == CODES
        assert access.scope.kind == "all"
    assert costs_view(get(AnonymousUser())).content == b"costos"


def test_off_the_provider_is_not_even_consulted(settings):
    settings.ACCESS_PROVIDER = "no.existe.Proveedor"

    assert resolve(get(AnonymousUser())).enforced is False


# ---------- Bandera encendida: matriz capacidad x persona ----------


@pytest.mark.parametrize("code", sorted(CODES))
def test_on_each_capability_only_opens_its_own_door(
    enforced, django_user_model, code
):
    holder = person(django_user_model, "con", caps=[code])
    other = person(django_user_model, "otra", caps=sorted(CODES - {code}))
    view = require_capability(code)(lambda request: HttpResponse("ok"))

    assert view(get(holder)).content == b"ok"
    with pytest.raises(PermissionDenied):
        view(get(other))


def test_on_anonymous_goes_to_login_not_403(enforced):
    response = costs_view(get(AnonymousUser()))

    assert response.status_code == 302
    assert response.url.startswith("/admin/login/")


def test_on_resolve_is_computed_once_per_request(enforced, django_user_model):
    request = get(person(django_user_model, caps=["view_costs"]))

    assert resolve(request) is resolve(request)
    assert scope_for(request).kind == "limited"


# ---------- DRF ----------


class CostsApi(APIView):
    permission_classes = [capability_permission("view_costs")]

    def get(self, request):
        return HttpResponse(json.dumps({"ok": True}))


def call_api(user=None):
    request = APIRequestFactory().get("/api/v1/x/")
    if user is not None:
        force_authenticate(request, user=user)
    return CostsApi.as_view()(request)


def test_api_permission_off_lets_everyone_through():
    assert call_api().status_code == 200


def test_api_permission_on_matrix(enforced, django_user_model):
    assert call_api().status_code == 403
    assert call_api(person(django_user_model, "a")).status_code == 403
    allowed = person(django_user_model, "b", caps=["view_costs"])
    assert call_api(allowed).status_code == 200


def test_api_error_message_is_readable_not_technical(
    enforced, django_user_model
):
    response = call_api(person(django_user_model))
    response.render() if hasattr(response, "render") else None

    assert "No tienes acceso" in response.data["detail"]


# ---------- /api/v1/me/ ----------


def test_me_off_reports_everything_and_not_enforced(client):
    body = client.get("/api/v1/me/").json()["data"]

    assert body["enforced"] is False
    assert body["capabilities"] == sorted(CODES)
    assert body["scope"] == {"kind": "all"}
    assert body["user"] is None


def test_me_on_reports_only_the_persons_capabilities(
    client, enforced, django_user_model, monkeypatch
):
    user = person(django_user_model, "ana", caps=["view_executive"])
    user.limits = AccessScope.limited(accounts=["Nestlé"])
    monkeypatch.setattr(
        FixedProvider, "capabilities", lambda s, u: {"view_executive"}
    )
    monkeypatch.setattr(FixedProvider, "scope", lambda s, u: user.limits)
    client.force_login(user)

    body = client.get("/api/v1/me/").json()["data"]

    assert body["enforced"] is True
    assert body["capabilities"] == ["view_executive"]
    assert body["scope"] == {"kind": "limited"}
    assert body["user"]["username"] == "ana"
    assert "Nestlé" not in json.dumps(body)  # la lista de cuentas no se expone


def test_me_group_permission_is_translated_to_a_capability(
    client, settings, django_user_model
):
    settings.ACCESS_ENFORCED = True
    user = django_user_model.objects.create_user("lupe")
    group = Group.objects.create(name="Finanzas")
    group.permissions.add(
        Permission.objects.get(
            content_type__app_label="access", codename="view_costs"
        )
    )
    user.groups.add(group)
    client.force_login(user)

    body = client.get("/api/v1/me/").json()["data"]

    assert body["capabilities"] == ["view_costs"]
    assert body["scope"] == {"kind": "all"}
