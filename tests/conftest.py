"""Ajustes compartidos: las pruebas no dependen del .env del equipo."""

from typing import TYPE_CHECKING

import pytest

from apps.access.scope import AccessScope
from tests.access.fake_provider import DictProvider

if TYPE_CHECKING:
    from pytest_django.fixtures import SettingsWrapper


@pytest.fixture(autouse=True)
def _stores_off_by_default(settings: "SettingsWrapper") -> None:
    """Apaga la lectura desde la base salvo que la prueba la encienda."""
    settings.CLOCKIFY_STORE_ENABLED = False
    settings.SHEETS_STORE_ENABLED = False
    settings.AZURE_STORE_ENABLED = False


@pytest.fixture(autouse=True)
def _access_not_enforced_by_default(settings: "SettingsWrapper") -> None:
    """El .env del equipo no enciende los accesos en las pruebas."""
    settings.ACCESS_ENFORCED = False


@pytest.fixture
def enforced(settings, django_user_model, client):
    """Enciende los accesos con un proveedor que se llena por usuario.

    sign_in(nombre, caps=..., scope=...) crea y firma a la persona; sin
    indicar capacidades solo tiene view_operations y alcance total.
    """
    settings.ACCESS_ENFORCED = True
    settings.ACCESS_PROVIDER = "tests.access.fake_provider.DictProvider"
    DictProvider.GRANTS = {}

    def sign_in(name, caps=frozenset({"view_operations"}), scope=None):
        DictProvider.GRANTS[name] = (caps, scope or AccessScope.everything())
        client.force_login(django_user_model.objects.create_user(name))

    yield sign_in
    DictProvider.GRANTS = {}
