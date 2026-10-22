"""Proveedor de Django y comando de preparacion."""

from io import StringIO

import pytest
from django.contrib.auth.models import AnonymousUser, Group, Permission
from django.core.management import call_command

from apps.access.capabilities import CODES
from apps.access.providers import DjangoAccessProvider, get_provider

pytestmark = pytest.mark.django_db

provider = DjangoAccessProvider()


def grant(user, code):
    user.user_permissions.add(
        Permission.objects.get(content_type__app_label="access", codename=code)
    )


def test_every_catalog_code_has_a_django_permission():
    stored = set(
        Permission.objects.filter(content_type__app_label="access").values_list(
            "codename", flat=True
        )
    )

    assert stored == CODES


def test_person_without_grants_has_no_capabilities(django_user_model):
    user = django_user_model.objects.create_user("sin")

    assert provider.capabilities(user) == frozenset()


def test_granted_permission_becomes_a_capability(django_user_model):
    user = django_user_model.objects.create_user("con")
    grant(user, "view_operations")

    assert provider.capabilities(user) == {"view_operations"}


def test_superuser_has_all_capabilities(django_user_model):
    user = django_user_model.objects.create_superuser("root")

    assert provider.capabilities(user) == CODES


def test_inactive_and_anonymous_have_nothing(django_user_model):
    user = django_user_model.objects.create_superuser("baja")
    user.is_active = False

    for who in (user, AnonymousUser()):
        assert provider.capabilities(who) == frozenset()
        assert not provider.scope(who).allows_account("Nestlé")


def test_signed_in_people_see_the_whole_portfolio_until_genesis_defines_scope(
    django_user_model,
):
    user = django_user_model.objects.create_user("ana")

    assert provider.scope(user).kind == "all"


def test_default_provider_comes_from_settings():
    assert isinstance(get_provider(), DjangoAccessProvider)


def test_setup_creates_the_full_access_group_and_is_repeatable(
    django_user_model,
):
    ana = django_user_model.objects.create_user("ana")
    baja = django_user_model.objects.create_user("baja", is_active=False)

    for _ in range(2):
        out = StringIO()
        call_command("access_setup", "--incluir-usuarios", stdout=out)

    group = Group.objects.get(name="Acceso completo")
    assert group.permissions.count() == len(CODES)
    assert list(group.user_set.all()) == [ana]
    assert baja not in group.user_set.all()
    assert provider.capabilities(ana) == CODES
    assert "actualizado" in out.getvalue()


def test_setup_without_flag_does_not_touch_people(django_user_model):
    django_user_model.objects.create_user("ana")

    call_command("access_setup", stdout=StringIO())

    assert Group.objects.get(name="Acceso completo").user_set.count() == 0
